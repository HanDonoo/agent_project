"""
FastAPI server for EC Employee Skills Finder
OpenWebUI compatible API

Includes:
- Complexity analysis
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
from EC_skills_agent.ai_client import create_ai_client

from EC_skills_agent.EC_recommender_engine import (
    recommend_top_candidates,
    infer_complexity_profile,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
    ComplexityProfile,
    EmployeeMatch,
    OllamaClient,
    recommend_team_for_required_coverage,
    workstream_team_score,
)

# Import configuration
import config

# IMPORTANT: your updated team planner should NOT require reqs.
# It should return workstreams with name/goal/domain/reasoning + intent/recommendation_mode/organisational_span/team_size.
from EC_skills_agent.EC_team_recommendation_engine import infer_team_plan

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

# Configuration
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

    logger.info(f"� Initializing AI client ({config.AI_PROVIDER})...")
    if config.AI_PROVIDER == "gemini":
        ai_client = create_ai_client(
            provider="gemini",
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL
        )
    else:
        ai_client = create_ai_client(
            provider="ollama",
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL
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

    # For complexity analysis - create a wrapper for backward compatibility
    logger.info("🤖 Initializing complexity analysis client...")

    # Create an adapter that wraps AIClient to work with old OllamaClient interface
    class AIClientAdapter:
        """Adapter to make AIClient work with old OllamaClient interface"""
        def __init__(self, ai_client, model):
            self.ai_client = ai_client
            self.model = model
            self.base_url = getattr(ai_client, 'base_url', 'N/A')

        def chat(self, model, messages, temperature=0.2, timeout=300):
            """Old interface: chat(model, messages, temperature)"""
            return self.ai_client.chat(messages=messages, temperature=temperature, timeout=timeout)

    ollama_client = AIClientAdapter(ai_client, CHAT_MODEL)
    logger.info("✅ Complexity analysis client initialized")

    logger.info("=" * 80)
    logger.info("✅ All components initialized successfully")
    logger.info("=" * 80)

    # Define legacy constants for backward compatibility
    DB_PATH = config.DB_PATH
    CHAT_MODEL = config.GEMINI_MODEL if config.AI_PROVIDER == "gemini" else config.OLLAMA_MODEL

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
    """
    Workstream-aware prefix that pushes the skills engine to infer skills
    for THIS stream (including cross-functional domains when relevant).
    """
    name = ws.get("name", "Workstream")
    goal = ws.get("goal", "")
    domain = ws.get("domain", "strategy")
    return (
        f"[WORKSTREAM CONTEXT]\n"
        f"Name: {name}\n"
        f"Domain: {domain}\n"
        f"Goal: {goal}\n\n"
        f"Only infer skills needed to achieve THIS workstream goal.\n"
        f"Be domain-appropriate:\n"
        f"- finance/accounting => procurement, budgeting, financial modelling, accounting, governance\n"
        f"- commercial => negotiation, contracting, pricing, vendor mgmt\n"
        f"- legal/risk => compliance, controls, risk mgmt, privacy/security\n"
        f"- technical => deep learning, data engineering, MLOps, software engineering\n\n"
        f"Do NOT bias toward technical skills unless the domain is technical/delivery.\n\n"
    )


async def infer_workstream_requirements(query: str, ws: dict) -> SkillRequirements:
    """
    Calls your existing SkillInferenceEngine, but with a workstream-specific prefix.
    """
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
    """
    Workstream pipeline:
      1) infer skills for this workstream (domain-aware)
      2) map to catalogue
      3) infer complexity profile for this workstream (targets)
      4) score candidates
      5) pick a small team via set-cover on required skills
    """
    catalogue = getattr(skill_engine, "skills", []) or []

    # 1) skills inference per stream
    reqs_obj = await infer_workstream_requirements(query, ws)

    # 2) map inferred skills to DB catalogue strings
    req_names = [s.skill for s in (reqs_obj.required or [])]
    pref_names = [s.skill for s in (reqs_obj.preferred or [])]

    req_mapped, _ = map_skill_strings_to_catalog(req_names, catalogue)
    pref_mapped, _ = map_skill_strings_to_catalog(pref_names, catalogue)

    # 2b) rebuild requirements using mapped strings
    required_objs: List[RequiredSkill] = []
    for i, s in enumerate(reqs_obj.required or []):
        if i < len(req_mapped):
            required_objs.append(
                RequiredSkill(
                    skill=req_mapped[i],
                    weight=float(s.weight),
                    confidence=float(s.confidence),
                    rationale=str(s.rationale),
                    importance=float(s.importance),
                )
            )

    preferred_objs: List[PreferredSkill] = []
    for i, s in enumerate(reqs_obj.preferred or []):
        if i < len(pref_mapped):
            preferred_objs.append(
                PreferredSkill(
                    skill=pref_mapped[i],
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

    # 3) workstream complexity profile (targets)
    profile = infer_complexity_profile(ollama_client, CHAT_MODEL, query, reqs_obj)

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

    # 5) set-cover team selection (covers required skills across people)
    team, team_cov, missing = recommend_team_for_required_coverage(
        candidates=pool,
        reqs=reqs_obj,
        max_team_size=max_team_size,
    )

    def emp_to_dict(m: EmployeeMatch) -> dict:
        return {
            "employee_id": m.employee_id,
            "name": m.formal_name,
            "email": m.email_address,
            "position": m.position_title,
            "team": m.team,
            "score": m.total_score,
            "coverage_required": m.coverage_required,
            "coverage_preferred": m.coverage_preferred,
            "matched_skills": m.matched_skills,
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
            "message": "⚠️ No matching employees found (Ollama unavailable, using keyword search)",
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
                "match_summary": "Keyword match (Ollama unavailable)",
            }
        )

    return {
        "success": True,
        "message": f"⚠️ Found {len(candidates)} employees using keyword search (Ollama unavailable)",
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

    # 1) Complexity (global) - do NOT depend on skill inference
    try:
        logger.info("🔍 Step 1: Complexity analysis...")
        # allow empty reqs here; your infer_complexity_profile is robust to it
        empty_reqs = SkillRequirements(outcome_reasoning="", overall_confidence=0.3, required=[], preferred=[])
        complexity = infer_complexity_profile(
            ollama_client,
            CHAT_MODEL,
            query,
            empty_reqs,
        )
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
            client=skill_engine.client,
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

    # 4) Optional overall candidates:
    #    If you want an overall list, infer a GLOBAL set of skills at the end.
    global_requirements = None
    matches: List[EmployeeMatch] = []
    try:
        logger.info("🔍 Step 4 (optional): Global skill inference for overall candidate list...")
        global_skill_result = await asyncio.to_thread(skill_engine.infer, query)
        global_requirements = _skill_result_to_requirements(global_skill_result)

        # If no required skills, skip overall scoring
        if global_requirements.required:
            profile_global = infer_complexity_profile(ollama_client, CHAT_MODEL, query, global_requirements)
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

    # Build response (main value is team_plan_result with per-stream skills)
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
    complexity = result.get("complexity", {}) or {}
    team_plan = result.get("team_plan")
    matches = result.get("matches", []) or []

    lines: List[str] = [
        f"✅ **Processed request**\n",
        "**Query:**",
        f"{result.get('query','')}\n",
        f"**Complexity:** {complexity.get('label', 'medium')} ({float(complexity.get('score', 0.5)):.2f})",
        f"_{complexity.get('reasoning', '')}_\n",
    ]

    # Workstreams are the “real” output now
    if team_plan:
        intent = team_plan.get("intent", "talent_search")
        mode = team_plan.get("recommendation_mode", "many_candidates")
        span = float(team_plan.get("organisational_span", 0.0) or 0.0)

        header = "**👥 Team Plan & Who To Talk To:**"
        if intent == "talent_search" and span >= 0.30:
            header = "**👥 Stakeholders & Who To Talk To:**"
        lines.append(header)

        lines.append(f"• Intent: **{intent}**")
        lines.append(f"• Mode: **{mode}**")
        lines.append(f"• Organisational span: **{span:.2f}**")
        lines.append(f"• Cross-functional input needed: **{bool(team_plan.get('needs_team', False))}**")
        lines.append(f"• Suggested people to talk to: **{int(team_plan.get('team_size', 1) or 1)}**")
        if team_plan.get("reasoning"):
            lines.append(f"• Reasoning: {team_plan.get('reasoning')}")
        lines.append("")

        for ws in (team_plan.get("workstreams", []) or [])[:5]:
            ws_name = ws.get("name", "Workstream")
            ws_goal = ws.get("goal", "")
            ws_domain = ws.get("domain", "strategy")
            ws_reasoning = ws.get("reasoning", "")

            lines.append(f"### {ws_name} ({ws_domain}) — Goal: {ws_goal}")
            if ws_reasoning:
                lines.append(f"_{ws_reasoning}_")

            reco = ws.get("workstream_reco") or {}
            reqs = (reco.get("requirements", {}) or {}).get("required", []) or []
            prefs = (reco.get("requirements", {}) or {}).get("preferred", []) or []

            # Print inferred skills PER stream (this is the point of your change)
            if reqs:
                lines.append("**Required skills (this stream):**")
                for s in reqs[:8]:
                    lines.append(
                        f"  • {s.get('skill')} (target: {s.get('target_level','skilled')}, "
                        f"importance: {float(s.get('importance', 0.0)):.2f})"
                    )
            if prefs:
                lines.append("**Preferred skills (this stream):**")
                for s in prefs[:8]:
                    lines.append(
                        f"  • {s.get('skill')} (target: {s.get('target_level','awareness')}, "
                        f"importance: {float(s.get('importance', 0.0)):.2f})"
                    )

            team = reco.get("team") or []
            team_cov = float(reco.get("team_coverage_required", 0.0) or 0.0)
            missing = reco.get("missing_required") or []
            ws_score = float(reco.get("workstream_score", 0.0) or 0.0)

            label = "Workstream score" if intent == "delivery" else "Stakeholder score"
            lines.append(f"**{label}:** {ws_score:.3f}")
            lines.append(f"**Coverage (required skills):** {team_cov:.0%}")
            if missing:
                lines.append(f"**Missing required skills:** {', '.join(missing)}")

            if team:
                lines.append("**Who to talk to:**")
                for c in team:
                    name = c.get("name") or "Unknown"
                    position = c.get("position") or ""
                    team_name = c.get("team") or ""
                    email = c.get("email") or ""
                    score = float(c.get("score", 0.0) or 0.0)
                    cov = float(c.get("coverage_required", 0.0) or 0.0)

                    if team_name:
                        lines.append(f"- **{name}** — {position} (Team: {team_name})")
                    else:
                        lines.append(f"- **{name}** — {position}")
                    if email:
                        lines.append(f"  📧 {email}")
                    lines.append(f"  ✅ Individual score: {score:.3f}, Covers: {cov:.0%} of required skills")
            else:
                lines.append("**Who to talk to:** No suitable people found for this stream.")
            lines.append("")

    # Optional overall list
    if matches:
        lines.append("**👥 Top Candidates (overall):**\n")
        for i, match in enumerate(matches[:5], 1):
            lines.append(f"**{i}. {match.get('name','Unknown')}**")
            if match.get("email"):
                lines.append(f"   📧 {match.get('email')}")
            lines.append(f"   💼 {match.get('position','')}")
            if match.get("team"):
                lines.append(f"   🏢 Team: {match.get('team')}")
            lines.append(f"   🎯 Overall score: {float(match.get('score', 0.0)):.3f}")
            lines.append(f"   📊 Required Coverage: {float(match.get('coverage_required', 0.0)):.0%}")
            lines.append(f"   📈 Preferred Coverage: {float(match.get('coverage_preferred', 0.0)):.0%}")

            matched = match.get("matched_skills", []) or []
            required_matched = [s for s in matched if s.get("type") == "required"][:3]
            if required_matched:
                lines.append("   ✅ Key Skills:")
                for sk in required_matched:
                    level = sk.get("employee_level", "N/A")
                    target = sk.get("target_level", "N/A")
                    verified = "✓" if sk.get("verified") else ""
                    lines.append(f"      • {sk.get('skill')}: {level} (target: {target}) {verified}")
            lines.append("")

    lines.append(f"\n⏱️ *Confidence: {float(result.get('confidence', 0.6)):.0%}*")
    return "\n".join(lines)


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

        # Extract LAST user query (important)
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
