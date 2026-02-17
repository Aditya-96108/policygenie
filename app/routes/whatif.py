import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.risk_service import assess_risk
from app.schemas.response_schema import WhatIfResponse

router = APIRouter()
logger = logging.getLogger(__name__)

class WhatIfRequest(BaseModel):
    original_data: dict
    modified_data: dict
    policy_type: str = "life"

@router.post("/what-if", response_model=WhatIfResponse)
async def what_if_endpoint(request: WhatIfRequest):
    try:
        original_result = await assess_risk(
            request.original_data,
            request.policy_type,
            enable_fraud_check=False,
            enable_explainability=False
        )
        
        modified_result = await assess_risk(
            request.modified_data,
            request.policy_type,
            enable_fraud_check=False,
            enable_explainability=False
        )
        
        return WhatIfResponse(result={
            "original": original_result,
            "modified": modified_result,
            "changes": {
                "risk_score_delta": modified_result["risk_score"] - original_result["risk_score"],
                "premium_delta": {
                    "annual": (modified_result["premium_estimate"]["annual"] - 
                              original_result["premium_estimate"]["annual"]),
                    "monthly": (modified_result["premium_estimate"]["monthly"] - 
                               original_result["premium_estimate"]["monthly"])
                },
                "decision_changed": original_result["decision"] != modified_result["decision"]
            }
        })
    except Exception as e:
        logger.error(f"What-if error: {str(e)}")
        raise HTTPException(500, str(e))
