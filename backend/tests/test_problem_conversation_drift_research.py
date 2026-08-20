from dataclasses import replace

from app.services.problem_conversation_service import continue_problem_conversation
from app.services.problem_knowledge_repository import ProblemKnowledgeSpec


def _spec() -> ProblemKnowledgeSpec:
    from pathlib import Path

    return ProblemKnowledgeSpec(
        problem_id="Q-CAREER-001",
        raw_question="一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
        normalized_question="职业低谷中的坚持与转向",
        retrieval_dimensions=("career transition", "persistence versus change"),
        candidate_profile_path=Path("unused.yaml"),
        reusable_layers=("HER", "HEU"),
        problem_specific_layers=("insight_selection", "candidate_scoring", "responder_eligibility"),
        status="reviewed",
    )


def test_drift_turn_carries_research_package(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_conversation_service.load_problem_spec",
        lambda _: _spec(),
    )

    fake_package = type(
        "Package",
        (),
        {
            "proposed_problem_id": "Q-RESEARCH-ABCDEF123456",
            "raw_question": "宋代的财政制度如何设计？",
            "normalized_question": "宋代的财政制度如何设计？",
            "candidates": (),
            "status": "research_package_requires_human_review",
            "can_render_answer": False,
            "required_next_gate": "review",
        },
    )()
    monkeypatch.setattr(
        "app.services.problem_conversation_service.build_problem_research_package",
        lambda question, candidate_limit=20: fake_package,
    )

    result = continue_problem_conversation(
        "Q-CAREER-001",
        "宋代的财政制度如何设计？",
        continuity_threshold=0.30,
    )

    assert result.route == "new_problem_required"
    assert result.requires_new_problem is True
    assert result.research_package is fake_package
    assert result.research_package.proposed_problem_id == "Q-RESEARCH-ABCDEF123456"


def test_related_followup_does_not_create_research_package(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_conversation_service.load_problem_spec",
        lambda _: _spec(),
    )

    rendered = type(
        "Answer",
        (),
        {
            "person_id": "tang_taizong",
            "historical_voice": "answer",
            "modern_translation": "modern",
            "cautions": ("caution",),
            "evidence_ids": ("E-1",),
            "insight_ids": ("I-1",),
        },
    )()
    monkeypatch.setattr(
        "app.services.problem_conversation_service.render_grounded_answer",
        lambda problem_id, question=None: rendered,
    )
    called = {"research": 0}

    def _research(*args, **kwargs):
        called["research"] += 1
        raise AssertionError("related follow-up should not start new-problem research")

    monkeypatch.setattr(
        "app.services.problem_conversation_service.build_problem_research_package",
        _research,
    )

    result = continue_problem_conversation(
        "Q-CAREER-001",
        "你刚才说的这个判断，具体是什么意思？",
    )

    assert result.route == "continue_current_responder"
    assert result.research_package is None
    assert called["research"] == 0
