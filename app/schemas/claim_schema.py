"""
Claim Schema - Rich structured input with full backward compatibility.

Backward-compat rule:
  If `claim_description` is absent but `query` is present,
  `query` is promoted to `claim_description` automatically.
  This means old-style  {"query": "..."}  payloads keep working.
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List


class ClaimRequest(BaseModel):
    # ── Core narrative ────────────────────────────────────────────────────
    # Optional at parse time; the validator below makes it required.
    claim_description: Optional[str] = Field(
        None,
        description="Full narrative of the incident"
    )

    # ── Incident metadata ─────────────────────────────────────────────────
    incident_date: Optional[str] = Field(
        None,
        description="Date of incident (YYYY-MM-DD or any recognisable format)"
    )
    incident_location: Optional[str] = Field(
        None,
        description="Location where incident occurred"
    )
    claim_amount: Optional[float] = Field(
        None,
        description="Amount being claimed in USD"
    )

    # ── Policy identification ─────────────────────────────────────────────
    policy_number: Optional[str] = Field(
        None,
        description="Policy number from the policy document"
    )
    claimant_name: Optional[str] = Field(
        None,
        description="Full legal name of the claimant"
    )

    # ── Supporting documents ──────────────────────────────────────────────
    submitted_documents: Optional[List[str]] = Field(
        default_factory=list,
        description="Names/types of documents being submitted with this claim"
    )

    # ── Contact details ───────────────────────────────────────────────────
    contact_email: Optional[str] = Field(
        None,
        description="Claimant contact email"
    )
    contact_phone: Optional[str] = Field(
        None,
        description="Claimant contact phone number"
    )

    # ── Legacy field (old API used only `query`) ──────────────────────────
    query: Optional[str] = Field(
        None,
        description="Legacy free-text field – auto-promoted to claim_description"
    )

    @model_validator(mode="after")
    def _promote_query_to_description(self) -> "ClaimRequest":
        """
        If `claim_description` is missing, use `query` as the description.
        If both are missing, raise a clear validation error.
        """
        if not self.claim_description:
            if self.query:
                self.claim_description = self.query
            else:
                raise ValueError(
                    "Either 'claim_description' or 'query' must be provided."
                )
        return self

