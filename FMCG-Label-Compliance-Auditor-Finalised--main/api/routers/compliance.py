from fastapi import APIRouter
from api.models.request_models import ProductDataRequest
from api.models.response_models import ComplianceCheckResponse
from api.services.compliance_service import evaluate_compliance

router = APIRouter(prefix="/compliance", tags=["Compliance"])

@router.post("/check", response_model=ComplianceCheckResponse)
def check_compliance(request: ProductDataRequest):
    product_data = request.model_dump()
    results = evaluate_compliance(product_data)
    return results
