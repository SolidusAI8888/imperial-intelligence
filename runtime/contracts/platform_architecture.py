from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArchitectureLayer(str, Enum):
    HISTORICAL_SOURCE = "historical_source"
    KNOWLEDGE = "knowledge"
    HISTORICAL_EXPERIENCE = "historical_experience"
    MATCHING = "matching"
    PERSONA_RUNTIME = "persona_runtime"
    MASTER_CONSULTATION_REPORT = "master_consultation_report"
    CONTENT_RUNTIME = "content_runtime"


class LifePerspectiveMode(str, Enum):
    COMPLETE_LIFE = "complete_life"
    HISTORICAL_CUTOFF = "historical_cutoff"


class PersonaLifePerspective(BaseModel):
    """历史人物默认以完整人生视角参与咨询；仅显式历史模拟允许时间截断。"""

    model_config = ConfigDict(extra="forbid")

    mode: LifePerspectiveMode = LifePerspectiveMode.COMPLETE_LIFE
    cutoff_stage_id: str | None = None
    allow_retrospective_reflection: bool = True
    allow_future_knowledge_at_event_time: Literal[False] = False

    @model_validator(mode="after")
    def validate_temporal_integrity(self) -> "PersonaLifePerspective":
        if self.mode == LifePerspectiveMode.COMPLETE_LIFE and self.cutoff_stage_id is not None:
            raise ValueError("Complete-life perspective must not define a historical cutoff.")
        if self.mode == LifePerspectiveMode.HISTORICAL_CUTOFF and not self.cutoff_stage_id:
            raise ValueError("Historical-cutoff mode requires cutoff_stage_id.")
        return self


class UserContext(BaseModel):
    """仅保存影响经验迁移和匹配质量的必要背景，不改变历史事实。"""

    model_config = ConfigDict(extra="forbid")

    age_range: str | None = None
    career_stage: str | None = None
    family_status: str | None = None
    country_or_region: str | None = None
    cultural_context: str | None = None
    major_constraints: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    risk_preferences: list[str] = Field(default_factory=list)


class ConsultationArchitectureContract(BaseModel):
    """Architecture V1 frozen runtime invariants."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    architecture_frozen: Literal[True] = True
    history_first: Literal[True] = True
    experience_first: Literal[True] = True
    insight_next: Literal[True] = True
    advice_last: Literal[True] = True
    final_decision_owner: Literal["user"] = "user"
    source_of_historical_truth: Literal["historical_source_database"] = "historical_source_database"
    master_content_source: Literal["master_consultation_report"] = "master_consultation_report"
    default_life_perspective: PersonaLifePerspective = Field(default_factory=PersonaLifePerspective)
    required_layer_order: tuple[ArchitectureLayer, ...] = (
        ArchitectureLayer.HISTORICAL_SOURCE,
        ArchitectureLayer.KNOWLEDGE,
        ArchitectureLayer.HISTORICAL_EXPERIENCE,
        ArchitectureLayer.MATCHING,
        ArchitectureLayer.PERSONA_RUNTIME,
        ArchitectureLayer.MASTER_CONSULTATION_REPORT,
        ArchitectureLayer.CONTENT_RUNTIME,
    )

    @model_validator(mode="after")
    def validate_frozen_layer_order(self) -> "ConsultationArchitectureContract":
        expected = (
            ArchitectureLayer.HISTORICAL_SOURCE,
            ArchitectureLayer.KNOWLEDGE,
            ArchitectureLayer.HISTORICAL_EXPERIENCE,
            ArchitectureLayer.MATCHING,
            ArchitectureLayer.PERSONA_RUNTIME,
            ArchitectureLayer.MASTER_CONSULTATION_REPORT,
            ArchitectureLayer.CONTENT_RUNTIME,
        )
        if self.required_layer_order != expected:
            raise ValueError("Architecture V1 layer order is frozen and cannot be reordered.")
        return self


ARCHITECTURE_V1 = ConsultationArchitectureContract()
