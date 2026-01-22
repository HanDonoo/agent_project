"""
FastAPI application for Employee Finder Agent
Compatible with OpenWebUI integration
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
from datetime import datetime

from database.db_manager import DatabaseManager
from agent.employee_finder_agent import EmployeeFinderAgent
from agent.ai_agent import EnhancedEmployeeFinderAgent
import config


# =====================================================
# App setup
# =====================================================

app = FastAPI(
    title="Employee Finder Agent",
    description="AI Agent for finding the right people across teams",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = DatabaseManager()

USE_AI_AGENT = getattr(config, "USE_AI_ROUTING", True)

if USE_AI_AGENT:
    agent = EnhancedEmployeeFinderAgent(
        db_manager=db_manager,
        enable_ai=getattr(config, "ENABLE_LLM", False)
    )
    print("🤖 Using Enhanced AI Agent")
else:
    agent = EmployeeFinderAgent(db_manager)
    print("📋 Using Basic Agent")


# =====================================================
# Helper functions (OpenWebUI compatibility)
# =====================================================

def extract_text_content(content) -> str:
    """OpenWebUI/OpenAI compatible content extraction"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
                elif "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p).strip()

    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or content).strip()

    return str(content).strip()


def rough_token_count(text: str) -> int:
    return len(text.split()) if text else 0


# =====================================================
# Request / Response models
# =====================================================

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    user_email: Optional[str] = None


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# =====================================================
# Basic endpoints
# =====================================================

@app.get("/")
async def root():
    return {
        "service": "Employee Finder Agent",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agent_type": "AI" if USE_AI_AGENT else "basic",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/query")
async def process_query(request: QueryRequest):
    try:
        clarification = agent.clarify_query(request.query)

        if clarification:
            return {
                "understanding": "Need clarification",
                "clarification_needed": clarification
            }

        response = agent.process_query(request.query, request.session_id)
        return response.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    try:
        with db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE query_log SET feedback_score = ? WHERE session_id = ?",
                (feedback.rating, feedback.session_id)
            )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# OpenAI / OpenWebUI compatible endpoints
# =====================================================

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "employee-finder",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "company"
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()

        # Ignore stream flag (OpenWebUI sends it by default)
        _ = bool(body.get("stream", False))

        model = body.get("model", "employee-finder")
        messages = body.get("messages", [])

        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = extract_text_content(msg.get("content"))
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        response = agent.process_query(user_message)
        formatted_response = format_response_for_chat(response)

        return {
            "id": f"chatcmpl-{datetime.now().timestamp()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": formatted_response
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": rough_token_count(user_message),
                "completion_tokens": rough_token_count(formatted_response),
                "total_tokens": rough_token_count(user_message)
                + rough_token_count(formatted_response)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"❌ Error in /v1/chat/completions: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Chat formatting
# =====================================================

def format_response_for_chat(response) -> str:
    output = []

    output.append(f"✅ **{response.understanding}**\n")

    if response.recommended_roles:
        output.append("📋 **Recommended Roles/Teams:**")
        for role in response.recommended_roles:
            output.append(f"  • {role}")
        output.append("")

    if response.recommendations:
        output.append("👥 **Recommended Contacts:**\n")
        for i, rec in enumerate(response.recommendations[:5], 1):
            emp = rec.employee
            output.append(f"**{i}. {emp.formal_name}**")
            output.append(f"   📧 {emp.email_address}")
            output.append(f"   💼 {emp.position_title}")
            if emp.team:
                output.append(f"   👥 Team: {emp.team}")
            output.append(
                f"   🎯 Match: {int(rec.match_score * 100)}% - {', '.join(rec.match_reasons)}"
            )
            output.append("")

    if response.next_steps:
        output.append("🚀 **Next Steps:**")
        for step in response.next_steps:
            output.append(f"  • {step}")
        output.append("")

    output.append(
        f"⏱️  *Estimated time saved: ~{int(response.estimated_time_saved * 60)} minutes*"
    )
    output.append(f"\nℹ️  *{response.disclaimer}*")

    return "\n".join(output)


# =====================================================
# Entrypoint
# =====================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
