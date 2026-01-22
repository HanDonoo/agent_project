from EC_skills_interpreter_engine import SkillInferenceEngine

engine = SkillInferenceEngine(
    db_path="data/employee_directory_200_mock.db",
    ollama_base_url="http://localhost:11434",
    chat_model="llama3.1:8b",
    embed_model="nomic-embed-text",
    shortlist_k=60,
    required_range=(3, 10),
    preferred_range=(2, 10),
)

query = "I want to learn about deep learning to be able to implement it in my team"
res = engine.infer(query)

print("Outcome:", res.outcome_reasoning)
print("Overall confidence:", res.overall_confidence)

print("\nRequired:")
for s in res.required:
    print(f"- {s.skill} (w={s.weight:.2f}, c={s.confidence:.2f}) :: {s.rationale}")

print("\nPreferred:")
for s in res.preferred:
    print(f"- {s.skill} (w={s.weight:.2f}, c={s.confidence:.2f}) :: {s.rationale}")
