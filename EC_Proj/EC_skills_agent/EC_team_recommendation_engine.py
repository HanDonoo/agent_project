from __future__ import annotations

from dataclasses import dataclass
from typing import List, Any, Optional, Literal
import json
import re


# ============================================================
# Models
# ============================================================

@dataclass(frozen=True)
class WorkstreamPlan:
    name: str
    goal: str
    required_skills: List[str]
    preferred_skills: List[str]
    reasoning: str


@dataclass(frozen=True)
class TeamPlan:
    """
    intent:
      - talent_search: "find me / who should I talk to"
      - delivery: discovery, strategy, execution, operation, implementation

    recommendation_mode:
      - many_candidates: show multiple people, but NOT a multi-owner team
      - team_workstreams: multiple owners/workstreams are appropriate
    """
    intent: Literal["talent_search", "delivery"]
    recommendation_mode: Literal["many_candidates", "team_workstreams"]
    needs_team: bool
    team_size: int
    workstreams: List[WorkstreamPlan]
    reasoning: str


# ============================================================
# JSON extraction helper
# ============================================================

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def safe_json(text: str) -> Optional[dict]:
    t = (text or "").strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    m = _JSON_BLOCK.search(t)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# ============================================================
# Helpers
# ============================================================

def _clamp_int(x: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = default
    return max(lo, min(hi, v))


def _as_str_list(x: Any) -> List[str]:
    if not isinstance(x, list):
        return []
    return [str(i).strip() for i in x if str(i).strip()]


def _dedupe_preserve(items: List[str]) -> List[str]:
    out, seen = [], set()
    for s in items:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


# ============================================================
# Main inference
# ============================================================

def infer_team_plan(
    client: Any,          # must expose .chat(...)
    chat_model: str,
    query: str,
    reqs,                 # reqs.required / reqs.preferred (each with .skill)
    profile,              # profile.complexity_score (cognitive complexity)
    max_team_size: int = 5,
) -> TeamPlan:
    """
    Team planner driven by TWO AI-understood dimensions:

    1) Cognitive complexity  → how hard the thinking is
    2) Organisational span   → how many distinct organisational domains must be involved

    Team size is driven primarily by organisational span.
    """

    required = [s.skill for s in (getattr(reqs, "required", []) or [])]
    preferred = [s.skill for s in (getattr(reqs, "preferred", []) or [])]

    cognitive_complexity = float(getattr(profile, "complexity_score", 0.5) or 0.5)

    prompt = f"""
You are deciding how many people need to be involved in responding to a user request.

You MUST assess TWO separate dimensions:

1) intent:
   - "talent_search": user wants to find / talk to people
   - "delivery": user wants discovery, strategy, execution, operation, or implementation

2) organisational_span (0.0–1.0):
   - How many distinct organisational domains must realistically be involved?
   - Consider finance, commercial, legal, risk, technology, operations, etc.
   - High span means multiple stakeholders are required even if no "delivery" happens yet.

IMPORTANT:
- Talent search → single owner (needs_team=false), but many candidates may be shown.
- Delivery or strategic discovery → team size depends primarily on organisational_span.
- Preferred skills NEVER create new people.
- Workstreams should only exist when different owners genuinely help.

User query:
{query}

Cognitive complexity (thinking difficulty, context only):
{cognitive_complexity}

Inferred required skills:
{json.dumps(required, ensure_ascii=False)}

Inferred preferred skills:
{json.dumps(preferred, ensure_ascii=False)}

Return ONLY valid JSON in this exact shape:
{{
  "intent": "talent_search|delivery",
  "organisational_span": 0.0,
  "reasoning": "1–3 sentences explaining the span and intent",
  "workstreams": [
    {{
      "name": "Workstream name",
      "goal": "What this stream is responsible for",
      "required_skills": ["..."],
      "preferred_skills": ["..."],
      "reasoning": "Why this stream exists"
    }}
  ]
}}
""".strip()

    content = client.chat(
        chat_model,
        [
            {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    data = safe_json(content) or {}

    # ---------------------------------------------------------
    # Parse intent
    # ---------------------------------------------------------
    intent_raw = str(data.get("intent", "")).lower().strip()
    intent: Literal["talent_search", "delivery"] = (
        intent_raw if intent_raw in {"talent_search", "delivery"} else "talent_search"
    )

    organisational_span = float(data.get("organisational_span", 0.0) or 0.0)
    organisational_span = max(0.0, min(1.0, organisational_span))

    # ---------------------------------------------------------
    # Determine team size from organisational span
    # ---------------------------------------------------------
    if organisational_span < 0.30:
        team_size = 1
    elif organisational_span < 0.55:
        team_size = 2
    elif organisational_span < 0.80:
        team_size = 3
    else:
        team_size = min(5, max_team_size)

    needs_team = team_size > 1
    recommendation_mode: Literal["many_candidates", "team_workstreams"] = (
        "many_candidates" if not needs_team else "team_workstreams"
    )

    # ---------------------------------------------------------
    # Allowed skills
    # ---------------------------------------------------------
    allowed = {s.lower(): s for s in (required + preferred)}

    # ---------------------------------------------------------
    # Parse workstreams
    # ---------------------------------------------------------
    workstreams_raw = data.get("workstreams", [])
    workstreams: List[WorkstreamPlan] = []

    if isinstance(workstreams_raw, list):
        for ws in workstreams_raw:
            if not isinstance(ws, dict):
                continue

            rs = _as_str_list(ws.get("required_skills"))
            ps = _as_str_list(ws.get("preferred_skills"))

            rs = [allowed[s.lower()] for s in rs if s.lower() in allowed]
            ps = [allowed[s.lower()] for s in ps if s.lower() in allowed]

            if not rs and required:
                rs = [required[0]]

            rs = _dedupe_preserve(rs)
            ps = _dedupe_preserve([p for p in ps if p.lower() not in {r.lower() for r in rs}])

            workstreams.append(
                WorkstreamPlan(
                    name=str(ws.get("name", "Workstream"))[:60],
                    goal=str(ws.get("goal", ""))[:160],
                    required_skills=rs,
                    preferred_skills=ps,
                    reasoning=str(ws.get("reasoning", ""))[:240] or "Split by organisational responsibility.",
                )
            )

    # ---------------------------------------------------------
    # Normalisation
    # ---------------------------------------------------------
    if intent == "talent_search":
        team_size = 1
        needs_team = False
        recommendation_mode = "many_candidates"
        workstreams = [
            WorkstreamPlan(
                name="Single owner",
                goal="Identify the best person to talk to.",
                required_skills=required[:5],
                preferred_skills=preferred[:5],
                reasoning="Talent search requests are handled by a single owner.",
            )
        ]

    if not workstreams:
        workstreams = [
            WorkstreamPlan(
                name="Single owner",
                goal="Identify and connect with the best-matching person.",
                required_skills=required[:5],
                preferred_skills=preferred[:5],
                reasoning="Fallback single workstream.",
            )
        ]

    reasoning = str(data.get("reasoning", "")).strip() or "Team size inferred from organisational span."

    return TeamPlan(
        intent=intent,
        recommendation_mode=recommendation_mode,
        needs_team=needs_team,
        team_size=team_size,
        workstreams=workstreams[:max_team_size],
        reasoning=reasoning,
    )
