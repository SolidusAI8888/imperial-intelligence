import pytest
from pydantic import ValidationError

from runtime.contracts.platform_architecture import (
    ARCHITECTURE_V1,
    ArchitectureLayer,
    ConsultationArchitectureContract,
    LifePerspectiveMode,
    PersonaLifePerspective,
)


def test_architecture_v1_is_frozen_and_history_first() -> None:
    assert ARCHITECTURE_V1.architecture_frozen is True
    assert ARCHITECTURE_V1.history_first is True
    assert ARCHITECTURE_V1.experience_first is True
    assert ARCHITECTURE_V1.insight_next is True
    assert ARCHITECTURE_V1.advice_last is True
    assert ARCHITECTURE_V1.final_decision_owner == "user"


def test_default_persona_uses_complete_life_perspective() -> None:
    perspective = PersonaLifePerspective()
    assert perspective.mode == LifePerspectiveMode.COMPLETE_LIFE
    assert perspective.cutoff_stage_id is None
    assert perspective.allow_retrospective_reflection is True
    assert perspective.allow_future_knowledge_at_event_time is False


def test_historical_cutoff_requires_explicit_stage() -> None:
    with pytest.raises(ValidationError):
        PersonaLifePerspective(mode=LifePerspectiveMode.HISTORICAL_CUTOFF)


def test_complete_life_cannot_have_cutoff() -> None:
    with pytest.raises(ValidationError):
        PersonaLifePerspective(
            mode=LifePerspectiveMode.COMPLETE_LIFE,
            cutoff_stage_id="zhenguan_15",
        )


def test_frozen_layer_order_cannot_be_reordered() -> None:
    with pytest.raises(ValidationError):
        ConsultationArchitectureContract(
            required_layer_order=(
                ArchitectureLayer.PERSONA_RUNTIME,
                ArchitectureLayer.HISTORICAL_SOURCE,
                ArchitectureLayer.KNOWLEDGE,
                ArchitectureLayer.HISTORICAL_EXPERIENCE,
                ArchitectureLayer.MATCHING,
                ArchitectureLayer.MASTER_CONSULTATION_REPORT,
                ArchitectureLayer.CONTENT_RUNTIME,
            )
        )
