"""
EC_skills_interpreter_engine.py

Ollama-only skill inference engine with AI-only ("smarter") top-up.

Design goals:
- Let the LLM interpret the query freely, but return skills ONLY from the DB catalogue (exact strings).
- Each inferred skill includes weight/confidence/importance (0..1) + rationale.
- If required skills count is below minimum, use an AI "repair/top-up" call (NOT deterministic catalogue fill).
- Minimal deterministic logic: clamp numeric ranges, dedupe, enforce max counts, remove preferred overlap.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import requests


# =========================
# Data structures
# =========================

@dataclass(frozen=True)
class InferredSkill:
    skill: str
    weight: float          # 0..1
    confidence: float      # 0..1
    importance: float      # 0..1
    rationale: str


@dataclass(frozen=True)
class SkillInferenceResult:
    outcome_reasoning: str
    overall_confidence: float
    required: List[InferredSkill]   # 1..10
    preferred: List[InferredSkill]  # 0..10


# =========================
# Utility
# =========================

_WS = re.compile(r"\s+")
_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())


def _clamp01(x) -> float:
    try:
        xf = float(x)
    except Exception:
        xf = 0.0
    return max(0.0, min(1.0, xf))


def _dedupe_keep_order(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in items:
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def _safe_json_extract(text: str) -> Optional[dict]:
    """
    Accept either pure JSON or JSON embedded in extra text.
    Returns dict or None.
    """
    if not text:
        return None
    t = text.strip()
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


# =========================
# Ollama client
# =========================

class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def chat(self, model: str, messages: List[dict], temperature: float = 0.2, timeout: int = 120) -> str:
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        try:
            return data["message"]["content"]
        except Exception:
            raise RuntimeError(f"Unexpected chat response shape: {data}")


# =========================
# DB loader
# =========================

def load_skills_from_db(db_path: str) -> List[str]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT name FROM skills ORDER BY name").fetchall()

    skills = [_norm(r["name"]) for r in rows if _norm(r["name"])]
    skills = _dedupe_keep_order(skills)

    if not skills:
        raise ValueError("No skills found in DB. Ensure the 'skills' table is populated.")
    return skills


# =========================
# Skill inference engine
# =========================

class SkillInferenceEngine:
    """
    - LLM sees the FULL catalogue (debug-style).
    - Output must use EXACT skill strings from the catalogue.
    - If required count is too low, we do an AI-only top-up/repair call.
    """

    def __init__(
        self,
        *,
        db_path: str,
        ollama_base_url: str = "http://localhost:11434",
        chat_model: str = "llama3.2:3b",
        required_range: Tuple[int, int] = (1, 10),
        preferred_range: Tuple[int, int] = (0, 10),
    ):
        self.db_path = db_path
        self.client = OllamaClient(ollama_base_url)
        self.chat_model = chat_model

        self.req_min, self.req_max = required_range
        self.pref_min, self.pref_max = preferred_range

        self.skills = load_skills_from_db(db_path)
        self._allowed = {s.lower(): s for s in self.skills}

    def infer(self, query: str) -> SkillInferenceResult:
        query = _norm(query)
        if not query:
            raise ValueError("Query must be non-empty.")

        # First pass
        prompt = self._build_prompt(query)
        content = self.client.chat(
            self.chat_model,
            [
                {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
        )

        data = _safe_json_extract(content)
        if not isinstance(data, dict):
            # AI repair attempt (one shot)
            repaired = self._ai_repair_json(query, raw_text=content)
            data = repaired if isinstance(repaired, dict) else {}

        res = self._postprocess(query, data)

        # If required count still below min, do AI top-up/repair (NOT deterministic fill)
        if len(res.required) < self.req_min:
            res = self._ai_topup_required(query, res)

        return res

    def _build_prompt(self, query: str) -> str:
        skill_list = self.skills

        return f"""
User query:
{query}

Rules (must follow precisely):
- You MUST select skills ONLY from the Candidate Skills list below (exact string matches).
- REQUIRED skills count must be {self.req_min}-{self.req_max}.
- PREFERRED skills count must be {self.pref_min}-{self.pref_max}.
- REQUIRED skills are strictly necessary to satisfy the query.
- PREFERRED skills strengthen the outcome but are not strictly necessary.
- For each skill returned include:
  - weight: 0.0 - 1.0 (how central the skill is)
  - confidence: 0.0 - 1.0 (your confidence it's relevant)
  - importance: 0.0 - 1.0 (how critical for THIS query)
  - rationale: 1-2 short sentences
- Avoid always choosing 1.0.
- Return ONLY valid JSON.

Return JSON exactly in this shape:
{{
  "outcome_reasoning": "1-3 sentences describing the inferred need",
  "overall_confidence": 0.0,
  "required": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}],
  "preferred": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}]
}}

Candidate Skills (choose from these EXACT strings):
{json.dumps(skill_list, ensure_ascii=False)}
""".strip()

    def _ai_repair_json(self, query: str, raw_text: str) -> Optional[dict]:
        """
        If the model returns non-JSON or malformed JSON, ask it to repair into the exact schema.
        """
        prompt = f"""
The following response was supposed to be JSON but is malformed or includes extra text.

User query:
{query}

Bad response:
{raw_text}

Fix it and return ONLY valid JSON in this exact shape:
{{
  "outcome_reasoning": "1-3 sentences",
  "overall_confidence": 0.0,
  "required": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}],
  "preferred": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}]
}}

Rules:
- skills MUST be EXACT matches from this candidate list:
{json.dumps(self.skills, ensure_ascii=False)}
""".strip()

        content = self.client.chat(
            self.chat_model,
            [
                {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return _safe_json_extract(content)

    def _ai_topup_required(self, query: str, res: SkillInferenceResult) -> SkillInferenceResult:
        """
        AI-only top-up: ask model to add missing required skills (from catalogue) while keeping prior ones.
        No deterministic filling.
        """
        have_required = [s.skill for s in res.required]
        have_preferred = [s.skill for s in res.preferred]

        prompt = f"""
Your previous skill inference returned too few REQUIRED skills.

User query:
{query}

You MUST return at least {self.req_min} REQUIRED skills and at most {self.req_max}.
You MUST choose skills ONLY from the Candidate Skills list (exact strings).

Existing required:
{json.dumps(have_required, ensure_ascii=False)}

Existing preferred:
{json.dumps(have_preferred, ensure_ascii=False)}

Task:
- Add additional REQUIRED skills (only if necessary) to reach the minimum.
- Keep existing skills unless clearly wrong.
- Ensure preferred does not duplicate required.
- Output the full final JSON (same schema).

Return JSON exactly in this shape:
{{
  "outcome_reasoning": "1-3 sentences describing the inferred need",
  "overall_confidence": 0.0,
  "required": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}],
  "preferred": [{{"skill":"…","weight":0.0,"confidence":0.0,"importance":0.0,"rationale":"…"}}]
}}

Candidate Skills:
{json.dumps(self.skills, ensure_ascii=False)}
""".strip()

        content = self.client.chat(
            self.chat_model,
            [
                {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
        )

        data = _safe_json_extract(content) or {}
        return self._postprocess(query, data)

    def _postprocess(self, query: str, data: dict) -> SkillInferenceResult:
        def parse_list(items) -> List[InferredSkill]:
            if not isinstance(items, list):
                return []

            out: List[InferredSkill] = []
            seen = set()

            for obj in items:
                if not isinstance(obj, dict):
                    continue

                sk_raw = _norm(str(obj.get("skill", "")))
                if not sk_raw:
                    continue

                canon = self._allowed.get(sk_raw.lower())
                if not canon:
                    # Cannot score unknown skills against DB later, so we must drop.
                    continue

                key = canon.lower()
                if key in seen:
                    continue
                seen.add(key)

                w = _clamp01(obj.get("weight", 0.6))
                c = _clamp01(obj.get("confidence", 0.6))
                imp = _clamp01(obj.get("importance", 0.6))
                r = _norm(str(obj.get("rationale", "")))[:320] or "Relevant to the query."

                out.append(InferredSkill(skill=canon, weight=w, confidence=c, importance=imp, rationale=r))

            # Sort by combined signal
            out.sort(key=lambda x: (x.weight * x.importance * x.confidence), reverse=True)
            return out

        required = parse_list(data.get("required", []))[: self.req_max]
        preferred = parse_list(data.get("preferred", []))[: self.pref_max]

        # remove overlap (preferred cannot duplicate required)
        req_set = {r.skill.lower() for r in required}
        preferred = [p for p in preferred if p.skill.lower() not in req_set][: self.pref_max]

        # clamp confidences/importances slightly away from 1.0
        required = [
            InferredSkill(s.skill, s.weight, min(s.confidence, 0.95), min(s.importance, 0.95), s.rationale)
            for s in required
        ]
        preferred = [
            InferredSkill(s.skill, s.weight, min(s.confidence, 0.95), min(s.importance, 0.95), s.rationale)
            for s in preferred
        ]

        outcome = _norm(str(data.get("outcome_reasoning", ""))) or "Identify the skills needed to address the user’s request."
        overall = _clamp01(data.get("overall_confidence", self._compute_overall_conf(required)))
        if overall > 0.95:
            overall = 0.9

        return SkillInferenceResult(
            outcome_reasoning=outcome,
            overall_confidence=overall,
            required=required,
            preferred=preferred,
        )

    def _compute_overall_conf(self, required: List[InferredSkill]) -> float:
        if not required:
            return 0.25
        weighted = sum((r.confidence * r.importance) for r in required)
        weight_sum = sum((r.importance) for r in required) or 1.0
        avg = weighted / weight_sum
        return _clamp01(0.25 + 0.65 * avg)
