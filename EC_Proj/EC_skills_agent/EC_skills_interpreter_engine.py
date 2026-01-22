"""
EC_skills_interpreter_engine.py

Updated Skill inference engine (Ollama-only) — DEBUG MODE: NO SHORTLISTING

Changes in this update:
- Each inferred skill now carries an `importance` (0..1) assigned by the LLM
  — this represents how critical the skill is for this specific query.
- Prompt asks the LLM to return importance for each skill.
- Stronger validation: LLM outputs are strictly mapped to DB catalogue entries
  (case-insensitive) and unknown skills are dropped.
- Outputs are clamped and post-processed; minimal top-up behavior remains for debug.
- Sorting of returned skills uses (weight * importance * confidence).
- No shortlisting: the full DB skills catalogue is provided to the LLM
  (debug mode). Replace candidate construction to re-enable shortlist retrieval.

Usage:
  engine = SkillInferenceEngine(db_path="data/employee_directory_200_mock.db", ...)
  res = engine.infer("find me deep learning engineers")
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
    weight: float          # 0..1 (model's notion of importance/role)
    confidence: float      # 0..1 (model confidence about this skill being relevant)
    importance: float      # 0..1 (how critical this skill is for THIS query)
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
    DEBUG MODE:
      query -> LLM over FULL DB skills catalogue (no shortlist)

    Guardrails:
      - LLM must choose only from candidate list (the full DB list)
      - Output must be JSON
      - Enforce counts and clamp values
      - Each returned skill must include an `importance` 0..1
    """

    def __init__(
        self,
        *,
        db_path: str,
        ollama_base_url: str = "http://localhost:11434",
        chat_model: str = "llama3.1:8b",
        embed_model: str = "nomic-embed-text",   # unused in debug mode
        shortlist_k: int = 60,                   # unused in debug mode
        required_range: Tuple[int, int] = (1, 10),
        preferred_range: Tuple[int, int] = (0, 10),
    ):
        self.db_path = db_path
        self.client = OllamaClient(ollama_base_url)
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.shortlist_k = shortlist_k

        self.req_min, self.req_max = required_range
        self.pref_min, self.pref_max = preferred_range

        self.skills = load_skills_from_db(db_path)

    def infer(self, query: str) -> SkillInferenceResult:
        query = _norm(query)
        if not query:
            raise ValueError("Query must be non-empty.")

        # ==========================================================
        # DEBUG: NO SHORTLISTING — use FULL DB catalogue as candidates
        # ==========================================================
        candidates = [(skill, 1.0) for skill in self.skills]  # (skill_name, score)

        prompt = self._build_prompt(query, candidates)
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
            return self._fallback(reason="LLM did not return parseable JSON.")

        return self._postprocess(query, candidates, data)

    def _build_prompt(self, query: str, candidates: List[Tuple[str, float]]) -> str:
        """
        Provide the full canonical candidate list and require the LLM to pick only from it.
        We now request an `importance` value (0.0-1.0) per skill representing how critical
        that skill is for this specific query.
        """
        skill_list = [s for (s, _score) in candidates]

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
  - weight: 0.0 - 1.0 (how central the skill is to the role)
  - confidence: 0.0 - 1.0 (your confidence the skill is relevant)
  - importance: 0.0 - 1.0 (how critical this skill is for THIS query; higher -> missing this skill should be penalized more)
  - rationale: 1-2 short sentences
- Weights, confidences, and importances must be numeric in 0..1; avoid 1.0 unless clearly exact.
- Return ONLY valid JSON that exactly follows the schema below. No extra text.

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

    def _postprocess(
        self,
        query: str,
        candidates: List[Tuple[str, float]],
        data: dict,
    ) -> SkillInferenceResult:
        allowed = {s.lower(): s for (s, _score) in candidates}

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

                canon = allowed.get(sk_raw.lower())
                if not canon:
                    # unknown skill - ignore (we require exact matches)
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

            # Sort by combined signal (weight * importance * confidence) so most important/strong items come first
            out.sort(key=lambda x: (x.weight * x.importance * x.confidence), reverse=True)
            return out

        required = parse_list(data.get("required", []))[: self.req_max]
        preferred = parse_list(data.get("preferred", []))[: self.pref_max]

        # remove overlap (preferred cannot duplicate required)
        req_set = {r.skill.lower() for r in required}
        preferred = [p for p in preferred if p.skill.lower() not in req_set][: self.pref_max]

        # ensure minimum required count (top up from catalogue if LLM under-returns)
        if len(required) < self.req_min:
            required = self._topup_required(required)

        # clamp confidences a bit (avoid absolute 1.0)
        required = [
            InferredSkill(s.skill, s.weight, min(s.confidence, 0.95), min(s.importance, 0.95), s.rationale)
            for s in required
        ]
        preferred = [
            InferredSkill(s.skill, s.weight, min(s.confidence, 0.95), min(s.importance, 0.95), s.rationale)
            for s in preferred
        ]

        outcome = _norm(str(data.get("outcome_reasoning", ""))) or "Identify the skills needed to successfully address the user’s request."
        overall = _clamp01(data.get("overall_confidence", self._compute_overall_conf(required)))
        if overall > 0.95:
            overall = 0.9

        return SkillInferenceResult(
            outcome_reasoning=outcome,
            overall_confidence=overall,
            required=required,
            preferred=preferred,
        )

    def _topup_required(self, required: List[InferredSkill]) -> List[InferredSkill]:
        """
        If the LLM returns too few required skills, fill from the start of the catalogue.
        (Debug-only behaviour; production should fill from retrieval / shortlist.)
        """
        have = {r.skill.lower() for r in required}
        for s in self.skills:
            if len(required) >= self.req_min:
                break
            if s.lower() in have:
                continue
            required.append(
                InferredSkill(
                    skill=s,
                    weight=0.55,
                    confidence=0.55,
                    importance=0.55,
                    rationale="Added to meet minimum required skills (debug top-up).",
                )
            )
            have.add(s.lower())
        return required[: self.req_max]

    def _compute_overall_conf(self, required: List[InferredSkill]) -> float:
        if not required:
            return 0.25
        # weigh skills by their importance when computing overall confidence
        weighted = sum((r.confidence * r.importance) for r in required)
        weight_sum = sum((r.importance) for r in required) or 1.0
        avg = weighted / weight_sum
        return _clamp01(0.25 + 0.65 * avg)

    def _fallback(self, reason: str) -> SkillInferenceResult:
        required = [
            InferredSkill(skill=self.skills[0], weight=0.6, confidence=0.5, importance=0.5, rationale=reason)
        ] if self.skills else []
        return SkillInferenceResult(
            outcome_reasoning="Fallback: unable to parse model output; returning minimal required skills.",
            overall_confidence=0.3,
            required=required,
            preferred=[],
        )
