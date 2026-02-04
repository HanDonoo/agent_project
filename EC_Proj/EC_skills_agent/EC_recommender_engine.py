from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set, Any

from .ai_client import AIClient

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
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        employees = [dict(r) for r in conn.execute("SELECT * FROM employees WHERE is_active = 1").fetchall()]

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

def load_employee_all_skills(db_path: str, employee_id: int) -> List[dict]:
    """
    Returns ALL skills for a single employee from the DB.
    Shape matches what your formatter expects: [{"skill": "...", "level": "..."}]
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.name AS skill, es.proficiency_level
            FROM employee_skills es
            JOIN skills s ON s.id = es.skill_id
            WHERE es.employee_id = ?
            ORDER BY s.name
            """,
            (employee_id,),
        ).fetchall()

    return [{"skill": r["skill"], "level": r["proficiency_level"]} for r in rows]

# =======================
# Complexity Profile (AIClient-based)
# =======================

def infer_complexity_profile(
    client: AIClient,
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
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No extra text."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        timeout=240,
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

def _match_ratio(emp_level: Optional[str], target_level: str) -> float:
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
    query: str,
    reqs: SkillRequirements,
    profile: Any,
    top_n: int = 20,
    strict_required: bool = False,
    preferred_multiplier: float = 0.33,
    # NEW: gate for sanity
    min_required_signal: float = 0.34,  # require ~>= 1/3 of required skills hit at ANY level (or better)
) -> List[EmployeeMatch]:
    """
    Key behavioural change (small but critical):
      - We now FILTER OUT employees who show no evidence on required skills.
      - This prevents "Account Manager recommended for Deep Learning engineer" when they have None/None on required skills.
    """
    employees, emp_skills = load_employee_skill_matrix(db_path)

    target_req = {t.skill.lower(): t for t in (getattr(profile, "targets_required", None) or [])}
    target_pref = {t.skill.lower(): t for t in (getattr(profile, "targets_preferred", None) or [])}

    required_list = reqs.required or []
    preferred_list = reqs.preferred or []

    results: List[EmployeeMatch] = []

    for e in employees:
        eid = int(e["id"])
        skills = emp_skills.get(eid, {})

        total = 0.0
        required_hits_at_target = 0     # match >= 1.0
        required_hits_any = 0           # emp has the skill at ANY prof level
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
                missing_penalty += weight * (0.8 + float(getattr(profile, "complexity_score", 0.5) or 0.5))
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

            # has *some* evidence on this required skill
            required_hits_any += 1

            m = _match_ratio(emp_level, target_level)
            if m >= 1.0:
                required_hits_at_target += 1

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

            m = _match_ratio(emp_level, target_level)
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

        # Coverage measures
        coverage_required_at_target = required_hits_at_target / max(1, len(required_list))
        coverage_required_any = required_hits_any / max(1, len(required_list))
        coverage_preferred = preferred_hits / max(1, len(preferred_list))

        # STRICT filter stays the same
        if strict_required and coverage_required_at_target < 1.0:
            continue

        # NEW: sanity gate — must have SOME required evidence
        if required_list and coverage_required_any < min_required_signal:
            continue

        # Re-weight total by coverage at target (keeps behaviour consistent but less noisy)
        total *= (0.7 + 0.3 * coverage_required_at_target)

        results.append(
            EmployeeMatch(
                employee_id=eid,
                formal_name=e["formal_name"],
                email_address=e["email_address"],
                position_title=e["position_title"],
                team=e.get("team"),
                total_score=round(total, 6),
                coverage_required=round(coverage_required_at_target, 3),
                coverage_preferred=round(coverage_preferred, 3),
                reasoning=f"required_at_target={coverage_required_at_target:.2f}, required_any={coverage_required_any:.2f}, preferred={coverage_preferred:.2f}",
                matched_skills=matched,
            )
        )

    results.sort(key=lambda x: x.total_score, reverse=True)
    return results[:top_n]


# =======================
# SET-COVER TEAM PICKER
# =======================

def employee_required_coverage_set(emp: EmployeeMatch) -> Set[str]:
    return {
        str(m.get("skill", "")).lower().strip()
        for m in (emp.matched_skills or [])
        if m.get("type") == "required" and float(m.get("match", 0.0) or 0.0) >= 1.0
    }


def recommend_team_for_required_coverage(
    candidates: List[EmployeeMatch],
    reqs: SkillRequirements,
    max_team_size: int = 3,
) -> Tuple[List[EmployeeMatch], float, List[str]]:
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
    return round(sum(m.total_score for m in (team or [])), 6)
