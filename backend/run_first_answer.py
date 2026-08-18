from app.services.answer_pipeline import FIRST_QUESTION, generate_first_question_answer


if __name__ == "__main__":
    result = generate_first_question_answer(FIRST_QUESTION)
    print(result.answer)
    print("\n---\nEvidence:")
    for evidence_id in result.evidence_ids:
        print(f"- {evidence_id}")
