"""

from EC_skills_interpreter_engine import SkillInferenceEngine
from EC_recommender_engine import (
    OllamaClient,
    infer_complexity_profile,
    recommend_top_candidates,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
)

DB_PATH = "data/employee_directory_200_mock.db"
OLLAMA = "http://localhost:11434"
CHAT_MODEL = "llama3.1:8b"

QUERIES = [
    "find me deep learning engineers",
    "evaluate the strategic, financial, and operational implications of adopting deep learning across the organisation",
]

def run_query(q: str):
    skills_engine = SkillInferenceEngine(db_path=DB_PATH, ollama_base_url=OLLAMA, chat_model=CHAT_MODEL)
    res = skills_engine.infer(q)

    reqs = SkillRequirements(
        outcome_reasoning=res.outcome_reasoning,
        overall_confidence=res.overall_confidence,
        required=[RequiredSkill(s.skill, s.weight, s.confidence, s.rationale) for s in res.required],
        preferred=[PreferredSkill(s.skill, s.weight, s.confidence, s.rationale) for s in res.preferred],
    )

    client = OllamaClient(OLLAMA)
    profile = infer_complexity_profile(client, CHAT_MODEL, q, reqs)

    top5 = recommend_top_candidates(DB_PATH, q, reqs, profile, top_n=5, strict_required=False)

    print("\n" + "="*80)
    print("QUERY:", q)
    print(f"COMPLEXITY: {profile.complexity_label} ({profile.complexity_score:.2f})")
    print("TOP 5 EMAILS:", [m.email_address for m in top5])

def main():
    for q in QUERIES:
        run_query(q)

if __name__ == "__main__":
    main()


"""

"""
from EC_skills_interpreter_engine import SkillInferenceEngine
from EC_recommender_engine import (
    OllamaClient,
    infer_complexity_profile,
    recommend_top_candidates,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
)

DB_PATH = "data/employee_directory_200_mock.db"
OLLAMA = "http://localhost:11434"
CHAT_MODEL = "llama3.1:8b"

def main():
    query = "find me deep learning engineers"

    # 1) Infer required/preferred skills
    skills_engine = SkillInferenceEngine(
        db_path=DB_PATH,
        ollama_base_url=OLLAMA,
        chat_model=CHAT_MODEL,
        # shortlist is bypassed in your debug version (full catalogue)
    )
    res = skills_engine.infer(query)

    reqs = SkillRequirements(
        outcome_reasoning=res.outcome_reasoning,
        overall_confidence=res.overall_confidence,
        required=[RequiredSkill(s.skill, s.weight, s.confidence, s.rationale) for s in res.required],
        preferred=[PreferredSkill(s.skill, s.weight, s.confidence, s.rationale) for s in res.preferred],
    )

    # 2) Infer complexity + target proficiency per skill
    client = OllamaClient(OLLAMA)
    profile = infer_complexity_profile(client, CHAT_MODEL, query, reqs)

    # 3) Recommend
    top5 = recommend_top_candidates(
        db_path=DB_PATH,
        query=query,
        reqs=reqs,
        profile=profile,
        top_n=5,
        strict_required=False,
    )

    print("\n=== QUERY ===")
    print(query)

    print("\n=== SKILLS (REQUIRED) ===")
    for s in reqs.required:
        print(f"- {s.skill} (w={s.weight:.2f}, c={s.confidence:.2f})")

    print("\n=== SKILLS (PREFERRED) ===")
    for s in reqs.preferred:
        print(f"- {s.skill} (w={s.weight:.2f}, c={s.confidence:.2f})")

    print("\n=== COMPLEXITY ===")
    print(f"score={profile.complexity_score:.2f} label={profile.complexity_label}")
    print(profile.reasoning)

    print("\n=== TOP 5 ===")
    for i, m in enumerate(top5, 1):
        print(f"\n#{i} {m.formal_name} ({m.email_address})")
        print(f"  Title: {m.position_title} | Team: {m.team}")
        print(f"  Score: {m.total_score} | Required coverage: {m.coverage_required} | Preferred coverage: {m.coverage_preferred}")

        # show strongest contributions
        contribs = [x for x in m.matched_skills if "contribution" in x]
        contribs.sort(key=lambda x: x["contribution"], reverse=True)
        for c in contribs[:6]:
            print(f"   - {c['type']}: {c['skill']} {c['employee_level']} vs {c['target_level']} "
                  f"(verified={c['verified']}) contrib={c['contribution']} match={c['match']}")

if __name__ == "__main__":
    main()

"""


from EC_skills_interpreter_engine import SkillInferenceEngine
from EC_recommender_engine import (
    OllamaClient,
    infer_complexity_profile,
    recommend_top_candidates,
    SkillRequirements,
    RequiredSkill,
    PreferredSkill,
)

DB_PATH = "data/employee_directory_200_mock.db"
OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.1:8b"


def run_query(query: str):
    print("\n" + "=" * 80)
    print("QUERY:", query)

    # --- 1) Skill inference ---
    skills_engine = SkillInferenceEngine(
        db_path=DB_PATH,
        ollama_base_url=OLLAMA_URL,
        chat_model=MODEL,
    )
    skills = skills_engine.infer(query)

    print("\nREQUIRED SKILLS:")
    for s in skills.required:
        print(f"- {s.skill} | weight={s.weight:.2f} | importance={s.importance:.2f}")

    print("\nPREFERRED SKILLS:")
    for s in skills.preferred:
        print(f"- {s.skill} | weight={s.weight:.2f} | importance={s.importance:.2f}")

    # --- 2) Complexity inference ---
    reqs = SkillRequirements(
        outcome_reasoning=skills.outcome_reasoning,
        overall_confidence=skills.overall_confidence,
        required=[
            RequiredSkill(s.skill, s.weight, s.confidence, s.rationale, s.importance)
            for s in skills.required
        ],
        preferred=[
            PreferredSkill(s.skill, s.weight, s.confidence, s.rationale, s.importance)
            for s in skills.preferred
        ],
    )

    client = OllamaClient(OLLAMA_URL)
    profile = infer_complexity_profile(client, MODEL, query, reqs)

    print("\nCOMPLEXITY:")
    print(f"- score: {profile.complexity_score:.2f}")
    print(f"- label: {profile.complexity_label}")
    print(profile.reasoning)

    # --- 3) Recommendation ---
    top = recommend_top_candidates(
        db_path=DB_PATH,
        query=query,
        reqs=reqs,
        profile=profile,
        top_n=3,
        strict_required=False,
    )

    print("\nTOP MATCHES:")
    for i, e in enumerate(top, 1):
        print(f"\n#{i} {e.formal_name} ({e.email_address})")
        print(f"  Score: {e.total_score}")
        print(f"  Required coverage: {e.coverage_required}")
        print(f"  Preferred coverage: {e.coverage_preferred}")

        # Show strongest contributions
        contribs = [x for x in e.matched_skills if "contribution" in x]
        contribs.sort(key=lambda x: x["contribution"], reverse=True)

        for c in contribs[:5]:
            print(
                f"   - {c['type']} | {c['skill']} | "
                f"{c['employee_level']} vs {c['target_level']} | "
                f"importance={c['effective_weight']}"
            )


if __name__ == "__main__":
    # SIMPLE QUERY
    run_query("I need someone to tell me what deep learning is")

    # COMPLEX QUERY
    run_query("Find me deep learning engineers")
