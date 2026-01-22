from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests


# -----------------------
# Models
# -----------------------

PROF_ORDER = {"awareness": 1, "skilled": 2, "advanced": 3, "expert": 4}
PROF_LABELS = ["awareness", "skilled", "advanced", "expert"]


@dataclass(frozen=True)
class RequiredSkill:
    skill: str
    weight: float          # 0..1
    confidence: float      # 0..1
    rationale: str
    importance: float      # 0..1 (from SkillInferenceEngine)


@dataclass(frozen=True)
class PreferredSkill:
    skill: str
    weight: float
    confidence: float
    rationale: str
    importance: float      # 0..1 (from SkillInferenceEngine)


@dataclass(frozen=True)
class SkillRequirements:
    outcome_reasoning: str
    overall_confidence: float
    required: List[RequiredSkill]
    preferred: List[PreferredSkill]


@dataclass(frozen=True)
class SkillTarget:
    skill: str
    target_level: str          # awareness/skilled/advanced/expert
    target_confidence: float   # 0..1
    importance: float          # 0..1 (importance at required target depth)
    reasoning: str


@dataclass(frozen=True)
class ComplexityProfile:
    complexity_score: float            # 0..1
    complexity_label: str              # low/medium/high
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
    coverage_required: float           # 0..1 portion of required skills met (>= target)
    coverage_preferred: float          # 0..1 portion of preferred skills met (>= target)
    reasoning: str
    matched_skills: List[dict]


# -----------------------
# Ollama client
# -----------------------

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
        return data["message"]["content"]


def clamp01(x) -> float:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return max(0.0, min(1.0, v))


def safe_json(text: str) -> Optional[dict]:
    try:
        obj = json.loads(text.strip())
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# -----------------------
# DB access
# -----------------------

def load_employee_skill_matrix(db_path: str) -> Tuple[List[dict], Dict[int, Dict[str, dict]]]:
    """
    Returns:
      employees: list of employee rows dict
      emp_skills: dict[employee_id][skill_name_lower] = {"skill_name": str, "level": str, "verified": bool}
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        employees = [dict(r) for r in conn.execute("SELECT * FROM employees WHERE is_active = 1").fetchall()]

        rows = conn.execute(
            """
            SELECT es.employee_id, s.name AS skill_name, es.proficiency_level, es.is_verified
            FROM employee_skills es
            JOIN skills s ON s.id = es.skill_id
            """
        ).fetchall()

    emp_skills: Dict[int, Dict[str, dict]] = {}
    for r in rows:
        eid = int(r["employee_id"])
        name = str(r["skill_name"]).strip()
        key = name.lower()
        emp_skills.setdefault(eid, {})[key] = {
            "skill_name": name,
            "level": str(r["proficiency_level"]).lower().strip(),
            "verified": bool(r["is_verified"]),
        }
    return employees, emp_skills


# -----------------------
# AI: complexity + per-skill targets (+ target importance)
# -----------------------

def infer_complexity_profile(
    client: OllamaClient,
    chat_model: str,
    query: str,
    reqs: SkillRequirements,
) -> ComplexityProfile:
    """
    AI decides:
      - complexity_score 0..1
      - complexity_label low/medium/high
      - target proficiency per skill (required/preferred)
      - importance per skill at that target depth (0..1)
    """
    req_skills = [
        {"skill": s.skill, "weight": s.weight, "confidence": s.confidence, "importance": s.importance}
        for s in reqs.required
    ]
    pref_skills = [
        {"skill": s.skill, "weight": s.weight, "confidence": s.confidence, "importance": s.importance}
        for s in reqs.preferred
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
  - choose target_importance 0.0..1.0 indicating how critical meeting this target is
- For each preferred skill:
  - choose a helpful target proficiency (not strictly required)
  - choose target_importance 0.0..1.0 (usually lower than required)
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


# -----------------------
# Recommender
# -----------------------

def proficiency_match_score(emp_level: str, target_level: str) -> float:
    """
    Returns 0..1
    - 1.0 if employee >= target
    - partial if below target
    """
    e = PROF_ORDER.get((emp_level or "").lower(), 0)
    t = PROF_ORDER.get((target_level or "").lower(), 0)
    if t <= 0 or e <= 0:
        return 0.0
    if e >= t:
        return 1.0
    return max(0.0, e / t)


def required_match_value(emp_level: str, target_level: str) -> float:
    """
    Required scoring with NO bonus for exceeding target.
      - below target: 0..1
      - meets/exceeds target: 1.0
    """
    e = PROF_ORDER.get((emp_level or "").lower(), 0)
    t = PROF_ORDER.get((target_level or "").lower(), 0)
    if t <= 0 or e <= 0:
        return 0.0
    if e < t:
        return max(0.0, e / t)
    return 1.0



def recommend_top_candidates(
    db_path: str,
    query: str,
    reqs: SkillRequirements,
    profile: ComplexityProfile,
    top_n: int = 5,
    strict_required: bool = False,
    preferred_multiplier: float = 0.33,       # knob: preferred vs required ratio
    #required_exceed_alpha: float = 0.65,      # knob: bonus for exceeding required target
) -> List[EmployeeMatch]:
    employees, emp_skills = load_employee_skill_matrix(db_path)

    # Map targets by skill name (case-insensitive)
    target_req = {t.skill.lower(): t for t in profile.targets_required}
    target_pref = {t.skill.lower(): t for t in profile.targets_preferred}

    required_list = reqs.required
    preferred_list = reqs.preferred

    results: List[EmployeeMatch] = []

    for e in employees:
        eid = int(e["id"])
        skills = emp_skills.get(eid, {})

        required_hits = 0
        preferred_hits = 0

        matched_details: List[dict] = []
        total = 0.0

        missing_required_penalty = 0.0

        # ---- Required ----
        for rs in required_list:
            sk = rs.skill.strip()
            sk_key = sk.lower()
            target = target_req.get(sk_key)

            emp = skills.get(sk_key)  # ✅ case-insensitive
            target_level = target.target_level if target else "skilled"

            # Combine importance:
            # - rs.importance: skill-engine importance (query relevance)
            # - target.importance: complexity-engine importance (critical at target depth)
            skill_imp = clamp01(rs.importance)
            target_imp = clamp01(target.importance if target else 0.7)
            effective_weight = clamp01(rs.weight) * skill_imp * target_imp

            if emp is None:
                missing_required_penalty += (0.8 + 0.6 * profile.complexity_score) * effective_weight
                matched_details.append({
                    "skill": sk,
                    "type": "required",
                    "employee_level": None,
                    "target_level": target_level if target else None,
                    "verified": None,
                    "match": 0.0,
                    "skill_importance": round(skill_imp, 3),
                    "target_importance": round(target_imp, 3),
                    "effective_weight": round(effective_weight, 3),
                    "note": "missing",
                })
                continue

            emp_level = emp["level"]
            verified = bool(emp["verified"])

            m = required_match_value(emp_level, target_level)

            if PROF_ORDER.get(emp_level, 0) >= PROF_ORDER.get(target_level, 0):
                required_hits += 1

            v_bonus = 0.08 if verified else 0.0
            conf = clamp01(0.5 * rs.confidence + 0.5 * (target.target_confidence if target else 0.6))

            contrib = effective_weight * conf * (m + v_bonus)
            total += contrib

            matched_details.append({
                "skill": emp.get("skill_name", sk),
                "type": "required",
                "employee_level": emp_level,
                "target_level": target_level,
                "verified": verified,
                "match": round(m, 3),
                "skill_importance": round(skill_imp, 3),
                "target_importance": round(target_imp, 3),
                "effective_weight": round(effective_weight, 3),
                "contribution": round(contrib, 4),
            })

        # ---- Preferred ----
        for ps in preferred_list:
            sk = ps.skill.strip()
            sk_key = sk.lower()
            target = target_pref.get(sk_key)

            emp = skills.get(sk_key)
            if emp is None:
                continue

            emp_level = emp["level"]
            verified = bool(emp["verified"])
            target_level = target.target_level if target else "awareness"

            m = proficiency_match_score(emp_level, target_level)

            if PROF_ORDER.get(emp_level, 0) >= PROF_ORDER.get(target_level, 0):
                preferred_hits += 1

            v_bonus = 0.05 if verified else 0.0
            conf = clamp01(0.5 * ps.confidence + 0.5 * (target.target_confidence if target else 0.6))

            skill_imp = clamp01(ps.importance)
            target_imp = clamp01(target.importance if target else 0.5)
            effective_weight = clamp01(ps.weight) * skill_imp * target_imp

            contrib = preferred_multiplier * effective_weight * conf * (m + v_bonus)
            total += contrib

            matched_details.append({
                "skill": emp.get("skill_name", sk),
                "type": "preferred",
                "employee_level": emp_level,
                "target_level": target_level,
                "verified": verified,
                "match": round(m, 3),
                "skill_importance": round(skill_imp, 3),
                "target_importance": round(target_imp, 3),
                "effective_weight": round(effective_weight, 3),
                "contribution": round(contrib, 4),
            })

        total -= missing_required_penalty

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
                reasoning=(
                    f"required={coverage_required:.2f}, preferred={coverage_preferred:.2f}, "
                    f"complexity={profile.complexity_label} ({profile.complexity_score:.2f})."
                ),
                matched_skills=matched_details,
            )
        )

    results.sort(key=lambda x: x.total_score, reverse=True)
    return results[:top_n]
