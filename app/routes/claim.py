"""
Claims Processing Route – rigorous multi-stage validation
Verdict ladder: APPROVED | PENDING_DOCUMENTS | UNDER_INVESTIGATION | REJECTED
"""
import json
import logging
from fastapi import APIRouter, HTTPException

from app.schemas.claim_schema import ClaimRequest
from app.schemas.response_schema import ClaimResponse
from app.services.llm_service import generate_response_async, llm_service
from app.services.rag_service import retrieve
from app.utils.prompts import get_claim_prompt
from app.services.fraud_service import detect_fraud

router = APIRouter()
logger = logging.getLogger(__name__)


def _clean_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON robustly."""
    text = raw.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


def _build_under_investigation_response(fraud_result: dict, claim_data: dict) -> dict:
    """Response when ML fraud detector flags a claim before LLM is even called."""
    return {
        "verdict": "UNDER_INVESTIGATION",
        "coverage_applicable": False,
        "fraud_risk": "HIGH",
        "fraud_score": round(fraud_result.get("fraud_score", 0.9), 3),
        "missing_documents": [],
        "fraud_signals_found": fraud_result.get("indicators", [
            "Multiple automated fraud signals detected"
        ]),
        "reason": (
            "Our automated fraud detection system identified one or more high-risk signals "
            "in this claim submission. In keeping with company policy and regulatory "
            "obligations, this claim has been escalated to a senior claims investigator "
            "for manual review."
        ),
        "claimant_message": (
            "Dear Claimant,\n\n"
            "Thank you for submitting your claim. Our system has flagged certain aspects "
            "of this submission for further review by our specialist claims team. A "
            "dedicated investigator will contact you within 2–3 business days.\n\n"
            "You are welcome to re-submit with additional supporting documentation at "
            "any time. We appreciate your patience and understanding.\n\n"
            "Warm regards,\nPolicyGenie Claims Department"
        ),
        "required_documents_checklist": [
            "Government-issued photo ID",
            "Original policy certificate",
            "Incident report / police report",
            "Two independent witness statements",
            "Photographs of damage / evidence",
            "Itemised cost estimate or receipts"
        ],
        "estimated_coverage_amount": 0.0,
        "policy_references": [],
        "next_steps": [
            "A senior claims investigator will contact you within 2–3 business days.",
            "Gather all supporting documents and keep them ready.",
            "Do not repair or dispose of damaged items until the investigation is complete.",
            "You may re-submit with additional evidence at any time via this portal."
        ],
        "internal_notes": (
            f"ML fraud score: {fraud_result.get('fraud_score', 0.9):.3f}. "
            f"Signals: {fraud_result.get('indicators', [])}. "
            "Requires manual investigation before any payment."
        )
    }


def _enrich_pending_response(result: dict) -> dict:
    """Ensure PENDING_DOCUMENTS response has a warm, clear claimant message."""
    missing = result.get("missing_documents", [])
    if not result.get("claimant_message") or len(result.get("claimant_message", "")) < 30:
        missing_list = "\n".join(f"  • {d}" for d in missing) if missing else "  • See required documents checklist below"
        result["claimant_message"] = (
            "Dear Claimant,\n\n"
            "Thank you for reaching out to us. Your claim appears to be largely valid "
            "and we genuinely want to help you through this process.\n\n"
            "However, we are unable to proceed to approval at this stage because the "
            "following required document(s) have not been submitted:\n\n"
            f"{missing_list}\n\n"
            "Please gather these documents and re-submit your claim through this portal. "
            "Once we receive the complete documentation, your claim will be processed "
            "as a priority.\n\n"
            "We are here to support you — please don't hesitate to contact our "
            "helpline if you need assistance obtaining any of these documents.\n\n"
            "Warm regards,\nPolicyGenie Claims Department"
        )
    return result


def _enrich_rejected_response(result: dict) -> dict:
    """Ensure REJECTED response explains clearly without being harsh."""
    if not result.get("claimant_message") or len(result.get("claimant_message", "")) < 30:
        result["claimant_message"] = (
            "Dear Claimant,\n\n"
            "Thank you for submitting your claim. After careful review against your "
            "policy terms and conditions, we regret to inform you that this claim "
            "cannot be approved at this time.\n\n"
            f"Reason: {result.get('reason', 'The incident does not fall within the covered perils of your policy.')}\n\n"
            "If you believe this decision is incorrect or if you have additional "
            "information that may change the outcome, you have the right to appeal "
            "within 30 days by contacting our disputes resolution team.\n\n"
            "We value your trust in PolicyGenie and remain committed to serving you.\n\n"
            "Warm regards,\nPolicyGenie Claims Department"
        )
    return result


@router.post("/process-claim", response_model=ClaimResponse)
async def process_claim_endpoint(request: ClaimRequest):
    try:
        claim_data = request.model_dump(exclude_none=True)

        text_for_fraud = request.claim_description or request.query or ""
        if not text_for_fraud.strip():
            raise HTTPException(400, "claim_description cannot be empty.")

        # Ensure submitted_documents is always a list (never None)
        submitted_docs = request.submitted_documents or []
        claim_data["submitted_documents"] = submitted_docs

        logger.info(
            f"Processing claim | claimant={request.claimant_name or 'N/A'} "
            f"| policy={request.policy_number or 'N/A'} "
            f"| amount={request.claim_amount or 'N/A'} "
            f"| declared_docs={len(submitted_docs)}"
        )

        # ── STAGE A: ML fraud pre-filter ──────────────────────────────────
        logger.info("Running ML fraud pre-filter…")
        fraud_result = await detect_fraud(text_for_fraud)
        fraud_score  = fraud_result.get("fraud_score", 0.0)
        logger.info(f"ML fraud score: {fraud_score:.3f}")

        if fraud_result.get("is_suspicious"):
            logger.warning("ML fraud detector flagged → UNDER_INVESTIGATION")
            return ClaimResponse(
                result=_build_under_investigation_response(fraud_result, claim_data)
            )

        # ── STAGE B: RAG retrieval ────────────────────────────────────────
        logger.info("Retrieving policy context…")
        try:
            embeddings = await llm_service.generate_embeddings([text_for_fraud])
            docs       = retrieve(embeddings[0])
            context    = "\n\n".join(docs[0]) if docs and docs[0] else ""
            logger.info(f"Retrieved {len(docs[0]) if docs and docs[0] else 0} chunks")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            context = ""

        # ── STAGE C: LLM adjudication ─────────────────────────────────────
        logger.info("Running LLM adjudication…")
        prompt = get_claim_prompt(context, claim_data)
        raw    = await generate_response_async(prompt, temperature=0.1)

        # ── STAGE D: Parse ────────────────────────────────────────────────
        try:
            result = _clean_json(raw)
        except (json.JSONDecodeError, ValueError) as parse_err:
            logger.error(f"LLM parse error: {parse_err} | raw={raw[:300]}")
            result = {
                "verdict": "UNDER_INVESTIGATION",
                "coverage_applicable": False,
                "fraud_risk": "MEDIUM",
                "fraud_score": fraud_score,
                "document_verification": {"declared_and_verified": [], "declared_but_unverified": [], "missing": []},
                "document_guidance": [],
                "missing_documents": [],
                "fraud_signals_found": ["System could not fully evaluate the claim narrative"],
                "reason": "Claim routed for manual review due to a processing anomaly.",
                "claimant_message": (
                    "Dear Claimant,\n\nYour claim is being reviewed by our team. "
                    "We will contact you within 2–3 business days.\n\n"
                    "Warm regards,\nPolicyGenie Claims Department"
                ),
                "required_documents_checklist": ["Incident report", "Photo evidence", "Policy certificate"],
                "estimated_coverage_amount": 0.0,
                "policy_references": [],
                "next_steps": ["Await contact from a claims representative within 2–3 business days."],
                "internal_notes": f"LLM parse error: {parse_err}. Raw: {raw[:200]}"
            }

        # ── STAGE E: Ensure document_verification key exists ──────────────
        if "document_verification" not in result:
            result["document_verification"] = {
                "declared_and_verified": [],
                "declared_but_unverified": [],
                "missing": []
            }
        if "document_guidance" not in result:
            result["document_guidance"] = []

        # ── STAGE F: ML fraud override ────────────────────────────────────
        if fraud_score >= 0.65 and result.get("verdict") == "APPROVED":
            logger.warning(f"Overriding LLM APPROVED → UNDER_INVESTIGATION (ML score={fraud_score:.3f})")
            result["verdict"]        = "UNDER_INVESTIGATION"
            result["fraud_risk"]     = "HIGH"
            result["fraud_score"]    = fraud_score
            result["internal_notes"] = f"LLM overridden: ML={fraud_score:.3f}. " + result.get("internal_notes", "")

        # ── STAGE G: Check if PENDING should apply due to unverified docs ──
        doc_ver  = result.get("document_verification", {})
        unverif  = doc_ver.get("declared_but_unverified", [])
        missing  = doc_ver.get("missing", [])
        # Merge missing_documents from both sources for display
        all_insufficient = list(dict.fromkeys(
            result.get("missing_documents", []) + unverif + missing
        ))
        result["missing_documents"] = all_insufficient

        if all_insufficient and result.get("verdict") == "APPROVED":
            logger.info(f"Overriding APPROVED → PENDING_DOCUMENTS ({len(all_insufficient)} insufficient docs)")
            result["verdict"] = "PENDING_DOCUMENTS"

        # ── STAGE H: Echo back declared docs for frontend display ──────────
        result["submitted_documents_echo"] = submitted_docs

        # ── STAGE I: Enrich messages ──────────────────────────────────────
        verdict = result.get("verdict", "UNDER_INVESTIGATION")
        if verdict == "PENDING_DOCUMENTS":
            result = _enrich_pending_response(result)
        elif verdict == "REJECTED":
            result = _enrich_rejected_response(result)

        result["fraud_score"] = round(max(fraud_score, result.get("fraud_score", 0.0)), 3)

        logger.info(
            f"Adjudication complete | verdict={verdict} "
            f"| fraud_risk={result.get('fraud_risk')} "
            f"| insufficient_docs={len(all_insufficient)}"
        )
        return ClaimResponse(result=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claim processing error: {e}", exc_info=True)
        raise HTTPException(500, f"Claims processing failed: {str(e)}")

