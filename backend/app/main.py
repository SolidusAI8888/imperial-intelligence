from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

from app.models.api import (
    AutoConsultationResponse,
    ConsultationRequest,
    ConsultationResponse,
    ProblemConversationRequest,
    ProblemConversationResponse,
    ProblemDraftReadinessResponse,
    ProblemDraftRequest,
    ProblemDraftResponse,
    ProblemDraftReviewPacketResponse,
    ProblemGroundedAnswerResponse,
    PersonaVoiceReadinessResponse,
    PersonaVoiceCandidateRequest,
    PersonaVoiceCandidateResponse,
    PersonaVoiceReviewDecisionRequest,
    PersonaVoiceReviewDecisionResponse,
    PersonaVoiceReviewPacketResponse,
    PersonaVoiceReviewQueueResponse,
    ProblemPromotionRequest,
    ProblemPromotionResponse,
    ProblemResearchPackageResponse,
    ProblemResearchRequest,
)
from app.models.runtime_conversation import RuntimeConversationRequest, RuntimeConversationResponse
from app.services.auto_consultation_service import AutoConsultationService
from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.persona_repository import PersonaRepository
from app.services.persona_voice_readiness import inspect_persona_voice_readiness
from app.services.persona_voice_candidate import create_persona_voice_candidate
from app.services.persona_voice_review import (
    apply_persona_voice_review_decision,
    build_persona_voice_review_packet,
)
from app.services.persona_voice_review_queue import build_persona_voice_review_queue
from app.services.consultation_service import ConsultationService
from app.services.problem_conversation_service import continue_problem_conversation
from app.services.problem_draft_package import build_problem_draft_package, persist_problem_draft_package
from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness
from app.services.problem_draft_review_packet import build_problem_draft_review_packet
from app.services.problem_promotion_service import promote_problem_draft
from app.services.problem_research_package import build_problem_research_package
from app.services.runtime_candidate_assessment import assess_runtime_problem
from app.services.runtime_conversation_service import continue_runtime_conversation
from app.services.runtime_explainability import explain_runtime_problem

app = FastAPI(title="帝王智库 API", version="0.1.0", description="中国历代帝王历史人格智能顾问平台后端")
repository = PersonaRepository()
consultation_service = ConsultationService(repository)
auto_consultation_service = AutoConsultationService(consultation_service)


@app.get("/")
def root() -> dict:
    return {"name": "Imperial Intelligence", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/emperors")
def list_emperors() -> list[dict]:
    return repository.list_emperors()


@app.get("/emperors/{emperor_id}")
def get_emperor(emperor_id: str) -> dict:
    emperor = repository.get_manifest(emperor_id)
    if emperor is None:
        raise HTTPException(status_code=404, detail="Emperor not found")
    return emperor


@app.get("/emperors/{emperor_id}/persona")
def get_persona(emperor_id: str) -> dict:
    persona = repository.get_persona_package(emperor_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Emperor not found")
    return persona


@app.get(
    "/personas/{person_id}/voice-readiness",
    response_model=PersonaVoiceReadinessResponse,
)
def persona_voice_readiness(person_id: str) -> PersonaVoiceReadinessResponse:
    """Expose optional PVC coverage without granting factual answer permission."""

    try:
        return PersonaVoiceReadinessResponse.model_validate(
            asdict(inspect_persona_voice_readiness(person_id))
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/persona-voice/candidates",
    response_model=PersonaVoiceCandidateResponse,
)
def create_voice_candidate(
    request: PersonaVoiceCandidateRequest,
) -> PersonaVoiceCandidateResponse:
    try:
        result = create_persona_voice_candidate(**request.model_dump())
        return PersonaVoiceCandidateResponse.model_validate(asdict(result))
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/persona-voice/review-queue",
    response_model=PersonaVoiceReviewQueueResponse,
)
def persona_voice_review_queue(
    person_id: str | None = None,
    queue_state: Literal["all", "ready", "blocked", "attestation_repair"] = "all",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PersonaVoiceReviewQueueResponse:
    try:
        return PersonaVoiceReviewQueueResponse.model_validate(
            asdict(
                build_persona_voice_review_queue(
                    person_id=person_id,
                    queue_state=queue_state,
                    offset=offset,
                    limit=limit,
                )
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/persona-voice/{voice_evidence_id}/review-packet",
    response_model=PersonaVoiceReviewPacketResponse,
)
def persona_voice_review_packet(
    voice_evidence_id: str,
) -> PersonaVoiceReviewPacketResponse:
    try:
        return PersonaVoiceReviewPacketResponse.model_validate(
            asdict(build_persona_voice_review_packet(voice_evidence_id))
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/persona-voice/{voice_evidence_id}/review",
    response_model=PersonaVoiceReviewDecisionResponse,
)
def review_persona_voice_candidate(
    voice_evidence_id: str,
    request: PersonaVoiceReviewDecisionRequest,
) -> PersonaVoiceReviewDecisionResponse:
    try:
        result = apply_persona_voice_review_decision(
            voice_evidence_id,
            reviewer=request.reviewer,
            decision=request.decision,
            passage_link_verified=request.passage_link_verified,
            person_identity_verified=request.person_identity_verified,
            transcription_checked=request.transcription_checked,
            feature_tags_reviewed=request.feature_tags_reviewed,
            note=request.note,
            persist=request.persist,
        )
        return PersonaVoiceReviewDecisionResponse.model_validate(asdict(result))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/emperors/{emperor_id}/consult", response_model=ConsultationResponse)
def consult(emperor_id: str, request: ConsultationRequest) -> ConsultationResponse:
    if repository.get_manifest(emperor_id) is None:
        raise HTTPException(status_code=404, detail="Emperor not found")
    return consultation_service.consult(emperor_id, request)


@app.post("/consult/auto", response_model=AutoConsultationResponse | ProblemGroundedAnswerResponse | ProblemResearchPackageResponse)
def auto_consult(request: ConsultationRequest) -> AutoConsultationResponse | ProblemGroundedAnswerResponse | ProblemResearchPackageResponse:
    try:
        return auto_consultation_service.consult(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/research", response_model=ProblemResearchPackageResponse)
def research_new_problem(request: ProblemResearchRequest) -> ProblemResearchPackageResponse:
    try:
        return ProblemResearchPackageResponse.model_validate(asdict(build_problem_research_package(request.question, candidate_limit=request.candidate_limit)))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/assess")
def assess_new_problem(request: ProblemResearchRequest) -> dict:
    try:
        return asdict(assess_runtime_problem(request.question, candidate_limit=request.candidate_limit))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/explain")
def explain_new_problem(request: ProblemResearchRequest) -> dict:
    """Return a read-only audit trail for automatic runtime responder selection."""
    try:
        return asdict(explain_runtime_problem(request.question, candidate_limit=request.candidate_limit))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/drafts", response_model=ProblemDraftResponse)
def create_problem_draft(request: ProblemDraftRequest) -> ProblemDraftResponse:
    try:
        package = build_problem_draft_package(request.question, candidate_limit=request.candidate_limit)
        manifest_path, profile_path, persisted = package.manifest.relative_path, package.candidate_profile.relative_path, False
        if request.persist:
            written_manifest, written_profile = persist_problem_draft_package(package)
            manifest_path, profile_path, persisted = str(written_manifest), str(written_profile), True
        return ProblemDraftResponse(problem_id=package.problem_id, manifest_path=manifest_path, candidate_profile_path=profile_path, status=package.status, responder_eligible=package.responder_eligible, can_render_answer=package.can_render_answer, required_next_gate=package.required_next_gate, persisted=persisted)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/drafts/{draft_problem_id}/readiness", response_model=ProblemDraftReadinessResponse)
def problem_draft_readiness(draft_problem_id: str) -> ProblemDraftReadinessResponse:
    try:
        return ProblemDraftReadinessResponse.model_validate(asdict(inspect_problem_draft_readiness(draft_problem_id)))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/drafts/{draft_problem_id}/review-packet", response_model=ProblemDraftReviewPacketResponse)
def problem_draft_review_packet(draft_problem_id: str) -> ProblemDraftReviewPacketResponse:
    try:
        return ProblemDraftReviewPacketResponse.model_validate(asdict(build_problem_draft_review_packet(draft_problem_id)))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/promote", response_model=ProblemPromotionResponse)
def promote_reviewed_problem(request: ProblemPromotionRequest) -> ProblemPromotionResponse:
    try:
        return ProblemPromotionResponse.model_validate(asdict(promote_problem_draft(request.draft_problem_id, request.registered_problem_id, persist=request.persist)))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/{problem_id}/answer", response_model=ProblemGroundedAnswerResponse)
def grounded_problem_answer(problem_id: str) -> ProblemGroundedAnswerResponse:
    try:
        return ProblemGroundedAnswerResponse.model_validate(render_grounded_answer(problem_id).__dict__)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/runtime/{problem_id}/continue", response_model=RuntimeConversationResponse)
def continue_runtime_problem(problem_id: str, request: RuntimeConversationRequest) -> RuntimeConversationResponse:
    """Continue an unpersisted runtime Problem or automatically reselect after topic drift."""
    try:
        history = tuple(message.content for message in request.conversation_history)
        result = continue_runtime_conversation(problem_id, request.original_question, request.question, previous_person_id=request.previous_person_id, conversation_history=history, candidate_limit=request.candidate_limit)
        return RuntimeConversationResponse.model_validate(asdict(result))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/{problem_id}/continue", response_model=ProblemConversationResponse)
def continue_reviewed_problem(problem_id: str, request: ProblemConversationRequest) -> ProblemConversationResponse:
    try:
        history = tuple(message.content for message in request.conversation_history)
        result = continue_problem_conversation(problem_id, request.question, conversation_history=history, candidate_limit=request.candidate_limit)
        return ProblemConversationResponse.model_validate(asdict(result))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
