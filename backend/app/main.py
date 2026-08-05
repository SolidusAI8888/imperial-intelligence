from fastapi import FastAPI, HTTPException

from app.models.api import ConsultationRequest, ConsultationResponse
from app.services.persona_repository import PersonaRepository
from app.services.consultation_service import ConsultationService

app = FastAPI(
    title="帝王智库 API",
    version="0.1.0",
    description="中国历代帝王历史人格智能顾问平台后端",
)

repository = PersonaRepository()
consultation_service = ConsultationService(repository)


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
