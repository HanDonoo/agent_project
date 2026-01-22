"""
FastAPI server for EC Employee Skills Finder
OpenWebUI compatible API
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import uuid
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from EC_database.EC_db_manager import DatabaseManager
from EC_skills_agent.EC_skills_interpreter_engine import SkillInferenceEngine
from EC_skills_agent.EC_recommender_engine import (
    recommend_top_candidates,
    infer_complexity_profile,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
    OllamaClient,
)

# Initialize FastAPI app
app = FastAPI(
    title="EC Employee Skills Finder API",
    description="AI-powered employee skills matching system with OpenWebUI support",
    version="1.0.0"
)

# CORS middleware
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
CHAT_MODEL = "llama3.2:3b"  # （ old one llama3.1:8b）

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
        chat_model=CHAT_MODEL
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
    logger.error(f"❌ FATAL: Failed to initialize components")
    logger.error(f"   Error type: {type(e).__name__}")
    logger.error(f"   Error message: {str(e)}")
    logger.error(f"📋 Full traceback:")
    logger.error(traceback.format_exc())
    logger.error("=" * 80)
    raise


# ============================================
# Pydantic Models
# ============================================

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


# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = db.get_statistics()
        return {
            "status": "healthy",
            "database": "connected",
            "employees": stats.get("total_employees", 0),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# ============================================
# OpenWebUI Compatible Endpoints
# ============================================

@app.get("/v1/models")
async def list_models():
    """List available models (OpenWebUI compatible)"""
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
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenWebUI compatible chat completions endpoint
    Processes employee skills queries using AI
    """
    try:
        logger.info("=" * 80)
        logger.info("📨 Received chat completion request from OpenWebUI")
        logger.info(f"   Model: {request.model}")
        logger.info(f"   Messages count: {len(request.messages)}")

        # Extract user query from messages
        user_message = None
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            logger.error("❌ No user message found in request")
            raise HTTPException(status_code=400, detail="No user message found")

        logger.info(f"   User query: {user_message}")

        # Process query
        logger.info("🚀 Starting query processing pipeline...")
        result = await process_skills_query(user_message, top_n=5)
        logger.info("✅ Query processing complete")

        # Format response
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
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ FATAL ERROR in chat_completions endpoint")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.error(f"📋 Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


# ============================================
# Direct Query Endpoint
# ============================================

@app.post("/query")
async def query_employees(request: QueryRequest):
    """
    Direct query endpoint for employee skills matching
    Returns structured JSON response
    """
    try:
        result = await process_skills_query(
            request.query,
            top_n=request.top_n,
            strict_required=request.strict_required
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ============================================
# Core Processing Logic
# ============================================

async def process_skills_query_fallback(
    query: str,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Fallback mode when Ollama is not available.
    Uses simple keyword matching to find employees.
    """
    # Simple keyword search in database
    employees = db.search_employees_by_keywords(query, limit=top_n)

    if not employees:
        return {
            "success": False,
            "message": "⚠️ No matching employees found (Ollama unavailable, using keyword search)",
            "query": query,
            "mode": "fallback",
            "candidates": []
        }

    # Format results
    candidates = []
    for emp in employees:
        candidates.append({
            "employee_id": emp.get("employee_id"),
            "name": emp.get("name"),
            "email": emp.get("email"),
            "title": emp.get("title"),
            "department": emp.get("department"),
            "team": emp.get("team"),
            "score": 1.0,  # Simple mode, no scoring
            "match_summary": "Keyword match (Ollama unavailable)"
        })

    return {
        "success": True,
        "message": f"⚠️ Found {len(candidates)} employees using keyword search (Ollama unavailable)",
        "query": query,
        "mode": "fallback",
        "candidates": candidates
    }


async def process_skills_query(
    query: str,
    top_n: int = 5,
    strict_required: bool = False
) -> Dict[str, Any]:
    """
    Process a skills query through the AI pipeline:
    1. Skill inference (what skills are needed?)
    2. Complexity analysis (what proficiency level?)
    3. Employee matching (who has these skills?)

    Falls back to simple keyword matching if Ollama is not available.
    """

    logger.info(f"📥 Processing query: {query}")
    logger.info(f"   Parameters: top_n={top_n}, strict_required={strict_required}")

    try:
        # Step 1: Infer required and preferred skills (using Ollama)
        logger.info("🔍 Step 1: Inferring skills using Ollama...")
        skill_result = skill_engine.infer(query)
        logger.info(f"✅ Skill inference complete: {len(skill_result.required)} required, {len(skill_result.preferred)} preferred")
    except Exception as e:
        # Fallback: Simple keyword-based skill extraction
        logger.error(f"❌ Ollama error: {type(e).__name__}: {str(e)}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        logger.warning("⚠️  Falling back to keyword search mode")
        return await process_skills_query_fallback(query, top_n)

    # Convert to SkillRequirements format
    try:
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
                    importance=s.importance
                )
                for s in skill_result.required
            ],
            preferred=[
                PreferredSkill(
                    skill=s.skill,
                    weight=s.weight,
                    confidence=s.confidence,
                    rationale=s.rationale,
                    importance=s.importance
                )
                for s in skill_result.preferred
            ]
        )
        logger.info("✅ Requirements format conversion complete")
    except Exception as e:
        logger.error(f"❌ Error converting requirements: {type(e).__name__}: {str(e)}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise

    # Step 2: Infer complexity profile and target proficiency levels
    try:
        logger.info("🔍 Step 2: Analyzing query complexity...")
        complexity = infer_complexity_profile(
            ollama_client,
            CHAT_MODEL,
            query,
            requirements
        )
        logger.info(f"✅ Complexity analysis complete: {complexity.complexity_label} (score: {complexity.complexity_score:.2f})")
    except Exception as e:
        logger.error(f"❌ Error in complexity analysis: {type(e).__name__}: {str(e)}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise

    # Step 3: Find matching employees
    try:
        logger.info("🔍 Step 3: Finding matching employees...")
        matches = recommend_top_candidates(
            DB_PATH,
            query,
            requirements,
            complexity,
            top_n=top_n,
            strict_required=strict_required
        )
        logger.info(f"✅ Found {len(matches)} matching candidates")
    except Exception as e:
        logger.error(f"❌ Error finding candidates: {type(e).__name__}: {str(e)}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise

    # Format result
    return {
        "query": query,
        "understanding": skill_result.outcome_reasoning,
        "complexity": {
            "score": complexity.complexity_score,
            "label": complexity.complexity_label,
            "reasoning": complexity.reasoning
        },
        "required_skills": [
            {
                "skill": s.skill,
                "weight": s.weight,
                "confidence": s.confidence,
                "importance": s.importance,
                "target_level": next(
                    (t.target_level for t in complexity.targets_required if t.skill.lower() == s.skill.lower()),
                    "skilled"
                ),
                "rationale": s.rationale
            }
            for s in skill_result.required
        ],
        "preferred_skills": [
            {
                "skill": s.skill,
                "weight": s.weight,
                "confidence": s.confidence,
                "importance": s.importance,
                "target_level": next(
                    (t.target_level for t in complexity.targets_preferred if t.skill.lower() == s.skill.lower()),
                    "awareness"
                ),
                "rationale": s.rationale
            }
            for s in skill_result.preferred
        ],
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
                "matched_skills": m.matched_skills
            }
            for m in matches
        ],
        "total_matches": len(matches),
        "confidence": skill_result.overall_confidence
    }


def format_response(result: Dict[str, Any]) -> str:
    """Format the query result for chat display"""

    matches = result.get("matches", [])
    complexity = result.get("complexity", {})
    required_skills = result.get("required_skills", [])

    if not matches:
        return f"""❌ **No matches found**

**Query Understanding:**
{result.get('understanding', 'Unable to process query')}

**Required Skills:**
{', '.join([s['skill'] for s in required_skills[:5]])}

**Complexity:** {complexity.get('label', 'unknown')} ({complexity.get('score', 0):.2f})

💡 **Suggestions:**
• Try broadening your search criteria
• Lower the required proficiency levels
• Search for related skills
"""

    # Build response
    lines = [
        f"✅ **Found {len(matches)} matching candidate(s)**\n",
        f"**Query Understanding:**",
        f"{result.get('understanding', '')}\n",
        f"**Complexity:** {complexity.get('label', 'medium')} ({complexity.get('score', 0.5):.2f})",
        f"_{complexity.get('reasoning', '')}_\n",
    ]

    # Required skills
    if required_skills:
        lines.append("**Required Skills:**")
        for s in required_skills[:5]:
            lines.append(f"  • {s['skill']} (target: {s['target_level']}, importance: {s['importance']:.2f})")
        lines.append("")

    # Top matches
    lines.append("**👥 Top Candidates:**\n")
    for i, match in enumerate(matches[:5], 1):
        lines.append(f"**{i}. {match['name']}**")
        lines.append(f"   📧 {match['email']}")
        lines.append(f"   💼 {match['position']}")
        if match.get('team'):
            lines.append(f"   🏢 Team: {match['team']}")
        lines.append(f"   🎯 Score: {match['score']:.3f}")
        lines.append(f"   📊 Required Coverage: {match['coverage_required']:.0%}")
        lines.append(f"   📈 Preferred Coverage: {match['coverage_preferred']:.0%}")

        # Show top matched skills
        matched = match.get('matched_skills', [])
        required_matched = [s for s in matched if s.get('type') == 'required'][:3]
        if required_matched:
            lines.append(f"   ✅ Key Skills:")
            for skill in required_matched:
                level = skill.get('employee_level', 'N/A')
                target = skill.get('target_level', 'N/A')
                verified = "✓" if skill.get('verified') else ""
                lines.append(f"      • {skill['skill']}: {level} (target: {target}) {verified}")
        lines.append("")

    lines.append(f"\n⏱️ *Confidence: {result.get('confidence', 0.5):.0%}*")

    return "\n".join(lines)

