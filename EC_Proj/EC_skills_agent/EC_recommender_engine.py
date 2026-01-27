from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

import requests


# =======================
# Constants
# =======================

PROF_ORDER = {"awareness": 1, "skilled": 2, "advanced": 3, "expert": 4}
PROF_LABELS = set(PROF_ORDER.keys())


# =======================
# Models
# =======================

@dataclass(frozen=True)
class RequiredSkill:
    skill: str
    weight: float
    confidence: float
    rationale: str
    importance: float


@dataclass(frozen=True)
class PreferredSkill:
    skill: str
    weight: float
    confidence: float
    rationale: str
    importance: float


@dataclass(frozen=True)
class SkillRequirements:
    outcome_reasoning: str
    overall_confidence: float
    required: List[RequiredSkill]
    preferred: List[PreferredSkill]


@dataclass(frozen=True)
class SkillTarget:
    skill: str
    target_level: str
    target_confidence: float
    importance: float
    reasoning: str


@dataclass(frozen=True)
class ComplexityProfile:
    complexity_score: float
    complexity_label: str
    targets_required: List[SkillTarget]
    targets_preferred: List[SkillTarget]
    reasoning: str


@dataclass(frozen=True)
class EmployeeMatch:
    employee_id: int
    formal_name: str
    email_address: str
    position_title: str
    team: Optional[str]
    total_score: float
    coverage_required: float
    coverage_preferred: float
    reasoning: str
    matched_skills: List[dict]


# =======================
# Ollama Client
# =======================

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
        return r.json()["message"]["content"]


# =======================
# Helpers
# =======================

def clamp01(x) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0


def safe_json(text: str) -> Optional[dict]:
    try:
        obj = json.loads((text or "").strip())
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# =======================
# DB Access
# =======================

def load_employee_skill_matrix(db_path: str) -> Tuple[List[dict], Dict[int, Dict[str, dict]]]:
    """
    Returns:
      employees: list of active employee rows dict
      emp_skills: dict[employee_id][skill_lower] = {"skill_name": str, "level": Optional[str], "verified": bool}

    Ensures skill level is ONLY set when valid (awareness/skilled/advanced/expert), else None.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        employees = [
            dict(r)
            for r in conn.execute("SELECT * FROM employees WHERE is_active = 1").fetchall()
        ]

        rows = conn.execute(
            """
            SELECT es.employee_id, s.name AS skill_name,
                   es.proficiency_level, es.is_verified
            FROM employee_skills es
            JOIN skills s ON s.id = es.skill_id
            """
        ).fetchall()

    emp_skills: Dict[int, Dict[str, dict]] = {}
    for r in rows:
        eid = int(r["employee_id"])
        skill_name = str(r["skill_name"]).strip()
        key = skill_name.lower()

        raw_level = r["proficiency_level"]
        level: Optional[str] = None
        if raw_level is not None:
            lvl = str(raw_level).lower().strip()
            if lvl in PROF_LABELS:
                level = lvl

        emp_skills.setdefault(eid, {})[key] = {
            "skill_name": skill_name,
            "level": level,
            "verified": bool(r["is_verified"]),
        }

    return employees, emp_skills


# =======================
# Complexity Profile
# =======================

def infer_complexity_profile(
    client: OllamaClient,
    chat_model: str,
    query: str,
    reqs: SkillRequirements,
) -> ComplexityProfile:
    req_skills = [
        {"skill": s.skill, "weight": s.weight, "confidence": s.confidence, "importance": s.importance}
        for s in (reqs.required or [])
    ]
    pref_skills = [
        {"skill": s.skill, "weight": s.weight, "confidence": s.confidence, "importance": s.importance}
        for s in (reqs.preferred or [])
    ]

    prompt = f"""
You are determining the depth of expertise required to answer a user query, and the importance of each skill at that depth.

Query:
{query}

Required skills:
{json.dumps(req_skills, ensure_ascii=False)}

Preferred skills:
{json.dumps(pref_skills, ensure_ascii=False)}

Proficiency levels (ordered):
awareness < skilled < advanced < expert

Rules:
- If the user asks for "explain/what is/overview", prefer lower target levels (awareness/skilled).
- If the user asks for "build/implement/engineer/production", prefer higher target levels (skilled/advanced/expert).
- For each required skill:
  - choose the MINIMUM target proficiency sufficient for the query
  - choose importance 0.0..1.0 indicating how critical meeting this target is
- For each preferred skill:
  - choose a helpful target proficiency (not strictly required)
  - choose importance 0.0..1.0 (usually lower than required)
- Provide complexity_score 0.0..1.0 (difficulty + ambiguity + cross-domain reasoning).
- Avoid always choosing expert; use expert only when strongly justified.
- Return ONLY valid JSON.

Return JSON exactly in this shape:
{{
  "complexity_score": 0.0,
  "complexity_label": "low|medium|high",
  "reasoning": "1-3 sentences",
  "targets_required": [
    {{"skill":"...","target_level":"awareness|skilled|advanced|expert","target_confidence":0.0,"importance":0.0,"reasoning":"..."}}
  ],
  "targets_preferred": [
    {{"skill":"...","target_level":"awareness|skilled|advanced|expert","target_confidence":0.0,"importance":0.0,"reasoning":"..."}}
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

    def parse_targets(key: str) -> List[SkillTarget]:
        out: List[SkillTarget] = []
        items = data.get(key, [])
        if not isinstance(items, list):
            return out

        allowed = {"awareness", "skilled", "advanced", "expert"}
        for it in items:
            if not isinstance(it, dict):
                continue
            sk = str(it.get("skill", "")).strip()
            lvl = str(it.get("target_level", "")).lower().strip()
            if not sk or lvl not in allowed:
                continue
            out.append(
                SkillTarget(
                    skill=sk,
                    target_level=lvl,
                    target_confidence=clamp01(it.get("target_confidence", 0.6)),
                    importance=clamp01(it.get("importance", 0.7)),
                    reasoning=str(it.get("reasoning", "")).strip()[:240] or "Target level for this query.",
                )
            )
        return out

    score = clamp01(data.get("complexity_score", 0.5))
    label = str(data.get("complexity_label", "medium")).lower().strip()
    if label not in {"low", "medium", "high"}:
        label = "medium"

    reasoning = str(data.get("reasoning", "")).strip() or "Complexity inferred from the query."

    return ComplexityProfile(
        complexity_score=score,
        complexity_label=label,
        targets_required=parse_targets("targets_required"),
        targets_preferred=parse_targets("targets_preferred"),
        reasoning=reasoning,
    )


# =======================
# Scoring
# =======================

def required_match_value(emp_level: Optional[str], target_level: str) -> float:
    if not emp_level or emp_level not in PROF_ORDER:
        return 0.0
    e = PROF_ORDER[emp_level]
    t = PROF_ORDER.get((target_level or "").lower().strip(), 0)
    if t <= 0:
        return 0.0
    return 1.0 if e >= t else e / t


def proficiency_match_score(emp_level: Optional[str], target_level: str) -> float:
    if not emp_level or emp_level not in PROF_ORDER:
        return 0.0
    e = PROF_ORDER[emp_level]
    t = PROF_ORDER.get((target_level or "").lower().strip(), 0)
    if t <= 0:
        return 0.0
    return 1.0 if e >= t else e / t


# =======================
# Candidate Recommender
# =======================

def recommend_top_candidates(
    db_path: str,
    query: str,  # kept for compatibility with main.py; not used directly in scoring
    reqs: SkillRequirements,
    profile: ComplexityProfile,
    top_n: int = 20,
    strict_required: bool = False,
    preferred_multiplier: float = 0.33,
) -> List[EmployeeMatch]:
    employees, emp_skills = load_employee_skill_matrix(db_path)

    target_req = {t.skill.lower(): t for t in (profile.targets_required or [])}
    target_pref = {t.skill.lower(): t for t in (profile.targets_preferred or [])}

    required_list = reqs.required or []
    preferred_list = reqs.preferred or []

    results: List[EmployeeMatch] = []

    for e in employees:
        eid = int(e["id"])
        skills = emp_skills.get(eid, {})

        total = 0.0
        required_hits = 0
        preferred_hits = 0
        missing_penalty = 0.0
        matched: List[dict] = []

        # ---------- REQUIRED ----------
        for rs in required_list:
            sk = rs.skill.strip()
            sk_key = sk.lower()

            target = target_req.get(sk_key)
            target_level = target.target_level if target else "skilled"

            emp = skills.get(sk_key)
            emp_level = emp["level"] if emp else None

            skill_imp = clamp01(rs.importance)
            target_imp = clamp01(target.importance if target else 0.7)
            weight = clamp01(rs.weight) * skill_imp * target_imp

            if not emp_level:
                missing_penalty += weight * (0.8 + float(getattr(profile, "complexity_score", 0.5)))
                matched.append(
                    {
                        "skill": sk,
                        "type": "required",
                        "employee_level": None,
                        "target_level": target_level,
                        "verified": None,
                        "match": 0.0,
                        "note": "missing",
                    }
                )
                continue

            m = required_match_value(emp_level, target_level)
            if m >= 1.0:
                required_hits += 1

            conf = clamp01(0.5 * rs.confidence + 0.5 * (target.target_confidence if target else 0.6))
            v_bonus = 0.08 if bool(emp.get("verified")) else 0.0

            contrib = weight * conf * (m + v_bonus)
            total += contrib

            matched.append(
                {
                    "skill": sk,
                    "type": "required",
                    "employee_level": emp_level,
                    "target_level": target_level,
                    "verified": bool(emp.get("verified")),
                    "match": round(m, 3),
                    "contribution": round(contrib, 4),
                }
            )

        # ---------- PREFERRED ----------
        for ps in preferred_list:
            sk = ps.skill.strip()
            sk_key = sk.lower()

            emp = skills.get(sk_key)
            emp_level = emp["level"] if emp else None
            if not emp_level:
                continue

            target = target_pref.get(sk_key)
            target_level = target.target_level if target else "awareness"

            m = proficiency_match_score(emp_level, target_level)
            if m >= 1.0:
                preferred_hits += 1

            skill_imp = clamp01(ps.importance)
            target_imp = clamp01(target.importance if target else 0.5)
            weight = clamp01(ps.weight) * skill_imp * target_imp

            conf = clamp01(0.5 * ps.confidence + 0.5 * (target.target_confidence if target else 0.6))
            v_bonus = 0.05 if bool(emp.get("verified")) else 0.0

            contrib = preferred_multiplier * weight * conf * (m + v_bonus)
            total += contrib

            matched.append(
                {
                    "skill": sk,
                    "type": "preferred",
                    "employee_level": emp_level,
                    "target_level": target_level,
                    "verified": bool(emp.get("verified")),
                    "match": round(m, 3),
                    "contribution": round(contrib, 4),
                }
            )

        total -= missing_penalty

        coverage_required = required_hits / max(1, len(required_list))
        coverage_preferred = preferred_hits / max(1, len(preferred_list))

        if strict_required and coverage_required < 1.0:
            continue

        total *= (0.7 + 0.3 * coverage_required)

        results.append(
            EmployeeMatch(
                employee_id=eid,
                formal_name=e["formal_name"],
                email_address=e["email_address"],
                position_title=e["position_title"],
                team=e.get("team"),
                total_score=round(total, 6),
                coverage_required=round(coverage_required, 3),
                coverage_preferred=round(coverage_preferred, 3),
                reasoning=f"required={coverage_required:.2f}, preferred={coverage_preferred:.2f}",
                matched_skills=matched,
            )
        )

    results.sort(key=lambda x: x.total_score, reverse=True)
    return results[:top_n]


# =======================
# TEAM COVERAGE (SET-COVER)
# =======================

def employee_required_coverage_set(emp: EmployeeMatch) -> Set[str]:
    """
    Skills this employee covers for REQUIRED items (meets/exceeds target).
    Uses match>=1.0 where available; falls back to comparing proficiency labels.
    """
    covered: Set[str] = set()
    for m in (emp.matched_skills or []):
        if m.get("type") != "required":
            continue
        sk = str(m.get("skill", "")).strip().lower()
        if not sk:
            continue

        match_val = m.get("match", None)
        if isinstance(match_val, (int, float)) and float(match_val) >= 1.0:
            covered.add(sk)
            continue

        emp_level = (m.get("employee_level") or "").lower().strip()
        tgt_level = (m.get("target_level") or "").lower().strip()
        if emp_level in PROF_ORDER and tgt_level in PROF_ORDER:
            if PROF_ORDER[emp_level] >= PROF_ORDER[tgt_level]:
                covered.add(sk)

    return covered


def recommend_team_for_required_coverage(
    candidates: List[EmployeeMatch],
    reqs: SkillRequirements,
    max_team_size: int = 3,
) -> Tuple[List[EmployeeMatch], float, List[str]]:
    """
    Greedy set-cover: select up to max_team_size people that cover as many required skills as possible.
    This is the mechanism that enables:
      "If required skills aren't covered by one person, recommend multiple people for the SAME workstream."
    """
    required = {s.skill.lower().strip() for s in (reqs.required or [])}
    covered: Set[str] = set()
    team: List[EmployeeMatch] = []

    remaining = list(candidates or [])
    coverage_map = {c.employee_id: employee_required_coverage_set(c) for c in remaining}

    while remaining and len(team) < max_team_size and covered != required:
        best = None
        best_gain = -1

        for c in remaining:
            gain = len((coverage_map[c.employee_id] & required) - covered)
            if gain > best_gain:
                best = c
                best_gain = gain
            elif gain == best_gain and best is not None and c.total_score > best.total_score:
                best = c

        if not best or best_gain <= 0:
            break

        team.append(best)
        covered |= (coverage_map[best.employee_id] & required)
        remaining.remove(best)

    coverage_ratio = len(covered) / max(1, len(required))
    missing = sorted(required - covered)
    return team, round(coverage_ratio, 3), missing


def workstream_team_score(team: List[EmployeeMatch]) -> float:
    """
    Simple team score: sum of member total_score.
    """
    return round(sum(m.total_score for m in (team or [])), 6)
