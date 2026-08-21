from typing import Literal
from pydantic import BaseModel, Field

from app.models.api import ConversationMessage, ProblemResearchPackageResponse


class RuntimeConversationRequest(BaseModel):
    original_question: str = Field(min_length=2, max_length=4000)
    question: str = Field(min_length=2, max_length=4000)
    previous_person_id: str | None = Field(default=None, max_length=128)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=20)
    candidate_limit: int = Field(default=20, ge=1, le=50)


class RuntimeConversationResponse(BaseModel):
    original_problem_id: str
    active_problem_id: str
    person_id: str | None = None
    previous_person_id: str | None = None
    user_question: str
    route: Literal[
        "continue_current_runtime_responder",
        "drift_reselected_runtime_responder",
        "drift_requires_new_problem_research",
    ]
    route_reason: str
    responder_switched: bool
    historical_voice: str | None = None
    modern_translation: str | None = None
    cautions: list[str]
    evidence_ids: list[str]
    insight_ids: list[str]
    voice_evidence_ids: list[str] = Field(default_factory=list)
    research_package: ProblemResearchPackageResponse | None = None
    status: Literal[
        "continued_with_runtime_grounded_responder",
        "runtime_problem_drift_reselected_and_answered",
        "runtime_problem_drift_requires_research",
    ]
