from typing import Literal
from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ConsultationRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    user_context: str | None = Field(default=None, max_length=8000)
    emperor_stage_id: str | None = None
    response_mode: Literal["concise", "standard", "detailed"] = "standard"
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=20)


class EvidenceReference(BaseModel):
    evidence_id: str
    source_id: str
    summary: str
    confidence: float = Field(ge=0, le=1)


class AvatarDirective(BaseModel):
    listening_state: str
    thinking_action: str
    speaking_style: str
    emotion: str


class ConsultationResponse(BaseModel):
    emperor_id: str
    emperor_stage_id: str
    imperial_advice: str
    reasoning: list[str]
    historical_analogy: str
    modern_translation: str
    cautions: list[str]
    evidence: list[EvidenceReference]
    overall_confidence: float = Field(ge=0, le=1)
    avatar_directive: AvatarDirective
    status: Literal["prototype", "evidence_grounded"]


class CandidateRanking(BaseModel):
    emperor_id: str
    dynasty: Literal["han", "tang", "song"]
    score: float = Field(ge=0, le=1)
    rationale: str
    evidence_ids: list[str]


class CandidateScreening(BaseModel):
    emperor_id: str
    name: str
    title: str
    dynasty: Literal["han", "tang", "song"]
    eligible: bool
    score: float | None = Field(default=None, ge=0, le=1)
    reason: str


class AutoConsultationResponse(BaseModel):
    selected_emperor_id: str
    screened_emperors: list[CandidateScreening]
    rankings: list[CandidateRanking]
    consultation: ConsultationResponse
