from fastapi import APIRouter
from api.models.request_models import AuditResultRequest
from api.models.response_models import RAGJustificationResponse
from api.services.rag_service import get_justification

router = APIRouter(prefix="/rag", tags=["RAG Legal Synthesis"])

@router.post("/justify", response_model=RAGJustificationResponse)
def justify_audit_result(request: AuditResultRequest):
    audit_result = request.model_dump()
    justification_data = get_justification(audit_result)
    return justification_data
