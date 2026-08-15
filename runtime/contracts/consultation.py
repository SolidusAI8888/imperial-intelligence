from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConsultationState(str, Enum):
    """一次咨询的生命周期状态。"""

    CREATED = "created"
    RECEIVED = "received"
    UNDERSTANDING = "understanding"
    CLARIFYING = "clarifying"
    MATCHING_EXPERIENCE = "matching_experience"
    RETRIEVING_EVIDENCE = "retrieving_evidence"
    REASONING = "reasoning"
    COMPOSING = "composing"
    RESPONDING = "responding"
    COMPLETED = "completed"


class ExperienceMatch(BaseModel):
    """与用户问题相匹配的、经史料支持的人生经验。"""

    model_config = ConfigDict(extra="forbid")

    experience_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    similarity_reasons: list[str] = Field(default_factory=list)
    important_differences: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class HistoricalReflection(BaseModel):
    """历史人格先回顾自己曾经历过的相似处境。"""

    model_config = ConfigDict(extra="forbid")

    has_comparable_experience: bool
    experience_matches: list[ExperienceMatch] = Field(default_factory=list)
    historical_context: list[str] = Field(default_factory=list)
    what_i_considered: list[str] = Field(default_factory=list)
    what_i_did: list[str] = Field(default_factory=list)
    historical_results: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_experience_truthfulness(self) -> "HistoricalReflection":
        if self.has_comparable_experience and not self.experience_matches:
            raise ValueError(
                "Comparable historical experience requires at least one verified experience match."
            )
        if not self.has_comparable_experience and self.experience_matches:
            raise ValueError(
                "Experience matches must be empty when no comparable experience exists."
            )
        return self


class ModernTransfer(BaseModel):
    """把历史经验迁移到现代处境，但不把历史情境等同于现代情境。"""

    model_config = ConfigDict(extra="forbid")

    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    transferable_principles: list[str] = Field(default_factory=list)
    non_transferable_elements: list[str] = Field(default_factory=list)
    modern_risks: list[str] = Field(default_factory=list)


class ReferenceAdvice(BaseModel):
    """历史人格基于自身经历给出的参考意见，而不是替用户做决定。"""

    model_config = ConfigDict(extra="forbid")

    if_i_were_you: str = Field(min_length=1)
    suggested_actions: list[str] = Field(default_factory=list)
    questions_for_self_reflection: list[str] = Field(default_factory=list)
    correction_or_exit_plan: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DecisionOwnership(BaseModel):
    """明确最终决定权属于提问者。"""

    model_config = ConfigDict(extra="forbid")

    final_decision_owner: Literal["user"] = "user"
    purpose: Literal["reference_and_inspiration"] = "reference_and_inspiration"
    statement: str = Field(
        default=(
            "这些意见来自历史人物自身经历的可借鉴部分，目的是提供参考并启发思考；"
            "最终决定由提问者结合自己的现实处境作出。"
        )
    )


class ConsultationOutput(BaseModel):
    """Historical Persona OS 的标准咨询输出。"""

    model_config = ConfigDict(extra="forbid")

    consultation_id: UUID = Field(default_factory=uuid4)
    persona_id: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    state: ConsultationState = ConsultationState.COMPLETED

    user_question: str = Field(min_length=1)
    historical_reflection: HistoricalReflection
    modern_transfer: ModernTransfer
    reference_advice: ReferenceAdvice
    decision_ownership: DecisionOwnership = Field(default_factory=DecisionOwnership)

    trace_event_ids: list[str] = Field(default_factory=list)
    trace_experience_ids: list[str] = Field(default_factory=list)
    trace_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_historical_experience_first(self) -> "ConsultationOutput":
        reflection = self.historical_reflection

        if reflection.has_comparable_experience:
            if not reflection.what_i_considered:
                raise ValueError(
                    "Modern reference advice cannot be produced before historical reasoning is recorded."
                )
            if not reflection.what_i_did:
                raise ValueError(
                    "Modern reference advice cannot be produced before historical action is recorded."
                )
            if not reflection.historical_results:
                raise ValueError(
                    "Modern reference advice cannot be produced before historical results are recorded."
                )
            if not reflection.lessons_learned:
                raise ValueError(
                    "Modern reference advice cannot be produced before historical lessons are recorded."
                )

        return self
