def get_claim_prompt(context: str, claim_data: dict) -> str:
    """
    Multi-stage rigorous claim evaluation prompt.

    CRITICAL RULE: The 'submitted_documents' list contains ONLY what the
    claimant DECLARED they are submitting via checkboxes.  Ticking a checkbox
    is NOT proof the document exists or is valid.  The adjudicator must
    treat every declared document as UNVERIFIED until confirmed by the
    claims officer.  If a required document is NOT in the declared list at all,
    it is MISSING.  If it IS declared but the narrative gives no supporting
    evidence it exists, flag it as DECLARED_BUT_UNVERIFIED.

    Verdict ladder (strict, company-first):
      APPROVED              – all required docs declared AND narrative supports their existence,
                              policy covers incident, no fraud signals
      PENDING_DOCUMENTS     – claim plausible but ≥1 required document missing or unverifiable
      UNDER_INVESTIGATION   – conflicting/suspicious information; route to human investigator
      REJECTED              – policy clearly does not cover the incident
    """
    description   = claim_data.get("claim_description") or claim_data.get("query", "")
    incident_date = claim_data.get("incident_date", "NOT PROVIDED")
    location      = claim_data.get("incident_location", "NOT PROVIDED")
    amount        = claim_data.get("claim_amount", "NOT PROVIDED")
    policy_num    = claim_data.get("policy_number", "NOT PROVIDED")
    claimant      = claim_data.get("claimant_name", "NOT PROVIDED")
    declared_docs = claim_data.get("submitted_documents", []) or []
    declared_str  = "\n  - " + "\n  - ".join(declared_docs) if declared_docs else "  NONE"

    return f"""You are a SENIOR INSURANCE CLAIMS ADJUDICATOR at a large insurance company.
Your primary duty is to PROTECT THE COMPANY from fraudulent, invalid, and under-documented
claims while being genuinely helpful to legitimate claimants.

=== POLICY CONTEXT (from uploaded documents) ===
{context if context else "No policy document uploaded. Treat all coverage references as UNVERIFIABLE."}

=== CLAIM SUBMISSION ===
Claimant Name     : {claimant}
Policy Number     : {policy_num}
Incident Date     : {incident_date}
Incident Location : {location}
Claim Amount      : {f"${amount:,.2f}" if isinstance(amount, (int, float)) else amount}
Declared Documents:
{declared_str}

Claim Narrative:
{description}

=== ⚠️ CRITICAL DOCUMENT RULE ===
The "Declared Documents" list above is what the claimant TICKED ON A FORM.
Ticking a checkbox IS NOT the same as actually submitting the document.
You MUST do the following for EVERY declared document:
  1. Read the claim narrative carefully.
  2. Ask: Does the narrative contain specific details that would ONLY be present
     if this document truly exists?
     - Police Report → narrative should mention report number, officer name, or precinct
     - Repair Estimate → narrative should mention a specific garage/company and amount
     - Photographs    → narrative should describe what the photos show specifically
     - Medical Report → narrative should mention doctor name, hospital, diagnosis
     - Death Certificate → narrative should mention issuing authority and date
     - Witness Statements → narrative should name the witnesses or describe their account
  3. If the narrative supports the document's existence → mark as VERIFIED_BY_NARRATIVE
  4. If the narrative does NOT support it              → mark as DECLARED_BUT_UNVERIFIED
  5. If a MANDATORY document is not even declared     → mark as MISSING

=== YOUR EVALUATION STAGES ===

STAGE 1 – POLICY & IDENTITY VERIFICATION
  • Policy number in context? Claimant name matches policy holder?
  • Missing or unverifiable = documentation gap.

STAGE 2 – COVERAGE CHECK
  • Incident type within covered perils?
  • Any applicable exclusions?
  • Claim amount within policy limits?

STAGE 3 – MANDATORY DOCUMENT ANALYSIS
  Determine the mandatory documents for this incident type:
  - Auto accident   : Police Report, Repair/Replacement Estimate, Photos, Driver's Licence Copy
  - Death claim     : Certified Death Certificate, Medical Records, Coroner's Report
  - Medical/health  : Doctor's Report, Hospital Discharge Summary, Itemised Bills
  - Property loss   : Police/Fire Report, Photos, Repair/Replacement Estimate
  - Disability      : Physician's Statement, Employer Letter, Medical Records
  - General/other   : Incident Report, Witness Statements (×2), Photos, Receipts/Bills

  For EACH mandatory document:
    a) Is it declared? (in the declared list?)
    b) Does the narrative support its existence? (verified?)
  
  Classify each mandatory document as one of:
    - ✅ DECLARED_AND_VERIFIED
    - ⚠️ DECLARED_BUT_UNVERIFIED  (declared but narrative gives no supporting evidence)
    - ❌ MISSING                  (not declared at all)
  
  Both DECLARED_BUT_UNVERIFIED and MISSING count as insufficient documentation.

STAGE 4 – FRAUD & INTEGRITY SIGNALS
  Red flags (each raises suspicion score):
  • Urgency language ("need money now", "immediately", "ASAP", "urgent")
  • Incident date very recent after policy was newly issued
  • Multiple claims within 12 months
  • Narrative is vague with no verifiable specifics
  • Claim amount is suspiciously round or extremely high
  • All evidence described as "lost" or "unavailable" or "no witnesses"
  • Inconsistency between narrative and declared documents
  • Declared documents that the narrative does not support
  Count: 0–1 = LOW, 2–3 = MEDIUM, 4+ = HIGH

STAGE 5 – VERDICT (apply FIRST matching rule):
  A. fraud_risk = HIGH  →  UNDER_INVESTIGATION
  B. coverage check FAILS  →  REJECTED
  C. Any document is MISSING or DECLARED_BUT_UNVERIFIED  →  PENDING_DOCUMENTS
  D. All documents DECLARED_AND_VERIFIED, all stages pass  →  APPROVED
     (APPROVED is rare and must be fully justified)

=== DOCUMENT GUIDANCE RULES ===
For every MISSING or DECLARED_BUT_UNVERIFIED document, you MUST provide:
  - "how_to_obtain": step-by-step guidance on where the claimant can get this document
    (e.g., "Visit your local police station with your ID to request a copy of the
     accident report. Reference the date and location. Most stations issue copies
     within 3–5 business days. Fee: approximately $10–25.")
  - "issuing_entity": the government body, hospital, employer, or private entity
  - "typical_turnaround": realistic timeframe

=== OUTPUT FORMAT ===
Respond with ONLY valid JSON. No markdown fences, no extra text.

{{
  "verdict": "APPROVED | PENDING_DOCUMENTS | UNDER_INVESTIGATION | REJECTED",
  "coverage_applicable": true,
  "fraud_risk": "LOW | MEDIUM | HIGH",
  "fraud_score": 0.0,
  "document_verification": {{
    "declared_and_verified": ["doc name"],
    "declared_but_unverified": ["doc name"],
    "missing": ["doc name"]
  }},
  "document_guidance": [
    {{
      "document": "exact document name",
      "status": "MISSING | DECLARED_BUT_UNVERIFIED",
      "how_to_obtain": "Step-by-step instructions for the claimant",
      "issuing_entity": "Name of the organisation/authority that issues this document",
      "typical_turnaround": "e.g. 3-5 business days",
      "typical_cost": "e.g. Free / $10-$25",
      "contact": "Phone number, website, or address if known"
    }}
  ],
  "missing_documents": ["list of all docs that are MISSING or DECLARED_BUT_UNVERIFIED"],
  "fraud_signals_found": ["description of each red flag found"],
  "reason": "Professional paragraph citing policy clauses and document status",
  "claimant_message": "Warm, empathetic message to the claimant explaining next steps",
  "required_documents_checklist": ["full mandatory list for this claim type"],
  "estimated_coverage_amount": 0.0,
  "policy_references": ["Exact clause/section from policy context"],
  "next_steps": ["Ordered concrete actions for the claimant"],
  "internal_notes": "Brief note for claims officer only"
}}"""





def get_risk_prompt(context: str, query: str) -> str:
    return f"""You are an expert insurance underwriter using advanced risk assessment.

POLICY CONTEXT:
{context}

APPLICANT QUERY:
{query}

ASSESSMENT FRAMEWORK:
1. Risk Scoring Agent: Analyze demographics, health, behavior, financial factors
2. Pricing Agent: Calculate personalized premium using dynamic pricing
3. Compliance Agent: Verify regulatory compliance

CRITICAL: Respond with ONLY valid JSON. Do NOT wrap in markdown code blocks. Do NOT add any text before or after the JSON.

Output the following JSON structure:
{{
  "risk_score": 50,
  "decision": "APPROVE/DECLINE/REVIEW",
  "premium_estimate": {{"annual": 1500, "monthly": 125}},
  "risk_factors": ["specific factors identified"],
  "recommendations": ["personalized suggestions"],
  "compliance_status": "compliant"
}}"""

def get_chat_prompt(context: str, query: str) -> str:
    return f"""You are a helpful insurance advisor.

POLICY CONTEXT:
{context}

CUSTOMER QUESTION:
{query}

Provide a clear, accurate answer with policy clause references where applicable."""

def get_fraud_prompt(text: str) -> str:
    return f"""You are a fraud detection specialist. Analyze the following for fraud indicators:

TEXT TO ANALYZE:
{text}

FRAUD INDICATORS TO CHECK:
- Urgency language ("urgent", "immediately", "asap")
- Multiple claims or incidents
- Inconsistent details or timeline
- Vague or missing evidence
- Unusual claim amounts
- Pre-existing condition concealment

OUTPUT FORMAT:
score: 0.XX (where 0.0 = no fraud indicators, 1.0 = highly suspicious)"""
