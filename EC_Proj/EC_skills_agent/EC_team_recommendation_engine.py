from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Literal
import json
import re

from .ai_client import AIClient


@dataclass(frozen=True)
class WorkstreamPlan:
    """
    domain is a LIGHT label used to drive skill inference prompts.
    Keep it broad and stable (finance, commercial, legal, risk, technical, ops, delivery, strategy).
    """
    name: str
    goal: str
    domain: str
    reasoning: str


@dataclass(frozen=True)
class TeamPlan:
    """
    intent:
      - "talent_search": user wants names / who to talk to / find people
      - "delivery": discovery, strategy, execution, operation, implementation, rollout

    recommendation_mode:
      - "many_candidates": show multiple people (stakeholders) but not delivery workstreams
      - "team_workstreams": multiple distinct streams/owners for delivery

    notes:
      - This planner does NOT output skills. It outputs workstreams/domains only.
      - Skills are inferred AFTER this, per workstream.
    """
    intent: Literal["talent_search", "delivery"]
    recommendation_mode: Literal["many_candidates", "team_workstreams"]
    organisational_span: float
    needs_team: bool
    team_size: int
    workstreams: List[WorkstreamPlan]
    reasoning: str


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


def _clamp01(x: Any, default: float = 0.5) -> float:
    try:
        v = float(x)
    except Exception:
        v = default
    return max(0.0, min(1.0, v))


def _clamp_int(x: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(x)
    except Exception:
        v = default
    return max(lo, min(hi, v))


def _as_ws_list(x: Any) -> List[dict]:
    return x if isinstance(x, list) else []


def infer_team_plan(
    client: AIClient,
    query: str,
    profile: Any,  # expects profile.complexity_score / complexity_label
    max_team_size: int = 5,
) -> TeamPlan:
    complexity_score = _clamp01(getattr(profile, "complexity_score", 0.5), 0.5)
    complexity_label = str(getattr(profile, "complexity_label", "medium") or "medium")

    prompt = f"""
You are deciding how a request should be handled: as a talent search (who to talk to) or as delivery planning (workstreams).

You MUST output:

1) intent:
   - "talent_search": user wants people to talk to / recommendations / who can help
   - "delivery": user wants discovery, strategy, execution, build, rollout, operations

2) organisational_span (0.0–1.0):
   - how many distinct organisational domains must be involved (finance, procurement/commercial, legal, risk, technical, ops, delivery)
   - high span means multiple stakeholders are required even if no delivery happens yet

3) workstreams:
   - For intent="talent_search":
       - output 2–4 stakeholder workstreams only if they are meaningfully different
       - avoid overlapping workstreams (don’t repeat the same skills/goal twice)
       - if the request is primarily technical, keep it to 1–2 technical workstreams max
       - each workstream should have a clear name and a specific goal
       - each goal must be phrased as a concrete outcome. Avoid generic goals like ‘manage’, ‘support’, ‘assess’ unless paired with a specific deliverable
       - names should be human-friendly and specific (examples: "Technical Requirements", "Commercial & Procurement", "Risk Management", "Legal & Compliance", "Finance Constraints")
       - choose an appropriate domain tag for each (finance|commercial|legal|risk|technical|ops|strategy)
   - For intent="delivery":
       - output 2–5 distinct workstreams with a domain tag for each.

Complexity (context):
- score: {complexity_score}
- label: {complexity_label}

Query:
{query}

Return ONLY valid JSON in this exact shape:
{{
  "intent": "talent_search|delivery",
  "organisational_span": 0.0,
  "reasoning": "1-3 sentences (why these workstreams and why cross-functional or not)",
  "workstreams": [
    {{
      "name": "Workstream name",
      "goal": "What this stream achieves",
      "domain": "finance|commercial|legal|risk|technical|ops|delivery|strategy",
      "reasoning": "Why this stream exists"
    }}
  ]
}}
""".strip()


    content = client.chat(
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        timeout=240,
    )

    data = safe_json(content) or {}

    intent_raw = str(data.get("intent", "")).strip().lower()
    intent: Literal["talent_search", "delivery"] = (
        intent_raw if intent_raw in {"talent_search", "delivery"} else "talent_search"
    )

    organisational_span = _clamp01(data.get("organisational_span", 0.5), 0.5)
    reasoning = str(data.get("reasoning", "")).strip() or "Team plan inferred from query."

    ws_out: List[WorkstreamPlan] = []
    allowed_domains = {"finance", "commercial", "legal", "risk", "technical", "ops", "delivery", "strategy"}

    for ws in _as_ws_list(data.get("workstreams")):
        if not isinstance(ws, dict):
            continue
        name = str(ws.get("name", "")).strip() or "Workstream"
        goal = str(ws.get("goal", "")).strip() or "Support the request."
        domain = str(ws.get("domain", "")).strip().lower() or "strategy"
        if domain not in allowed_domains:
            domain = "strategy"

        ws_out.append(
            WorkstreamPlan(
                name=name[:60],
                goal=goal[:180],
                domain=domain,
                reasoning=str(ws.get("reasoning", "")).strip()[:260] or "Workstream inferred from query.",
            )
        )

    # Hard fallback
    if not ws_out:
        if intent == "delivery":
            ws_out = [
                WorkstreamPlan(
                    name="Delivery",
                    goal="Deliver the requested outcome end-to-end.",
                    domain="delivery",
                    reasoning="Fallback single delivery stream.",
                )
            ]
        else:
            ws_out = [
                WorkstreamPlan(
                    name="Stakeholders",
                    goal="Identify the right people to talk to across relevant functions.",
                    domain="strategy",
                    reasoning="Fallback stakeholder stream.",
                )
            ]

    # Team sizing logic
    if intent == "delivery":
        if complexity_score < 0.35:
            base = 1
        elif complexity_score <= 0.65:
            base = 2
        else:
            base = 3

        if organisational_span < 0.30:
            span_lift = 0
        elif organisational_span < 0.55:
            span_lift = 1
        elif organisational_span < 0.80:
            span_lift = 2
        else:
            span_lift = 2

        team_size = min(max_team_size, max(base + span_lift, len(ws_out)))
        needs_team = team_size > 1
        recommendation_mode: Literal["many_candidates", "team_workstreams"] = "team_workstreams"
    else:
        # talent_search: allow multiple stakeholder workstreams (2–5) so output matches the example style
        # We keep recommendation_mode="many_candidates" and team sizing logic, but DO NOT collapse to a single stream.
        if organisational_span < 0.30:
            team_size = 1
        elif organisational_span < 0.55:
            team_size = 2
        elif organisational_span < 0.80:
            team_size = 3
        else:
            team_size = min(max_team_size, 5)

        needs_team = team_size > 1
        recommendation_mode = "many_candidates"

        # Keep up to team_size workstreams (already inferred by the model)
        ws_out = ws_out[:team_size]

    team_size = _clamp_int(team_size, 1, max_team_size, 1)

    return TeamPlan(
        intent=intent,
        recommendation_mode=recommendation_mode,
        organisational_span=organisational_span,
        needs_team=needs_team,
        team_size=team_size,
        workstreams=ws_out[:max_team_size],
        reasoning=reasoning,
    )
