"""
FastAPI server for EC Employee Skills Finder
OpenWebUI compatible API

Includes:
- Skill inference
- Complexity analysis
- Team plan inference + per-workstream candidate search
- Overall candidate recommendations
- Workstream score displayed separately from overall score
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
DB_PATH = "data/employee_directory_200_mock.db"
OLLAMA_BASE_URL = "http://localhost:11434"
CHAT_MODEL = "llama3.2:3b"

logger.info("=" * 80)
logger.info("🚀 Initializing EC Skills Finder API Server")
logger.info("=" * 80)
logger.info(f"📁 Database path: {DB_PATH}")
logger.info(f"🤖 Ollama URL: {OLLAMA_BASE_URL}")
logger.info(f"🧠 Chat model: {CHAT_MODEL}")

# Initialize components
try:
    logger.info("📊 Initializing database manager...")
    db = DatabaseManager(db_path=DB_PATH)
    logger.info("✅ Database manager initialized")

    logger.info("🧠 Initializing skill inference engine...")
    skill_engine = SkillInferenceEngine(
        db_path=DB_PATH,
        ollama_base_url=OLLAMA_BASE_URL,
        chat_model=CHAT_MODEL,
        required_range=(1, 10),
        preferred_range=(0, 10),
    )
    logger.info("✅ Skill inference engine initialized")

    logger.info("🤖 Initializing Ollama client...")
    ollama_client = OllamaClient(OLLAMA_BASE_URL)
    logger.info("✅ Ollama client initialized")

    logger.info("=" * 80)
    logger.info("✅ All components initialized successfully")
    logger.info("=" * 80)
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
# Utilities: map/match LLM skills -> DB catalogue
# ---------------------------
def map_skill_strings_to_catalog(skill_strings: List[str], catalogue: List[str]) -> Tuple[List[str], List[str]]:
    """
    Minimal mapping for workstreams: tries exact/substring/token overlap.
    (This is only for workstream skill strings; your primary skill inference already uses exact DB strings.)
    Returns (mapped_list, unknown_list).
    """
    mapped: List[str] = []
    unknown: List[str] = []
    if not catalogue:
        return mapped, skill_strings or []

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


async def find_candidates_for_workstream(
    db_path: str,
    query: str,
    ws: dict,
    top_n_pool: int = 15,       # pool size to search over
    max_team_size: int = 3,     # how many people to recommend per workstream
) -> dict:
    """
    Returns a workstream recommendation object:
      - candidate_pool: top individuals (partial matches allowed)
      - team: 1..max_team_size people chosen to cover required skills (set-cover)
      - team_coverage_required + missing_required
      - workstream_score: sum of team members' scores
    """
    catalogue = getattr(skill_engine, "skills", []) or []

    req_raw = ws.get("required_skills", []) or []
    pref_raw = ws.get("preferred_skills", []) or []

    req_mapped, _ = map_skill_strings_to_catalog(req_raw, catalogue)
    pref_mapped, _ = map_skill_strings_to_catalog(pref_raw, catalogue)

    required_objs: List[RequiredSkill] = [
        RequiredSkill(skill=s, weight=0.7, confidence=0.7, rationale="workstream required", importance=0.8)
        for s in req_mapped
    ]
    preferred_objs: List[PreferredSkill] = [
        PreferredSkill(skill=s, weight=0.5, confidence=0.5, rationale="workstream preferred", importance=0.5)
        for s in pref_mapped
    ]

    req_obj = SkillRequirements(
        outcome_reasoning=ws.get("goal", "") or ws.get("reasoning", ""),
        overall_confidence=0.6,
        required=required_objs,
        preferred=preferred_objs,
    )

    if not req_obj.required:
        return {
            "candidate_pool": [],
            "team": [],
            "team_coverage_required": 0.0,
            "missing_required": [],
            "workstream_score": 0.0,
        }

    # Simple stub profile (keeps scoring logic working without needing per-workstream target levels)
    profile_stub = ComplexityProfile(
        complexity_score=0.5,
        complexity_label="medium",
        targets_required=[],
        targets_preferred=[],
        reasoning="workstream stub profile",
    )

    # 1) pool of candidates (partial matches allowed)
    pool: List[EmployeeMatch] = await asyncio.to_thread(
        recommend_top_candidates,
        db_path,
        query,
        req_obj,
        profile_stub,
        top_n_pool,
        False,  # strict_required=False
    )

    # 2) select a team that covers required skills (multi-person per workstream)
    team, team_cov, missing = recommend_team_for_required_coverage(
        candidates=pool,
        reqs=req_obj,
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
        "candidate_pool": [emp_to_dict(m) for m in pool[: min(10, len(pool))]],
        "team": [emp_to_dict(m) for m in team],
        "team_coverage_required": float(team_cov),
        "missing_required": list(missing or []),
        "workstream_score": float(workstream_team_score(team)),
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
# Core processing pipeline
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


async def process_skills_query(
    query: str,
    top_n: int = 5,
    strict_required: bool = False,
) -> Dict[str, Any]:
    logger.info(f"📥 Processing query: {query}")
    logger.info(f"   Parameters: top_n={top_n}, strict_required={strict_required}")

    try:
        logger.info("🔍 Step 1: Inferring skills using Ollama...")
        skill_result = skill_engine.infer(query)
        logger.info(
            f"✅ Skill inference complete: {len(skill_result.required)} required, {len(skill_result.preferred)} preferred"
        )
    except Exception as e:
        logger.error(f"❌ Ollama error: {type(e).__name__}: {str(e)}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        logger.warning("⚠️  Falling back to keyword search mode")
        return await process_skills_query_fallback(query, top_n)

    # Convert to SkillRequirements
    logger.info("🔄 Converting skill inference results to requirements format...")
    requirements = SkillRequirements(
        outcome_reasoning=skill_result.outcome_reasoning,
        overall_confidence=skill_result.overall_confidence,
        required=[
            RequiredSkill(
                skill=s.skill,
                weight=s.weight,
                confidence=s.confidence,
                rationale=s.rationale,
                importance=s.importance,
            )
            for s in skill_result.required
        ],
        preferred=[
            PreferredSkill(
                skill=s.skill,
                weight=s.weight,
                confidence=s.confidence,
                rationale=s.rationale,
                importance=s.importance,
            )
            for s in skill_result.preferred
        ],
    )
    logger.info("✅ Requirements format conversion complete")

    # Step 2: Complexity analysis
    logger.info("🔍 Step 2: Analyzing query complexity...")
    complexity = infer_complexity_profile(
        ollama_client,
        CHAT_MODEL,
        query,
        requirements,
    )
    logger.info(
        f"✅ Complexity analysis complete: {complexity.complexity_label} (score: {complexity.complexity_score:.2f})"
    )

    # Step 2b: Team plan + per-workstream candidates
    team_plan_result = None
    try:
        logger.info("👥 Step 2b: Inferring team plan...")
        team_plan_obj = infer_team_plan(
            client=skill_engine.client,
            chat_model=CHAT_MODEL,
            query=query,
            reqs=requirements,
            profile=complexity,
            max_team_size=5,
        )
        logger.info(
            f"✅ Team plan: needs_team={team_plan_obj.needs_team}, team_size={team_plan_obj.team_size}, workstreams={len(team_plan_obj.workstreams)}"
        )

        logger.info("🔍 Finding candidates for each workstream...")
        tasks = []
        for ws in team_plan_obj.workstreams[:5]:
            ws_dict = {
                "name": getattr(ws, "name", ""),
                "goal": getattr(ws, "goal", ""),
                "required_skills": getattr(ws, "required_skills", []) or [],
                "preferred_skills": getattr(ws, "preferred_skills", []) or [],
                "reasoning": getattr(ws, "reasoning", ""),
            }
            tasks.append(find_candidates_for_workstream(DB_PATH, query, ws_dict, top_n_pool=15, max_team_size=3))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        workstreams_out: List[dict] = []
        for idx, ws in enumerate(team_plan_obj.workstreams[: len(results)]):
            reco = results[idx]
            if isinstance(reco, Exception):
                logger.warning(f"⚠️ Workstream candidate search failed: {reco}")
                reco = {
                    "candidate_pool": [],
                    "team": [],
                    "team_coverage_required": 0.0,
                    "missing_required": [],
                    "workstream_score": 0.0,
                }

            workstreams_out.append(
                {
                    "name": getattr(ws, "name", "") or "Workstream",
                    "goal": getattr(ws, "goal", "") or "",
                    "required_skills": getattr(ws, "required_skills", []) or [],
                    "preferred_skills": getattr(ws, "preferred_skills", []) or [],
                    "reasoning": getattr(ws, "reasoning", "") or "",
                    "workstream_reco": reco,
                }
            )

        team_plan_result = {
            "needs_team": bool(getattr(team_plan_obj, "needs_team", False)),
            "team_size": int(getattr(team_plan_obj, "team_size", 1) or 1),
            "reasoning": getattr(team_plan_obj, "reasoning", "") or "",
            "workstreams": workstreams_out,
        }
        logger.info("✅ Per-workstream candidate collection complete")
    except Exception as e:
        logger.warning(f"⚠️ Team plan / per-workstream candidate search failed: {type(e).__name__}: {str(e)}")
        logger.warning(traceback.format_exc())
        team_plan_result = None

    # Step 3: Overall matching
    logger.info("🔍 Step 3: Finding matching employees...")
    matches = recommend_top_candidates(
        DB_PATH,
        query,
        requirements,
        complexity,
        top_n=top_n,
        strict_required=strict_required,
    )
    logger.info(f"✅ Found {len(matches)} matching candidates")

    result = {
        "query": query,
        "understanding": skill_result.outcome_reasoning,
        "complexity": {
            "score": complexity.complexity_score,
            "label": complexity.complexity_label,
            "reasoning": complexity.reasoning,
        },
        "required_skills": [
            {
                "skill": s.skill,
                "weight": s.weight,
                "confidence": s.confidence,
                "importance": s.importance,
                "target_level": next(
                    (t.target_level for t in complexity.targets_required if t.skill.lower() == s.skill.lower()),
                    "skilled",
                ),
                "rationale": s.rationale,
            }
            for s in (skill_result.required or [])
        ],
        "preferred_skills": [
            {
                "skill": s.skill,
                "weight": s.weight,
                "confidence": s.confidence,
                "importance": s.importance,
                "target_level": next(
                    (t.target_level for t in complexity.targets_preferred if t.skill.lower() == s.skill.lower()),
                    "awareness",
                ),
                "rationale": s.rationale,
            }
            for s in (skill_result.preferred or [])
        ],
        "matches": [
            {
                "employee_id": m.employee_id,
                "name": m.formal_name,
                "email": m.email_address,
                "position": m.position_title,
                "team": m.team,
                "score": m.total_score,  # overall score
                "coverage_required": m.coverage_required,
                "coverage_preferred": m.coverage_preferred,
                "reasoning": m.reasoning,
                "matched_skills": m.matched_skills,
            }
            for m in (matches or [])
        ],
        "total_matches": len(matches or []),
        "confidence": skill_result.overall_confidence,
        "team_plan": team_plan_result,
    }

    return result


# ---------------------------
# Response formatting for OpenWebUI
# ---------------------------
def format_response(result: Dict[str, Any]) -> str:
    matches = result.get("matches", []) or []
    complexity = result.get("complexity", {}) or {}
    required_skills = result.get("required_skills", []) or []
    preferred_skills = result.get("preferred_skills", []) or []
    team_plan = result.get("team_plan")

    if not matches:
        return (
            "❌ **No matches found**\n\n"
            "**Query Understanding:**\n"
            f"{result.get('understanding', 'Unable to process query')}\n\n"
            "**Required Skills:**\n"
            f"{', '.join([s.get('skill','') for s in required_skills[:5] if s.get('skill')])}\n\n"
            f"**Complexity:** {complexity.get('label', 'unknown')} ({float(complexity.get('score', 0.0)):.2f})\n"
        )

    lines: List[str] = [
        f"✅ **Found {len(matches)} matching candidate(s)**\n",
        "**Query Understanding:**",
        f"{result.get('understanding', '')}\n",
        f"**Complexity:** {complexity.get('label', 'medium')} ({float(complexity.get('score', 0.5)):.2f})",
        f"_{complexity.get('reasoning', '')}_\n",
    ]

    if required_skills:
        lines.append("**Required Skills:**")
        for s in required_skills[:8]:
            lines.append(
                f"  • {s.get('skill')} (target: {s.get('target_level','skilled')}, "
                f"importance: {float(s.get('importance', 0.0)):.2f})"
            )
        lines.append("")

    if preferred_skills:
        lines.append("**Preferred Skills:**")
        for s in preferred_skills[:8]:
            lines.append(
                f"  • {s.get('skill')} (target: {s.get('target_level','awareness')}, "
                f"importance: {float(s.get('importance', 0.0)):.2f})"
            )
        lines.append("")

    if team_plan:
        lines.append("**👥 Team Plan & Who To Talk To:**")
        lines.append(f"• Needs team: **{bool(team_plan.get('needs_team', False))}**")
        lines.append(f"• Suggested team size: **{int(team_plan.get('team_size', 1) or 1)}**")
        if team_plan.get("reasoning"):
            lines.append(f"• Reasoning: {team_plan.get('reasoning')}")
        lines.append("")

        for ws in (team_plan.get("workstreams", []) or [])[:5]:
            lines.append(f"### {ws.get('name','Workstream')} — Goal: {ws.get('goal','')}")
            if ws.get("reasoning"):
                lines.append(f"_{ws.get('reasoning')}_")

            reqs = ws.get("required_skills", []) or []
            prefs = ws.get("preferred_skills", []) or []

            if reqs:
                lines.append(f"**Required skills:** {', '.join(reqs)}")
            if prefs:
                lines.append(f"**Preferred skills:** {', '.join(prefs)}")

            reco = ws.get("workstream_reco") or {}
            team = reco.get("team") or []
            team_cov = float(reco.get("team_coverage_required", 0.0) or 0.0)
            missing = reco.get("missing_required") or []
            ws_score = float(reco.get("workstream_score", 0.0) or 0.0)

            lines.append(f"**Workstream score:** {ws_score:.3f}")
            lines.append(f"**Team coverage (required):** {team_cov:.0%}")
            if missing:
                lines.append(f"**Missing required skills:** {', '.join(missing)}")

            if team:
                lines.append("**Who to talk to (team):**")
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
                    lines.append(f"  ✅ Individual score: {score:.3f}, Covers: {cov:.0%} required")
            else:
                lines.append("**Who to talk to:** No suitable team found for this workstream.")
            lines.append("")

    # Overall candidates
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

    lines.append(f"\n⏱️ *Confidence: {float(result.get('confidence', 0.5)):.0%}*")
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
            logger.error("❌ No user message found in request")
            raise HTTPException(status_code=400, detail="No user message found")

        logger.info(f"   User query: {user_message}")

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
                        "What team or product area should this role support?",
                        "Do you need MLOps/deployment experience as well?",
                        "What seniority level and timeframe are you hiring for?",
                        "Should telecom domain knowledge (5G/core) be required or optional?",
                        "Do you want a single owner or a small team to cover the required skills?",
                    ]
                }
            )
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
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

        logger.info("🚀 Starting query processing pipeline...")
        result = await process_skills_query(user_message, top_n=5)
        logger.info("✅ Query processing complete")

        logger.info("📝 Formatting response for OpenWebUI...")
        response_content = format_response(result)
        logger.info(f"✅ Response formatted ({len(response_content)} characters)")
        logger.info("=" * 80)

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
