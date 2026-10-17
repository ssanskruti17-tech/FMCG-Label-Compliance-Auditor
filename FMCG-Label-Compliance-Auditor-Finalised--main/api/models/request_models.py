from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ProductDataRequest(BaseModel):
    product_name: str = Field(default="Live Scanned Upload")
    category: str = Field(default="Uncategorized")
    claims: List[str] = Field(default_factory=list)
    ingredients: List[str] = Field(default_factory=list)
    nutrition: Dict[str, Any] = Field(default_factory=dict)
    declared_basis: Optional[str] = None
    serving_size_g: Optional[float] = None
    front_uploaded: bool = False
    back_uploaded: bool = False

class AuditResultRequest(BaseModel):
    rule_id: str
    status: str
    claim: str
    evidence: str
    message: str
