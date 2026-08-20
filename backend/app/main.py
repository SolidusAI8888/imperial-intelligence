from dataclasses import asdict

from fastapi import FastAPI, HTTPException

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
    ProblemPromotionRequest,
    ProblemPromotionResponse,
    ProblemResearchPackageResponse,
    ProblemResearchRequest,
)
from app.services.auto_consultation_service import AutoConsultationService
from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.persona_repository import PersonaRepository
from app.services.consultation_service import ConsultationService
from app.services.problem_conversation_service import continue_problem_conversation
from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)
from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness
from app.services.problem_draft_review_packet import build_problem_draft_review_packet
from app.services.problem_promotion_service import promote_problem_draft
from app.services.problem_research_package import build_problem_research_package

app = FastAPI(
    title="帝王智库 API",
    version="0.1.0",
    description="中国历代帝王历史人格智能顾问平台后端",
)

repository = PersonaRepository()
consultation_service = ConsultationService(repository)
auto_consultation_service = AutoConsultationService(consultation_service)


@app.get("/")
def root() -> dict:
    return {
        "name": "Imperial Intelligence",
        "version": "0.1.0",
        "status": "running",
    }


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


@app.post("/emperors/{emperor_id}/consult", response_model=ConsultationResponse)
def consult(emperor_id: str, request: ConsultationRequest) -> ConsultationResponse:
    if repository.get_manifest(emperor_id) is None:
        raise HTTPException(status_code=404, detail="Emperor not found")
    return consultation_service.consult(emperor_id, request)


@app.post("/consult/auto", response_model=AutoConsultationResponse)
def auto_consult(request: ConsultationRequest) -> AutoConsultationResponse:
    try:
        return auto_consultation_service.consult(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/research", response_model=ProblemResearchPackageResponse)
def research_new_problem(request: ProblemResearchRequest) -> ProblemResearchPackageResponse:
    try:
        package = build_problem_research_package(
            request.question,
            candidate_limit=request.candidate_limit,
        )
        return ProblemResearchPackageResponse.model_validate(asdict(package))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/drafts", response_model=ProblemDraftResponse)
def create_problem_draft(request: ProblemDraftRequest) -> ProblemDraftResponse:
    try:
        package = build_problem_draft_package(
            request.question,
            candidate_limit=request.candidate_limit,
        )
        manifest_path = package.manifest.relative_path
        profile_path = package.candidate_profile.relative_path
        persisted = False
        if request.persist:
            written_manifest, written_profile = persist_problem_draft_package(package)
            manifest_path = str(written_manifest)
            profile_path = str(written_profile)
            persisted = True
        return ProblemDraftResponse(
            problem_id=package.problem_id,
            manifest_path=manifest_path,
            candidate_profile_path=profile_path,
            status=package.status,
            responder_eligible=package.responder_eligible,
            can_render_answer=package.can_render_answer,
            required_next_gate=package.required_next_gate,
            persisted=persisted,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/drafts/{draft_problem_id}/readiness", response_model=ProblemDraftReadinessResponse)
def problem_draft_readiness(draft_problem_id: str) -> ProblemDraftReadinessResponse:
    try:
        return ProblemDraftReadinessResponse.model_validate(
            asdict(inspect_problem_draft_readiness(draft_problem_id))
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/drafts/{draft_problem_id}/review-packet", response_model=ProblemDraftReviewPacketResponse)
def problem_draft_review_packet(draft_problem_id: str) -> ProblemDraftReviewPacketResponse:
    try:
        return ProblemDraftReviewPacketResponse.model_validate(
            asdict(build_problem_draft_review_packet(draft_problem_id))
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/promote", response_model=ProblemPromotionResponse)
def promote_reviewed_problem(request: ProblemPromotionRequest) -> ProblemPromotionResponse:
    try:
        return ProblemPromotionResponse.model_validate(
            asdict(
                promote_problem_draft(
                    request.draft_problem_id,
                    request.registered_problem_id,
                    persist=request.persist,
                )
            )
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/problems/{problem_id}/answer", response_model=ProblemGroundedAnswerResponse)
def grounded_problem_answer(problem_id: str) -> ProblemGroundedAnswerResponse:
    try:
        return ProblemGroundedAnswerResponse.model_validate(
            render_grounded_answer(problem_id).__dict__
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/problems/{problem_id}/continue", response_model=ProblemConversationResponse)
def continue_reviewed_problem(
    problem_id: str, request: ProblemConversationRequest
) -> ProblemConversationResponse:
    """Continue a reviewed problem or route semantic drift back to new-problem research."""
    try:
        history = tuple(message.content for message in request.conversation_history)
        result = continue_problem_conversation(
            problem_id,
            request.question,
            conversation_history=history,
        )
        return ProblemConversationResponse.model_validate(asdict(result))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
