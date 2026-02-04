"""
FastAPI server for EC Employee Skills Finder
OpenWebUI compatible API

Includes:
- Complexity analysis (AIClient-based; works with Ollama or Gemini)
- Team/workstream planning (workstreams first; no skills gating)
- Workstream-specific skill inference (per stream)
- Per-workstream candidate selection + set-cover
- Optional overall candidate recommendations
- Guard against OpenWebUI meta follow-up prompt requests triggering pipeline
"""
from __future__ import annotations

import sys
from pathlib import Path
import re
import asyncio
import time
import logging
import traceback
import json
from typing import List, Optional, Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path (keep relative paths unchanged)
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import your project modules
from EC_database.EC_db_manager import DatabaseManager
from EC_skills_agent.EC_skills_interpreter_engine import SkillInferenceEngine
from EC_skills_agent.ai_client import create_ai_client, AIClient

from EC_skills_agent.EC_recommender_engine import (
    recommend_top_candidates,
    infer_complexity_profile,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
    ComplexityProfile,
    EmployeeMatch,
    recommend_team_for_required_coverage,
    workstream_team_score,
    load_employee_all_skills,
)

from EC_skills_agent.EC_team_recommendation_engine import infer_team_plan

# Import configuration
import config

# FastAPI app
app = FastAPI(
    title="EC Employee Skills Finder API",
    description="AI-powered employee skills matching system with OpenWebUI support",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("=" * 80)
logger.info("🚀 Initializing EC Skills Finder API Server")
logger.info("=" * 80)

# Validate configuration
try:
    config.validate_config()
    logger.info("✅ Configuration validated")
except Exception as e:
    logger.error(f"❌ Configuration error: {e}")
    raise

logger.info(f"📁 Database path: {config.DB_PATH}")
logger.info(f"🤖 AI Provider: {config.AI_PROVIDER}")
if config.AI_PROVIDER == "gemini":
    logger.info(f"🌟 Gemini Model: {config.GEMINI_MODEL}")
else:
    logger.info(f"🤖 Ollama URL: {config.OLLAMA_BASE_URL}")
    logger.info(f"🧠 Ollama Model: {config.OLLAMA_MODEL}")

# Initialize components
try:
    logger.info("📊 Initializing database manager...")
    db = DatabaseManager(db_path=config.DB_PATH)
    logger.info("✅ Database manager initialized")

    logger.info(f"🤖 Initializing AI client ({config.AI_PROVIDER})...")
    if config.AI_PROVIDER == "gemini":
        ai_client: AIClient = create_ai_client(
            provider="gemini",
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
        )
    else:
        ai_client = create_ai_client(
            provider="ollama",
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
        )
    logger.info("✅ AI client initialized")

    logger.info("🧠 Initializing skill inference engine...")
    skill_engine = SkillInferenceEngine(
        db_path=config.DB_PATH,
        ai_client=ai_client,
        required_range=(2, 10),
        preferred_range=(1, 10),
    )
    logger.info("✅ Skill inference engine initialized")

    logger.info("=" * 80)
    logger.info("✅ All components initialized successfully")
    logger.info("=" * 80)

    DB_PATH = config.DB_PATH

except Exception as e:
    logger.error("=" * 80)
    logger.error("❌ FATAL: Failed to initialize components")
    logger.error(f"   Error type: {type(e).__name__}")
    logger.error(f"   Error message: {str(e)}")
    logger.error("📋 Full traceback:")
    logger.error(traceback.format_exc())
    logger.error("=" * 80)
    raise


# ---------------------------
# Pydantic models
# ---------------------------
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    stream: Optional[bool] = False


class QueryRequest(BaseModel):
    query: str
    top_n: Optional[int] = 5
    strict_required: Optional[bool] = False


# ---------------------------
# Utilities: map/match inferred skills -> DB catalogue
# ---------------------------
def map_skill_strings_to_catalog(skill_strings: List[str], catalogue: List[str]) -> Tuple[List[str], List[str]]:
    """
    Minimal mapping: exact/substring/token overlap.
    Returns (mapped_list, unknown_list).
    """
    mapped: List[str] = []
    unknown: List[str] = []
    if not catalogue:
        return mapped, (skill_strings or [])

    norm_catalogue = {s.lower(): s for s in catalogue}

    for raw in skill_strings or []:
        if not raw:
            continue
        s = str(raw).strip()
        s_l = s.lower()

        # exact
        if s_l in norm_catalogue:
            mapped.append(norm_catalogue[s_l])
            continue

        # substring match
        found = None
        for ck_l, ck in norm_catalogue.items():
            if s_l in ck_l or ck_l in s_l:
                found = ck
                break
        if found:
            mapped.append(found)
            continue

        # token overlap
        tokens = set(t for t in re.split(r"\W+", s_l) if t)
        best = None
        best_score = 0.0
        for ck_l, ck in norm_catalogue.items():
            ck_tokens = set(t for t in re.split(r"\W+", ck_l) if t)
            if not ck_tokens or not tokens:
                continue
            score = len(tokens & ck_tokens) / max(1, len(tokens | ck_tokens))
            if score > best_score and score >= 0.25:
                best_score = score
                best = ck
        if best:
            mapped.append(best)
            continue

        unknown.append(s)

    # dedupe preserving order
    out: List[str] = []
    seen = set()
    for m in mapped:
        kl = m.lower()
        if kl in seen:
            continue
        seen.add(kl)
        out.append(m)

    return out, unknown


def _skill_result_to_requirements(skill_result) -> SkillRequirements:
    return SkillRequirements(
        outcome_reasoning=getattr(skill_result, "outcome_reasoning", "") or "",
        overall_confidence=float(getattr(skill_result, "overall_confidence", 0.6) or 0.6),
        required=[
            RequiredSkill(
                skill=s.skill,
                weight=s.weight,
                confidence=s.confidence,
                rationale=s.rationale,
                importance=s.importance,
            )
            for s in (getattr(skill_result, "required", []) or [])
        ],
        preferred=[
            PreferredSkill(
                skill=s.skill,
                weight=s.weight,
                confidence=s.confidence,
                rationale=s.rationale,
                importance=s.importance,
            )
            for s in (getattr(skill_result, "preferred", []) or [])
        ],
    )

def _workstream_prompt_prefix(ws: dict) -> str:
    name = ws.get("name", "Workstream")
    goal = ws.get("goal", "")
    domain = ws.get("domain", "strategy")

    return (
        f"[WORKSTREAM CONTEXT]\n"
        f"Name: {name}\n"
        f"Domain: {domain}\n"
        f"Goal: {goal}\n\n"
        f"INSTRUCTIONS:\n"
        f"1) Infer skills ONLY for achieving THIS workstream's goal.\n"
        f"2) Treat the goal as the scope boundary: include skills that directly enable the goal.\n"
        f"3) Required skills = minimally sufficient to achieve the goal.\n"
        f"4) Preferred skills = improve success, speed, quality, or reduce delivery risk for the goal.\n"
        f"5) If a skill does not materially affect achieving the goal, it should not be selected.\n\n"
        f"Now infer skills for this workstream.\n\n"
    )




async def infer_workstream_requirements(query: str, ws: dict) -> SkillRequirements:
    ws_query = _workstream_prompt_prefix(ws) + query
    skill_result = await asyncio.to_thread(skill_engine.infer, ws_query)
    return _skill_result_to_requirements(skill_result)


async def find_candidates_for_workstream(
    db_path: str,
    query: str,
    ws: dict,
    top_n_pool: int = 15,
    max_team_size: int = 3,
) -> dict:
    catalogue = getattr(skill_engine, "skills", []) or []

    # 1) skills inference per stream
    reqs_obj = await infer_workstream_requirements(query, ws)

    # 2) map inferred skills to DB catalogue strings
    req_names = [s.skill for s in (reqs_obj.required or [])]
    pref_names = [s.skill for s in (reqs_obj.preferred or [])]

    def map_one(skill: str, catalogue: List[str]) -> Optional[str]:
        mapped, _ = map_skill_strings_to_catalog([skill], catalogue)
        return mapped[0] if mapped else None

    required_objs: List[RequiredSkill] = []
    for s in (reqs_obj.required or []):
        mapped = map_one(s.skill, catalogue)
        if not mapped:
            continue
        required_objs.append(
            RequiredSkill(
                skill=mapped,
                weight=float(s.weight),
                confidence=float(s.confidence),
                rationale=str(s.rationale),
                importance=float(s.importance),
            )
        )

    preferred_objs: List[PreferredSkill] = []
    for s in (reqs_obj.preferred or []):
        mapped = map_one(s.skill, catalogue)
        if not mapped:
            continue
        preferred_objs.append(
            PreferredSkill(
                skill=mapped,
                weight=float(s.weight),
                confidence=float(s.confidence),
                rationale=str(s.rationale),
                importance=float(s.importance),
            )
        )


    reqs_obj = SkillRequirements(
        outcome_reasoning=reqs_obj.outcome_reasoning,
        overall_confidence=reqs_obj.overall_confidence,
        required=required_objs,
        preferred=preferred_objs,
    )

    if not reqs_obj.required:
        return {
            "requirements": {
                "required": [],
                "preferred": [],
                "understanding": reqs_obj.outcome_reasoning,
                "confidence": reqs_obj.overall_confidence,
            },
            "complexity": {"score": 0.0, "label": "low", "reasoning": "No required skills inferred."},
            "candidate_pool": [],
            "team": [],
            "team_coverage_required": 0.0,
            "missing_required": [],
            "workstream_score": 0.0,
        }

    # 3) workstream complexity profile (AIClient-based)
    profile = infer_complexity_profile(ai_client, query, reqs_obj)

    # 4) candidate pool
    pool: List[EmployeeMatch] = await asyncio.to_thread(
        recommend_top_candidates,
        db_path,
        query,
        reqs_obj,
        profile,
        top_n_pool,
        False,  # strict_required=False for pool
    )

    # 5) set-cover team selection
    team, team_cov, missing = recommend_team_for_required_coverage(
        candidates=pool,
        reqs=reqs_obj,
        max_team_size=max_team_size,
    )

    def emp_to_dict(m: EmployeeMatch) -> dict:
        """
        Convert EmployeeMatch into a presentation-safe dict.

        IMPORTANT:
        - matched_skills = skills evaluated against the workstream requirements
        - all_skills     = full known skill list for display ("All other skills")
        (for now derived from matched_skills; can later be upgraded to DB-backed)
        """

        all_skills = load_employee_all_skills(db_path, m.employee_id)

        return {
            # --- existing fields (unchanged) ---
            "employee_id": m.employee_id,
            "name": m.formal_name,
            "email": m.email_address,
            "position": m.position_title,
            "team": m.team,
            "score": m.total_score,
            "coverage_required": m.coverage_required,
            "coverage_preferred": m.coverage_preferred,
            "matched_skills": m.matched_skills,

            # --- NEW field (used by formatter only) ---
            "all_skills": all_skills,
        }


    return {
        "requirements": {
            "required": [
                {
                    "skill": s.skill,
                    "weight": s.weight,
                    "confidence": s.confidence,
                    "importance": s.importance,
                    "rationale": s.rationale,
                    "target_level": next(
                        (t.target_level for t in (profile.targets_required or []) if t.skill.lower() == s.skill.lower()),
                        "skilled",
                    ),
                }
                for s in (reqs_obj.required or [])
            ],
            "preferred": [
                {
                    "skill": s.skill,
                    "weight": s.weight,
                    "confidence": s.confidence,
                    "importance": s.importance,
                    "rationale": s.rationale,
                    "target_level": next(
                        (t.target_level for t in (profile.targets_preferred or []) if t.skill.lower() == s.skill.lower()),
                        "awareness",
                    ),
                }
                for s in (reqs_obj.preferred or [])
            ],
            "understanding": reqs_obj.outcome_reasoning,
            "confidence": reqs_obj.overall_confidence,
        },
        "complexity": {
            "score": profile.complexity_score,
            "label": profile.complexity_label,
            "reasoning": profile.reasoning,
        },
        "candidate_pool": [emp_to_dict(m) for m in pool[: min(10, len(pool))]],
        "team": [emp_to_dict(m) for m in team],
        "team_coverage_required": team_cov,
        "missing_required": missing,
        "workstream_score": workstream_team_score(team),
    }


# ---------------------------
# Health & OpenWebUI endpoints
# ---------------------------
@app.get("/health")
async def health_check():
    try:
        stats = db.get_statistics()
        return {
            "status": "healthy",
            "database": "connected",
            "employees": stats.get("total_employees", 0),
            "timestamp": time.time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "ec-skills-finder",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "company",
                "permission": [],
                "root": "ec-skills-finder",
                "parent": None,
            }
        ],
    }


# ---------------------------
# Fallback processing
# ---------------------------
async def process_skills_query_fallback(query: str, top_n: int = 5) -> Dict[str, Any]:
    employees = db.search_employees_by_keywords(query, limit=top_n)

    if not employees:
        return {
            "success": False,
            "message": "⚠️ No matching employees found (AI unavailable, using keyword search)",
            "query": query,
            "mode": "fallback",
            "candidates": [],
        }

    candidates = []
    for emp in employees:
        candidates.append(
            {
                "employee_id": emp.get("employee_id"),
                "name": emp.get("name"),
                "email": emp.get("email"),
                "title": emp.get("title"),
                "department": emp.get("department"),
                "team": emp.get("team"),
                "score": 1.0,
                "match_summary": "Keyword match (AI unavailable)",
            }
        )

    return {
        "success": True,
        "message": f"⚠️ Found {len(candidates)} employees using keyword search (AI unavailable)",
        "query": query,
        "mode": "fallback",
        "candidates": candidates,
    }


# ---------------------------
# Core processing pipeline
# ---------------------------
async def process_skills_query(
    query: str,
    top_n: int = 5,
    strict_required: bool = False,
) -> Dict[str, Any]:
    logger.info(f"📥 Processing query: {query}")
    logger.info(f"   Parameters: top_n={top_n}, strict_required={strict_required}")

    # 1) Complexity (global) - AIClient-based, no model/base_url assumptions
    try:
        logger.info("🔍 Step 1: Complexity analysis...")
        empty_reqs = SkillRequirements(outcome_reasoning="", overall_confidence=0.3, required=[], preferred=[])
        complexity = infer_complexity_profile(ai_client, query, empty_reqs)
        logger.info(f"✅ Complexity: {complexity.complexity_label} ({complexity.complexity_score:.2f})")
    except Exception as e:
        logger.warning(f"⚠️ Complexity analysis failed: {type(e).__name__}: {str(e)}")
        complexity = ComplexityProfile(
            complexity_score=0.5,
            complexity_label="medium",
            targets_required=[],
            targets_preferred=[],
            reasoning="Complexity defaulted.",
        )

    # 2) Team/workstream planning FIRST (no skills)
    try:
        logger.info("👥 Step 2: Team/workstream planning...")
        team_plan_obj = infer_team_plan(
            client=ai_client,
            query=query,
            profile=complexity,
            max_team_size=5,
        )
        logger.info(
            f"✅ Team plan: intent={getattr(team_plan_obj,'intent',None)}, "
            f"mode={getattr(team_plan_obj,'recommendation_mode',None)}, "
            f"span={getattr(team_plan_obj,'organisational_span',None)}, "
            f"needs_team={getattr(team_plan_obj,'needs_team',None)}, size={getattr(team_plan_obj,'team_size',None)}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Team planning failed: {type(e).__name__}: {str(e)}")
        logger.warning(traceback.format_exc())
        team_plan_obj = None

    # 3) Workstream-specific skills + candidates
    team_plan_result = None
    if team_plan_obj:
        logger.info("🔍 Step 3: Per-workstream skills + candidates...")
        tasks = []
        ws_dicts: List[dict] = []
        for ws in (getattr(team_plan_obj, "workstreams", []) or [])[:5]:
            ws_dict = {
                "name": getattr(ws, "name", "") or "Workstream",
                "goal": getattr(ws, "goal", "") or "",
                "domain": getattr(ws, "domain", "") or "strategy",
                "reasoning": getattr(ws, "reasoning", "") or "",
            }
            ws_dicts.append(ws_dict)
            tasks.append(find_candidates_for_workstream(DB_PATH, query, ws_dict, top_n_pool=15, max_team_size=3))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        workstreams_out: List[dict] = []
        for idx, ws in enumerate(ws_dicts):
            reco = results[idx]
            if isinstance(reco, Exception):
                logger.warning(f"⚠️ Workstream candidate search failed for {ws.get('name')}: {reco}")
                reco = {
                    "requirements": {"required": [], "preferred": [], "understanding": "", "confidence": 0.0},
                    "complexity": {"score": 0.0, "label": "low", "reasoning": "failed"},
                    "candidate_pool": [],
                    "team": [],
                    "team_coverage_required": 0.0,
                    "missing_required": [],
                    "workstream_score": 0.0,
                }

            workstreams_out.append({**ws, "workstream_reco": reco})

        team_plan_result = {
            "intent": getattr(team_plan_obj, "intent", "talent_search"),
            "recommendation_mode": getattr(team_plan_obj, "recommendation_mode", "many_candidates"),
            "organisational_span": float(getattr(team_plan_obj, "organisational_span", 0.0) or 0.0),
            "needs_team": bool(getattr(team_plan_obj, "needs_team", False)),
            "team_size": int(getattr(team_plan_obj, "team_size", 1) or 1),
            "reasoning": getattr(team_plan_obj, "reasoning", "") or "",
            "workstreams": workstreams_out,
        }

    # 4) Optional overall candidates: infer GLOBAL skills at the end
    global_requirements = None
    matches: List[EmployeeMatch] = []
    try:
        logger.info("🔍 Step 4 (optional): Global skill inference for overall candidate list...")
        global_skill_result = await asyncio.to_thread(skill_engine.infer, query)
        global_requirements = _skill_result_to_requirements(global_skill_result)

        if global_requirements.required:
            profile_global = infer_complexity_profile(ai_client, query, global_requirements)
            matches = recommend_top_candidates(
                DB_PATH,
                query,
                global_requirements,
                profile_global,
                top_n=top_n,
                strict_required=strict_required,
            )
            logger.info(f"✅ Overall matches: {len(matches)}")
    except Exception as e:
        logger.warning(f"⚠️ Overall matching skipped/failed: {type(e).__name__}: {str(e)}")

    result: Dict[str, Any] = {
        "query": query,
        "understanding": (
            (global_requirements.outcome_reasoning if global_requirements else "")
            or "Interpreting the request, planning workstreams, then inferring skills per stream."
        ),
        "complexity": {
            "score": complexity.complexity_score,
            "label": complexity.complexity_label,
            "reasoning": complexity.reasoning,
        },
        "team_plan": team_plan_result,
        "matches": [
            {
                "employee_id": m.employee_id,
                "name": m.formal_name,
                "email": m.email_address,
                "position": m.position_title,
                "team": m.team,
                "score": m.total_score,
                "coverage_required": m.coverage_required,
                "coverage_preferred": m.coverage_preferred,
                "reasoning": m.reasoning,
                "matched_skills": m.matched_skills,
            }
            for m in (matches or [])
        ],
        "total_matches": len(matches or []),
        "confidence": float(getattr(global_requirements, "overall_confidence", 0.6) or 0.6) if global_requirements else 0.6,
    }

    return result


# ---------------------------
# Response formatting for OpenWebUI
# ---------------------------
def format_response(result: Dict[str, Any]) -> str:
    def _fmt_score(x: Any) -> str:
        try:
            return f"{float(x):.2f}"
        except Exception:
            return "0.50"

    def _fmt_pct(x: Any) -> str:
        try:
            v = float(x)
            return f"{int(round(v * 100))}%"
        except Exception:
            return "—"

    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _emp_label(emp: Dict[str, Any]) -> str:
        try:
            return f"Employee {int(emp.get('employee_id')):03d}"
        except Exception:
            return f"Employee {emp.get('employee_id')}"

    def _emp_header(emp: Dict[str, Any]) -> str:
        label = _emp_label(emp)
        title = emp.get("position") or emp.get("position_title") or ""
        team = emp.get("team") or ""
        if team:
            return f"{label} — {title} (Team: {team})".strip()
        return f"{label} — {title}".strip()

    def _domain_explainer(domain: str) -> str:
        d = (domain or "").lower().strip()
        if d in {"technical", "delivery", "ops"}:
            return "These skills are essential to assess the technical aspects of the project"
        if d in {"risk", "legal"}:
            return "These skills are crucial to assess the risk landscape and develop effective mitigation plans"
        if d in {"finance", "commercial"}:
            return "These skills are essential to assess commercial and financial feasibility"
        return "These skills are crucial to achieve the workstream goal"

    def _targets_map(skill_list: List[dict], default_target: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for s in skill_list or []:
            sk = s.get("skill")
            if not sk:
                continue
            out[str(sk)] = str(s.get("target_level") or default_target)
        return out

    def _find_employee_level(emp: Dict[str, Any], skill_name: str) -> Any:
        for m in (emp.get("matched_skills") or []):
            if not isinstance(m, dict):
                continue
            if str(m.get("skill", "")).strip().lower() == str(skill_name).strip().lower():
                return m.get("employee_level")
        return None

    def _relevant_skills_line(emp: Dict[str, Any], required_targets: Dict[str, str], preferred_targets: Dict[str, str]) -> str:
        parts: List[str] = []
        for sk, tgt in required_targets.items():
            lvl = _find_employee_level(emp, sk)
            lvl_txt = "None" if lvl is None else str(lvl)
            parts.append(f"{sk}: {lvl_txt} (target: {tgt})")
        # include preferred too (if you want it shown)
        for sk, tgt in preferred_targets.items():
            lvl = _find_employee_level(emp, sk)
            lvl_txt = "None" if lvl is None else str(lvl)
            parts.append(f"{sk}: {lvl_txt} (target: {tgt})")
        return "; ".join(parts)

    def _all_other_skills_line(emp: Dict[str, Any]) -> str:
        """
        Requires emp["all_skills"] to exist (added in find_candidates_for_workstream()).
        """
        skills = emp.get("all_skills") or []
        if not skills:
            return "All other skills: (not available)"
        # show concise "Skill: level" pairs
        pairs = []
        for s in skills[:25]:
            if not isinstance(s, dict):
                continue
            name = s.get("skill") or s.get("skill_name")
            lvl = s.get("level")
            if not name:
                continue
            pairs.append(f"{name}: {lvl if lvl else 'None'}")
        return "All other skills: " + ", ".join(pairs)

    understanding = (result.get("understanding") or "").strip()
    if not understanding:
        understanding = "Identify the skills needed to address the user’s request."

    complexity = result.get("complexity", {}) or {}
    team_plan = result.get("team_plan") or {}

    lines: List[str] = []
    lines.append("Query Understanding:")
    lines.append(understanding)
    lines.append(f"Complexity: {complexity.get('label','medium')} ({_fmt_score(complexity.get('score',0.5))})")
    lines.append((complexity.get("reasoning") or "Complexity inferred from the query.").strip())
    lines.append("👥 Team Plan & Who To Talk To:")
    lines.append(f"•\tCross-functional input needed: {bool(team_plan.get('needs_team', False))}")
    lines.append(f"•\tSuggested people to talk to: {int(team_plan.get('team_size', 1) or 1)}")
    lines.append(f"•\tReasoning: {(team_plan.get('reasoning') or 'Team plan inferred from query.').strip()}")

    for ws in (team_plan.get("workstreams", []) or [])[:5]:
        ws_name = ws.get("name", "Workstream")
        ws_goal = (ws.get("goal") or "").strip()
        ws_domain = (ws.get("domain") or "strategy").strip()

        lines.append(f"{ws_name} - Goal: {ws_goal}")
        lines.append(_domain_explainer(ws_domain))

        reco = ws.get("workstream_reco") or {}
        reqs = (reco.get("requirements", {}) or {}).get("required", []) or []
        prefs = (reco.get("requirements", {}) or {}).get("preferred", []) or []

        # Required / preferred lines (match your template)
        if reqs:
            lines.append("Required skills: " + ", ".join([str(s.get("skill")) for s in reqs if s.get("skill")]))
        else:
            lines.append("Required skills: —")

        if prefs:
            lines.append("Preferred skills: " + ", ".join([str(s.get("skill")) for s in prefs if s.get("skill")]))
        else:
            lines.append("Preferred skills: —")

        lines.append("Who to talk to:")

        team = reco.get("team") or []
        pool = reco.get("candidate_pool") or []
        primary = team[0] if team else (pool[0] if pool else None)

        required_targets = _targets_map(reqs, "skilled")
        preferred_targets = _targets_map(prefs, "awareness")

        if isinstance(primary, dict):
            lines.append(_emp_header(primary))
            if primary.get("email"):
                lines.append(f"📧 {primary.get('email')}")
            lines.append(f"✅ Relevant skills: {_relevant_skills_line(primary, required_targets, preferred_targets)}")
            lines.append(_all_other_skills_line(primary))
            lines.append("They are recommended as the top candidate because they cover "
                        f"{_fmt_pct(primary.get('coverage_required'))} of required skills for this workstream.")
        else:
            lines.append("No suitable people found for this workstream.")
            continue

        # Other candidates block
        seen = {primary.get("employee_id")} if isinstance(primary, dict) else set()
        others: List[Dict[str, Any]] = []

        for c in team[1:]:
            if isinstance(c, dict) and c.get("employee_id") not in seen:
                others.append(c)
                seen.add(c.get("employee_id"))

        for c in pool:
            if len(others) >= 2:
                break
            if isinstance(c, dict) and c.get("employee_id") not in seen:
                others.append(c)
                seen.add(c.get("employee_id"))

        if others:
            lines.append("Other candidates to talk to are:")
            for c in others:
                lines.append(f"–\t{_emp_header(c)}")
                if c.get("email"):
                    lines.append(f"\t📧 {c.get('email')}")
                lines.append(f"\t✅ Relevant skills: {_relevant_skills_line(c, required_targets, preferred_targets)}")
                lines.append(f"\t{_all_other_skills_line(c)}")

        lines.append("")  # blank line between workstreams

    return "\n".join(lines).strip() + "\n"



# ---------------------------
# OpenWebUI-compatible endpoints
# ---------------------------
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        logger.info("=" * 80)
        logger.info("📨 Received chat completion request from OpenWebUI")
        logger.info(f"   Model: {request.model}")
        logger.info(f"   Messages count: {len(request.messages)}")

        # Extract LAST user query
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Guard: OpenWebUI meta-follow-up prompt requests (don’t run pipeline)
        meta_markers = [
            "Suggest 3-5 relevant follow-up questions",
            "### Task:",
            "<chat_history>",
            '"follow_ups"',
        ]
        if any(m.lower() in user_message.lower() for m in meta_markers):
            response_content = json.dumps(
                {
                    "follow_ups": [
                        "What is the outcome you want (hire someone, or deliver a piece of work)?",
                        "Which organisational domains must be involved (finance, legal, risk, tech, commercial)?",
                        "Is this discovery/strategy work or delivery/implementation work?",
                        "What time horizon and constraints (budget, compliance, tooling) matter most?",
                        "Do you want a single point-of-contact or multiple stakeholders per domain?",
                    ]
                }
            )
            return {
                "id": f"chatcmpl-{time.time()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

        logger.info("🚀 Starting query processing pipeline...")
        result = await process_skills_query(user_message, top_n=5, strict_required=False)
        response_content = format_response(result)

        return {
            "id": f"chatcmpl-{time.time()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split()),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ FATAL ERROR in chat_completions endpoint")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.error("📋 Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.post("/query")
async def query_employees(request: QueryRequest):
    try:
        return await process_skills_query(
            request.query,
            top_n=request.top_n or 5,
            strict_required=bool(request.strict_required),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
