from runtime.contracts.persona_runtime import (
    EvidencePolicy,
    HistoricalKnowledgeBoundary,
    PersonaRuntimeContext,
    RuntimeMode,
)


def test_create_tang_taizong_runtime_context() -> None:
    context = PersonaRuntimeContext(
        emperor_id="tang_taizong",
        persona_package_version="0.1.0",
        historical_stage_id="zhenguan_15",
        historical_stage_name="贞观十五年",
        runtime_mode=RuntimeMode.CONSULTATION,
        evidence_policy=EvidencePolicy.BALANCED,
        knowledge_boundary=HistoricalKnowledgeBoundary(
            cutoff_date="641-12-31",
            allow_posthumous_knowledge=False,
            allow_modern_context=True,
            allow_modern_terms=True,
        ),
        active_traits=[
            "strategic_pragmatism",
            "receptiveness_to_remonstrance",
        ],
        emotional_state={
            "calm": 0.8,
            "concern": 0.3,
            "resolve": 0.7,
        },
    )

    assert context.emperor_id == "tang_taizong"
    assert context.historical_stage_id == "zhenguan_15"
    assert context.runtime_mode == RuntimeMode.CONSULTATION
    assert context.evidence_policy == EvidencePolicy.BALANCED
    assert context.knowledge_boundary.allow_posthumous_knowledge is False
    assert context.emotional_state["calm"] == 0.8
    assert context.runtime_id is not None
    assert context.created_at.tzinfo is not None