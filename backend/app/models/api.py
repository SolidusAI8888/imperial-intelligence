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


class ProblemGroundedAnswerResponse(BaseModel):
    problem_id: str
    person_id: str
    question: str
    historical_voice: str
    modern_translation: str
    cautions: list[str]
    evidence_ids: list[str]
    insight_ids: list[str]
    voice_evidence_ids: list[str] = Field(default_factory=list)
    status: Literal[
        "rendered_from_reviewed_grounded_bundle",
        "rendered_from_runtime_reviewed_grounded_bundle",
    ]


class PersonaVoiceReadinessResponse(BaseModel):
    person_id: str
    total_records: int = Field(ge=0)
    candidate_records: int = Field(ge=0)
    reviewed_records: int = Field(ge=0)
    rejected_records: int = Field(ge=0)
    attested_reviewed_records: int = Field(ge=0)
    traceable_reviewed_records: int = Field(ge=0)
    runtime_style_ready: bool
    selected_voice_evidence_ids: list[str]
    applied_voice_evidence_ids: list[str]
    distinct_passage_count: int = Field(ge=0)
    distinct_source_count: int = Field(ge=0)
    total_evidence_weight: float = Field(ge=0)
    gate_blockers: list[str]
    voice_features: list[str]
    decision_features: list[str]
    rhetoric_features: list[str]
    fallback_reason: str | None = None
    status: Literal[
        "runtime_voice_style_ready",
        "neutral_voice_fallback_required",
    ]


class PersonaVoiceReviewPacketResponse(BaseModel):
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    current_status: Literal["candidate", "reviewed", "rejected"]
    canonical_passage_found: bool
    archived_file_integrity_verified: bool
    candidate_text_matches_archive: bool
    archived_passage_path: str | None = None
    feature_tag_count: int = Field(ge=0)
    requires_person_identity_review: Literal[True]
    approval_ready: bool
    blockers: list[str]
    status: Literal[
        "ready_for_explicit_human_voice_review",
        "blocked_before_human_voice_approval",
    ]


class PersonaVoiceReviewDecisionRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=200)
    decision: Literal["approved", "rejected"]
    passage_link_verified: bool = False
    person_identity_verified: bool = False
    transcription_checked: bool = False
    feature_tags_reviewed: bool = False
    note: str | None = Field(default=None, max_length=4000)
    persist: bool = False


class PersonaVoiceReviewDecisionResponse(BaseModel):
    voice_evidence_id: str
    reviewer: str
    decision: Literal["approved", "rejected"]
    resulting_status: Literal["reviewed", "rejected"]
    persisted: bool
    runtime_eligible_after_persist: bool
    status: Literal[
        "voice_review_decision_validated_style_only_no_answer_permission_change"
    ]


class PersonaVoiceCandidateRequest(BaseModel):
    person_id: str = Field(min_length=3, max_length=64)
    source_id: str = Field(min_length=3, max_length=80)
    passage_id: str = Field(min_length=5, max_length=120)
    source_kind: Literal[
        "imperial_verbatim",
        "vermilion_rescript",
        "imperial_edict",
        "court_diary",
        "memorial_response",
        "institutional_record",
        "later_compilation",
    ]
    contemporaneous: bool
    text: str = Field(min_length=12, max_length=12000)
    voice_features: list[str] = Field(default_factory=list, max_length=20)
    decision_features: list[str] = Field(default_factory=list, max_length=20)
    rhetoric_features: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0, le=1)
    proposed_by: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=4000)
    persist: bool = False


class PersonaVoiceCandidateResponse(BaseModel):
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    candidate_path: str
    persisted: bool
    review_required: Literal[True]
    runtime_eligible: Literal[False]
    status: Literal["persona_voice_candidate_requires_explicit_human_review"]


class PersonaVoiceReviewQueueItemResponse(BaseModel):
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    current_status: Literal["candidate", "reviewed"]
    approval_ready: bool
    blockers: list[str]
    review_attested: bool
    runtime_eligible: bool
    status: Literal[
        "candidate_ready_for_explicit_human_review",
        "candidate_blocked_before_human_review",
        "reviewed_record_requires_attestation_repair",
    ]


class PersonaVoiceReviewQueueResponse(BaseModel):
    total_records: int = Field(ge=0)
    candidate_records: int = Field(ge=0)
    ready_candidate_records: int = Field(ge=0)
    blocked_candidate_records: int = Field(ge=0)
    unattested_reviewed_records: int = Field(ge=0)
    runtime_eligible_reviewed_records: int = Field(ge=0)
    rejected_records: int = Field(ge=0)
    queue_state: Literal["all", "ready", "blocked", "attestation_repair"]
    filtered_records: int = Field(ge=0)
    returned_records: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    has_more: bool
    items: list[PersonaVoiceReviewQueueItemResponse]
    status: Literal["persona_voice_review_queue_read_only_no_automatic_approval"]


class ProblemResearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    candidate_limit: int = Field(default=20, ge=1, le=50)


class ProblemResearchCandidateResponse(BaseModel):
    person_id: str
    heu_ids: list[str]
    retrieval_score: float = Field(ge=0, le=1)
    review_priority: int = Field(ge=1)
    status: Literal["research_candidate_requires_problem_specific_review"]
    responder_eligible: Literal[False]


class ProblemResearchPackageResponse(BaseModel):
    proposed_problem_id: str
    raw_question: str
    normalized_question: str
    candidates: list[ProblemResearchCandidateResponse]
    status: Literal["research_package_requires_human_review"]
    can_render_answer: Literal[False]
    required_next_gate: str


class ProblemDraftRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    candidate_limit: int = Field(default=20, ge=1, le=50)
    persist: bool = False


class ProblemDraftResponse(BaseModel):
    problem_id: str
    manifest_path: str
    candidate_profile_path: str
    status: Literal["draft_package_requires_human_review"]
    responder_eligible: Literal[False]
    can_render_answer: Literal[False]
    required_next_gate: str
    persisted: bool


class ProblemDraftReadinessResponse(BaseModel):
    problem_id: str
    ready: bool
    blockers: list[str]
    status: str
    manifest_path: str
    candidate_profile_path: str


class ReviewHEUSummaryResponse(BaseModel):
    heu_id: str
    title: str
    challenge: str
    response_or_choice: list[str]
    experienced_outcome: list[str]
    explicit_reflection: list[str]
    interpretation: list[str]
    status: str


class ExistingInsightSuggestionResponse(BaseModel):
    insight_id: str
    statement: str
    derived_from_heus: list[str]
    applies_when: list[str]
    limits: list[str]
    status: Literal["suggestion_only_requires_problem_specific_review"]


class DraftCandidateReviewPacketResponse(BaseModel):
    person_id: str
    review_priority: int
    retrieval_score: float = Field(ge=0, le=1)
    recalled_heus: list[ReviewHEUSummaryResponse]
    existing_insight_suggestions: list[ExistingInsightSuggestionResponse]
    selected_insight_ids: list[str]
    candidate_score: float | None = None
    responder_eligible: bool
    status: Literal["review_packet_only_no_approval_side_effects"]


class ProblemDraftReviewPacketResponse(BaseModel):
    problem_id: str
    raw_question: str
    normalized_question: str
    retrieval_dimensions: list[str]
    candidates: list[DraftCandidateReviewPacketResponse]
    readiness_status: str
    readiness_blockers: list[str]
    status: Literal["human_review_packet_no_automatic_approval"]


class ProblemPromotionRequest(BaseModel):
    draft_problem_id: str = Field(min_length=1, max_length=64)
    registered_problem_id: str = Field(min_length=4, max_length=66)
    persist: bool = False


class ProblemPromotionResponse(BaseModel):
    source_draft_problem_id: str
    registered_problem_id: str
    manifest_path: str
    candidate_profile_path: str
    status: str
    persisted: bool


class ProblemConversationRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=20)
    candidate_limit: int = Field(default=20, ge=1, le=50)


class ProblemConversationResponse(BaseModel):
    problem_id: str
    person_id: str | None = None
    user_question: str
    route: Literal["continue_current_responder", "new_problem_required"]
    route_reason: str
    historical_voice: str | None = None
    modern_translation: str | None = None
    cautions: list[str]
    evidence_ids: list[str]
    insight_ids: list[str]
    voice_evidence_ids: list[str] = Field(default_factory=list)
    requires_new_problem: bool
    research_package: ProblemResearchPackageResponse | None = None
    status: Literal[
        "continued_with_reviewed_problem_responder",
        "problem_drift_requires_new_problem_research",
    ]
