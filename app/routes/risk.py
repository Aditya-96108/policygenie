import logging
from fastapi import APIRouter, HTTPException
from app.schemas.risk_schema import RiskRequest
from app.schemas.response_schema import RiskResponse
from app.services.risk_service import assess_risk

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/assess-risk", response_model=RiskResponse)
async def assess_risk_endpoint(request: RiskRequest):
    try:
        result = await assess_risk(
            request.applicant_data,
            request.policy_type,
            request.coverage_amount
        )
        return RiskResponse(result=result)
    except Exception as e:
        logger.error(f"Risk assessment error: {str(e)}")
        raise HTTPException(500, str(e))
