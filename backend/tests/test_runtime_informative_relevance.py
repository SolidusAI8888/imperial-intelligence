from app.models.knowledge import Insight
from app.services.runtime_candidate_assessment import _insight_relevant_to_question


def _insight(statement: str, *, applies_when: list[str] | None = None) -> Insight:
    return Insight(
        insight_id="INS-TEST-0001",
        research_id="R-TEST",
        statement=statement,
        derived_from_heus=["HEU-TEST-0001"],
        applies_when=applies_when or [],
        limits=[],
        status="reviewed",
    )


def test_generic_advisory_words_do_not_create_false_relevance() -> None:
    question = "团队反复犯错时，领导者应该先换人还是先改制度？"
    unrelated = _insight("边疆补给出现问题时，主帅应该先稳定粮道。")

    assert _insight_relevant_to_question(question, unrelated) is False


def test_informative_topic_overlap_still_creates_relevance() -> None:
    question = "团队反复犯错时，领导者应该先换人还是先改制度？"
    related = _insight("制度设计失灵时，应先查清责任边界。", applies_when=["团队制度反复失效"])

    assert _insight_relevant_to_question(question, related) is True
