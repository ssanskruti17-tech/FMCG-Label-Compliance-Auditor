from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ParsedProductResponse(BaseModel):
    product_name: str
    category: str
    claims: List[str]
    ingredients: List[str]
    nutrition: Dict[str, Any]
    declared_basis: Optional[str]
    serving_size_g: Optional[float]
    front_uploaded: bool
    back_uploaded: bool

class AuditResultItem(BaseModel):
    rule_id: str
    status: str
    severity: str
    claim: str
    evidence: str
    message: str
    regulation: str

class ComplianceCheckResponse(BaseModel):
    overall_status: str
    passed_count: int
    flagged_count: int
    review_count: int
    results: List[AuditResultItem]

class RetrievedDoc(BaseModel):
    clause: str
    text: str

class RAGJustificationResponse(BaseModel):
    rule_id: str
    justification: str
    retrieved_docs: List[RetrievedDoc]

class HealthResponse(BaseModel):
    status: str
    ollama: str
    chromadb: str
