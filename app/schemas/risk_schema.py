from pydantic import BaseModel
from typing import Optional, Dict

class RiskRequest(BaseModel):
    applicant_data: Dict
    policy_type: str = "life"
    coverage_amount: Optional[float] = None
