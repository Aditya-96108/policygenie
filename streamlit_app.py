"""
PolicyGenie AI – Professional Enterprise Insurance Platform
=========================================================
• Full session-state persistence: data survives tab switches & re-runs.
  State is only cleared when a new document is uploaded.
• Rigorous claims adjudication UI that matches the new multi-stage backend.
• All spinners correctly cleared before results are rendered.
"""

import streamlit as st
import requests
import json
import plotly.graph_objects as go
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────
API_BASE    = "http://localhost:8000/api"
API_TIMEOUT = 300          # 5 minutes – covers model loading on cold start

st.set_page_config(
    page_title="PolicyGenie AI",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session-state initialisation ───────────────────────────────────────────
# All data lives here so it survives tab switches, widget interactions
# and Streamlit re-runs.  Only a new upload clears relevant keys.
_DEFAULTS = {
    # Upload
    "upload_result":        None,
    "uploaded_filename":    None,
    "docs_indexed":         0,
    # Risk Assessment
    "risk_result":          None,
    # Claims
    "claim_result":         None,
    "claim_submitted":      False,
    # Chat  – list of {"role": "user"|"assistant", "content": str}
    "chat_history":         [],
    # What-If
    "whatif_result":        None,
    "wi_orig_inputs":       None,
    "wi_mod_inputs":        None,
    # Reports
    "pdf_bytes":            None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header  {font-size:2.8rem;color:#1a3c6e;text-align:center;font-weight:700;padding:.8rem 0 .2rem}
    .sub-header   {font-size:1.15rem;color:#555;text-align:center;margin-bottom:1.4rem}
    .verdict-approved    {background:#d4edda;border-left:5px solid #28a745;padding:1rem;border-radius:6px;margin:.6rem 0}
    .verdict-pending     {background:#fff3cd;border-left:5px solid #ffc107;padding:1rem;border-radius:6px;margin:.6rem 0}
    .verdict-investigate {background:#f8d7da;border-left:5px solid #dc3545;padding:1rem;border-radius:6px;margin:.6rem 0}
    .verdict-rejected    {background:#f5c6cb;border-left:5px solid #721c24;padding:1rem;border-radius:6px;margin:.6rem 0}
    .doc-chip  {display:inline-block;background:#e8f0fe;border:1px solid #4a90d9;
                border-radius:20px;padding:2px 12px;margin:3px;font-size:.85rem;color:#1a3c6e}
    .missing-chip {display:inline-block;background:#fdecea;border:1px solid #e57373;
                   border-radius:20px;padding:2px 12px;margin:3px;font-size:.85rem;color:#c62828}
    .section-card {background:#f8faff;border:1px solid #dde6f5;border-radius:10px;padding:1.2rem;margin:.8rem 0}
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown('<h1 class="main-header">🏆 PolicyGenie AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Enterprise Insurance Underwriting & Claims Platform</p>',
            unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏢 PolicyGenie AI")
    st.markdown("*Enterprise Insurance Platform*")
    st.markdown("---")
    st.markdown("### 🎯 Platform Capabilities")
    st.markdown("""
✅ **Multi-Stage Claims Adjudication**  
✅ **Advanced Fraud Detection (DeBERTa + FinBERT)**  
✅ **Predictive Risk Assessment**  
✅ **Hybrid RAG Policy Search**  
✅ **Scenario Analysis**  
✅ **PDF Report Generation**
    """)
    st.markdown("---")
    st.markdown("### 📊 System Status")
    try:
        h = requests.get(f"{API_BASE.replace('/api','')}/health", timeout=3)
        if h.status_code == 200:
            data = h.json()
            st.success("🟢 API Operational")
            st.caption(f"Models loaded: {'✅' if data.get('models_loaded') else '⏳ loading…'}")
        else:
            st.error("🔴 API Error")
    except Exception:
        st.warning("⚠️ Cannot reach API")

    if st.session_state.uploaded_filename:
        st.markdown("---")
        st.markdown("### 📄 Active Policy")
        st.info(f"📎 {st.session_state.uploaded_filename}\n\n"
                f"🗂 {st.session_state.docs_indexed} chunks indexed")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📁 Upload Documents",
    "🎯 Risk Assessment",
    "💼 Process Claims",
    "💬 Policy Chat",
    "🔮 What-If Analysis",
    "📄 Generate Reports",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – UPLOAD DOCUMENTS
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📁 Upload & Index Policy Documents")
    st.markdown("Upload a PDF policy document. The system will index it for all other features.")

    col_form, col_guide = st.columns([2, 1])

    with col_form:
        uploaded_file = st.file_uploader(
            "Choose a PDF file", type="pdf", help="Maximum file size: 10 MB"
        )

        if uploaded_file:
            st.caption(f"Selected: **{uploaded_file.name}** "
                       f"({uploaded_file.size / 1024:.1f} KB)")

        if uploaded_file and st.button("🚀 Upload & Process", type="primary"):
            with st.spinner("Uploading and indexing document…"):
                try:
                    files    = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = requests.post(f"{API_BASE}/upload-docs",
                                             files=files, timeout=API_TIMEOUT)
                    upload_result = response.json() if response.ok else None
                except Exception as exc:
                    upload_result = None
                    upload_error  = str(exc)
                else:
                    upload_error = None

            # ── results outside spinner ──
            if response.ok and upload_result:
                if "fraud_details" in upload_result:
                    st.warning("⚠️ Document flagged for manual review")
                    st.json(upload_result["fraud_details"])
                    # Do NOT update session state – keep previous valid doc
                else:
                    chunks = upload_result.get("chunks", 0)
                    st.success(f"✅ Document processed successfully! ({chunks} chunks indexed)")

                    # ── Clear all dependent state when new doc uploaded ──
                    for k in ("risk_result", "claim_result", "claim_submitted",
                              "chat_history", "whatif_result", "pdf_bytes"):
                        st.session_state[k] = _DEFAULTS[k]

                    st.session_state.upload_result     = upload_result
                    st.session_state.uploaded_filename = uploaded_file.name
                    st.session_state.docs_indexed      = chunks
                    st.info(f"📊 {chunks} document chunks ready for AI queries.")
            else:
                err_body = response.text if not response.ok else ""
                st.error(f"Upload failed: {upload_error or err_body}")

        # Show persisted result if already uploaded
        if st.session_state.upload_result and not uploaded_file:
            st.success(f"✅ Active document: **{st.session_state.uploaded_filename}** "
                       f"({st.session_state.docs_indexed} chunks indexed)")

    with col_guide:
        st.info("""
**Upload Guidelines**
- PDF format only
- Max size: 10 MB
- Text-based PDFs (not scanned images)

**Security checks**
- Malware & script scanning
- MIME type validation
- Fraud content analysis

**After upload**
- All tabs use this document
- Upload a new doc to refresh
        """)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – RISK ASSESSMENT
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🎯 Advanced Risk Assessment")
    st.markdown("AI-powered underwriting with predictive analytics and dynamic pricing.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Applicant Information")
        age         = st.number_input("Age", 18, 100, 35, key="ra_age")
        gender      = st.selectbox("Gender", ["Male","Female","Other"], key="ra_gender")
        occupation  = st.text_input("Occupation", "Software Engineer", key="ra_occ")
        location    = st.text_input("Location", "California", key="ra_loc")
        st.subheader("Health & Lifestyle")
        smoking      = st.checkbox("Smoker", key="ra_smoke")
        health_status = st.selectbox("Health Status",
                                     ["Excellent","Good","Fair","Poor"], key="ra_health")

    with col2:
        st.subheader("Financial Information")
        credit_score   = st.slider("Credit Score", 300, 850, 750, key="ra_credit")
        claims_history = st.number_input("Previous Claims", 0, 10, 0, key="ra_claims")
        st.subheader("Policy Details")
        policy_type     = st.selectbox("Policy Type",
                                       ["life","health","auto","home"], key="ra_ptype")
        coverage_amount = st.number_input("Coverage Amount ($)", 10000, 10000000,
                                          500000, step=10000, key="ra_cov")

    if st.button("🔍 Assess Risk", type="primary", key="ra_btn"):
        with st.spinner("Running risk assessment…"):
            try:
                payload = {
                    "applicant_data": {
                        "age": age, "gender": gender, "occupation": occupation,
                        "location": location, "smoking": smoking,
                        "health_status": health_status, "credit_score": credit_score,
                        "claims_history": [f"claim_{i}" for i in range(int(claims_history))],
                    },
                    "policy_type": policy_type,
                    "coverage_amount": coverage_amount,
                }
                response = requests.post(f"{API_BASE}/assess-risk",
                                         json=payload, timeout=API_TIMEOUT)
                ra_result = response.json().get("result") if response.ok else None
            except Exception as exc:
                ra_result  = None
                ra_error   = str(exc)
            else:
                ra_error = None

        # Display outside spinner
        if ra_result:
            st.session_state.risk_result = ra_result
        elif ra_error:
            st.error(f"Assessment failed: {ra_error}")
        elif not response.ok:
            st.error(f"API error: {response.text}")

    # Always render persisted result
    ra = st.session_state.risk_result
    if ra:
        st.markdown("---")
        decision = ra.get("decision", "UNKNOWN")
        score    = ra.get("risk_score", 0)
        conf     = ra.get("confidence", 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Score", f"{score:.1f}/100")
        c2.metric("Decision", decision)
        c3.metric("Confidence", f"{conf:.0%}" if isinstance(conf, float) else conf)

        prem = ra.get("premium_estimate", {})
        if prem:
            pc1, pc2 = st.columns(2)
            pc1.metric("Annual Premium", f"${prem.get('annual', 0):,.2f}")
            pc2.metric("Monthly Premium", f"${prem.get('monthly', 0):,.2f}")

        # Risk breakdown chart
        breakdown = ra.get("risk_breakdown", {})
        if breakdown:
            fig = go.Figure(go.Bar(
                x=list(breakdown.values()),
                y=list(breakdown.keys()),
                orientation="h",
                marker_color=["#e74c3c" if v > 50 else "#f39c12" if v > 30 else "#27ae60"
                              for v in breakdown.values()]
            ))
            fig.update_layout(title="Risk Factor Breakdown", height=300,
                              xaxis_title="Score", margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        for rec in ra.get("recommendations", []):
            st.info(f"💡 {rec}")

        with st.expander("📋 Detailed Assessment"):
            st.text(ra.get("detailed_assessment", "N/A"))
        with st.expander("🔍 Complete Response"):
            st.json(ra)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – PROCESS CLAIMS  (fully rewritten)
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("💼 Claims Processing Centre")
    st.markdown(
        "Submit your insurance claim below. Our multi-stage AI adjudicator evaluates "
        "fraud risk, policy coverage, and document completeness before any decision is made."
    )

    # ── Instructions banner ──────────────────────────────────────────────
    with st.expander("ℹ️  How the claims process works", expanded=False):
        st.markdown("""
**Stage 1 – Fraud pre-filter (ML models)**  
Automated scanning for fraud signals using ensemble models (DeBERTa v3 + FinBERT).

**Stage 2 – Policy context retrieval (RAG)**  
Relevant policy clauses are pulled from the uploaded document.

**Stage 3 – Multi-stage LLM adjudication**  
The AI adjudicator checks: identity & policy match → coverage → required documents → fraud signals.

**Possible verdicts**

| Verdict | Meaning |
|---|---|
| ✅ APPROVED | All checks passed. Claim proceeding to payment. |
| 📋 PENDING_DOCUMENTS | Claim valid but specific documents are missing. |
| 🔍 UNDER_INVESTIGATION | Suspicious signals detected. Routed to investigator. |
| ❌ REJECTED | Incident not covered by your policy. |
        """)

    # ── Claim form ────────────────────────────────────────────────────────
    st.subheader("📝 Claim Submission Form")

    with st.form("claim_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            claimant_name  = st.text_input("Full Legal Name *",
                                           placeholder="As printed on the policy")
            policy_number  = st.text_input("Policy Number *",
                                           placeholder="e.g. POL-2024-001234")
            incident_date  = st.date_input("Date of Incident *",
                                           value=datetime.today())
        with c2:
            incident_location = st.text_input("Incident Location *",
                                              placeholder="City, State / full address")
            claim_amount      = st.number_input("Claim Amount (USD) *",
                                                min_value=0.0, value=0.0,
                                                step=100.0, format="%.2f")
            contact_email     = st.text_input("Contact Email",
                                              placeholder="your@email.com")

        claim_description = st.text_area(
            "Claim Description *",
            placeholder=(
                "Provide a clear, detailed account of the incident:\n"
                "• What happened?\n"
                "• When and where exactly?\n"
                "• Were there any witnesses?\n"
                "• What is the nature and extent of the damage or loss?\n"
                "• What actions have you already taken?"
            ),
            height=180,
        )

        st.markdown("**Supporting Documents** *(tick all that you are submitting)*")
        doc_cols = st.columns(3)
        doc_options = [
            "Police Report",
            "Repair / Replacement Estimate",
            "Photographs / Video Evidence",
            "Witness Statements",
            "Medical Report",
            "Hospital Discharge Summary",
            "Death Certificate",
            "Coroner's Report",
            "Doctor / Physician Statement",
            "Employer Letter (disability)",
            "Itemised Bills / Receipts",
            "Driver's Licence Copy",
        ]
        selected_docs: list[str] = []
        for i, doc in enumerate(doc_options):
            with doc_cols[i % 3]:
                if st.checkbox(doc, key=f"doc_{i}"):
                    selected_docs.append(doc)

        other_doc = st.text_input("Other documents (comma-separated)",
                                  placeholder="e.g. Insurance broker letter, Survey report")
        if other_doc:
            selected_docs += [d.strip() for d in other_doc.split(",") if d.strip()]

        submitted = st.form_submit_button("🚀 Submit Claim for Adjudication",
                                          type="primary", use_container_width=True)

    if submitted:
        # Validate mandatory fields
        errors = []
        if not claimant_name.strip():
            errors.append("Full Legal Name is required.")
        if not claim_description.strip() or len(claim_description.strip()) < 30:
            errors.append("Claim Description must be at least 30 characters.")
        if claim_amount <= 0:
            errors.append("Claim Amount must be greater than $0.")

        if errors:
            for e in errors:
                st.error(f"❌ {e}")
        else:
            with st.spinner("🔍 Adjudicating claim — please wait…"):
                try:
                    payload = {
                        "claim_description":  claim_description.strip(),
                        "incident_date":      str(incident_date),
                        "incident_location":  incident_location.strip() or None,
                        "claim_amount":       claim_amount,
                        "policy_number":      policy_number.strip() or None,
                        "claimant_name":      claimant_name.strip(),
                        "submitted_documents": selected_docs,
                        "contact_email":      contact_email.strip() or None,
                    }
                    response = requests.post(f"{API_BASE}/process-claim",
                                             json=payload, timeout=API_TIMEOUT)
                    claim_result_raw = response.json().get("result") if response.ok else None
                except Exception as exc:
                    claim_result_raw = None
                    claim_api_error  = str(exc)
                else:
                    claim_api_error = None

            # Save to session state outside spinner
            if claim_result_raw:
                st.session_state.claim_result    = claim_result_raw
                st.session_state.claim_submitted = True
            elif claim_api_error:
                st.error(f"Submission failed: {claim_api_error}")
            else:
                st.error(f"API error {response.status_code}: {response.text}")

    # ── Render persisted claim result ────────────────────────────────────
    cr = st.session_state.claim_result
    if cr and st.session_state.claim_submitted:
        st.markdown("---")
        st.subheader("📋 Adjudication Result")

        verdict     = cr.get("verdict", cr.get("decision", "UNKNOWN")).upper()
        fraud_risk  = cr.get("fraud_risk", "UNKNOWN")
        fraud_score = cr.get("fraud_score", 0.0)

        # ── Verdict banner ────────────────────────────────────────────────
        if verdict == "APPROVED":
            st.markdown(
                '<div class="verdict-approved"><h3>✅ CLAIM APPROVED</h3>'
                '<p>All verification stages passed. Your claim is proceeding to payment processing.</p></div>',
                unsafe_allow_html=True
            )
        elif verdict == "PENDING_DOCUMENTS":
            st.markdown(
                '<div class="verdict-pending"><h3>📋 PENDING — ADDITIONAL DOCUMENTS REQUIRED</h3>'
                '<p>Your claim appears valid but we need more documentation before we can proceed. <strong>This is NOT a fraud flag.</strong></p></div>',
                unsafe_allow_html=True
            )
        elif verdict == "UNDER_INVESTIGATION":
            st.markdown(
                '<div class="verdict-investigate"><h3>🔍 UNDER INVESTIGATION</h3>'
                '<p>This claim has been escalated to our specialist investigation team.</p></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="verdict-rejected"><h3>❌ CLAIM REJECTED</h3>'
                '<p>This claim falls outside the covered perils of your policy.</p></div>',
                unsafe_allow_html=True
            )

        # ── Key metrics ───────────────────────────────────────────────────
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Fraud Risk Level", fraud_risk)
        mc2.metric("Fraud Score", f"{fraud_score:.0%}")
        if cr.get("estimated_coverage_amount", 0) > 0:
            mc3.metric("Estimated Coverage", f"${cr['estimated_coverage_amount']:,.2f}")
        else:
            mc3.metric("Coverage", "Pending / N/A")

        # ── Document Verification Dashboard ──────────────────────────────
        st.markdown("---")
        st.subheader("📂 Document Verification Status")

        doc_ver   = cr.get("document_verification", {})
        verified  = doc_ver.get("declared_and_verified", [])
        unverif   = doc_ver.get("declared_but_unverified", [])
        missing   = doc_ver.get("missing", [])
        submitted_echo = cr.get("submitted_documents_echo", [])

        # Summary gauge row
        total_req = len(verified) + len(unverif) + len(missing)
        if total_req:
            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("✅ Verified", len(verified),
                       help="Declared AND narrative confirms existence")
            dc2.metric("⚠️ Declared but Unverified", len(unverif),
                       help="Ticked on form but narrative doesn't confirm the document exists")
            dc3.metric("❌ Missing", len(missing),
                       help="Required but not declared at all")

            # Visual progress bar
            pct_ok = len(verified) / total_req if total_req else 0
            st.progress(pct_ok, text=f"Document completeness: {pct_ok:.0%}")

        # Per-document status table
        req_docs = cr.get("required_documents_checklist", [])
        if req_docs:
            rows = []
            for doc in req_docs:
                if doc in verified:
                    rows.append({"Document": doc, "Status": "✅ Verified", "Action": "—"})
                elif doc in unverif:
                    rows.append({"Document": doc, "Status": "⚠️ Declared but Unverified",
                                 "Action": "See guidance below"})
                elif doc in missing:
                    rows.append({"Document": doc, "Status": "❌ Missing",
                                 "Action": "See guidance below"})
                else:
                    rows.append({"Document": doc, "Status": "❓ Status Unknown",
                                 "Action": "Please declare if you have this"})
            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Unverified callout
        if unverif:
            st.warning(
                f"⚠️ **{len(unverif)} document(s) were ticked but could not be verified "
                f"from your claim description.** Ticking a checkbox does not submit the "
                f"document — please see the guidance below on how to obtain and submit them."
            )
            for d in unverif:
                st.markdown(
                    f'<span class="missing-chip">⚠️ {d} — declared but unverified</span>',
                    unsafe_allow_html=True
                )

        # Missing callout
        if missing:
            st.error(f"❌ **{len(missing)} required document(s) are missing.**")
            for d in missing:
                st.markdown(
                    f'<span class="missing-chip">❌ {d} — not submitted</span>',
                    unsafe_allow_html=True
                )

        # ── Document Guidance (how to obtain) ─────────────────────────────
        guidance_list = cr.get("document_guidance", [])
        if guidance_list:
            st.markdown("---")
            st.subheader("🗺️ How to Obtain Your Missing Documents")
            st.info(
                "💙 **We are here to help.** Below is step-by-step guidance on where and how "
                "to obtain each required document. **This is not a fraud accusation** — it is "
                "simply the due-diligence process required by all insurance companies to protect "
                "policyholders like you."
            )
            for g in guidance_list:
                doc_name  = g.get("document", "Document")
                status    = g.get("status", "")
                icon      = "⚠️" if "UNVERIFIED" in status else "❌"
                with st.expander(f"{icon} **{doc_name}** — {status.replace('_', ' ').title()}", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.markdown(f"**🏢 Issuing Entity:** {g.get('issuing_entity', 'N/A')}")
                        st.markdown(f"**📋 How to Obtain:**")
                        st.markdown(g.get("how_to_obtain", "Please contact the relevant authority."))
                        contact = g.get("contact", "")
                        if contact:
                            st.markdown(f"**📞 Contact:** {contact}")
                    with col_b:
                        st.markdown(f"**⏱ Turnaround:** {g.get('typical_turnaround', 'Varies')}")
                        st.markdown(f"**💰 Typical Cost:** {g.get('typical_cost', 'Varies')}")

        # ── Official letter ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📬 Official Communication to Claimant")
        st.markdown(cr.get("claimant_message", "").replace("\n", "  \n"))
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Adjudicator assessment ────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🔎 Adjudicator's Assessment")
        st.write(cr.get("reason", ""))
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Fraud signals ─────────────────────────────────────────────────
        fraud_signals = cr.get("fraud_signals_found", [])
        if fraud_signals:
            with st.expander(f"⚠️ Fraud Signals Detected ({len(fraud_signals)})", expanded=False):
                for s in fraud_signals:
                    st.warning(f"• {s}")

        # ── Next steps ────────────────────────────────────────────────────
        next_steps = cr.get("next_steps", [])
        if next_steps:
            st.subheader("🗂 Next Steps")
            for i, step in enumerate(next_steps, 1):
                st.markdown(f"**{i}.** {step}")

        # ── Policy references ─────────────────────────────────────────────
        refs = cr.get("policy_references", [])
        if refs:
            with st.expander("📚 Policy References"):
                for r in refs:
                    st.markdown(f"• *{r}*")

        with st.expander("🔬 Full Technical Report (JSON)"):
            st.json({k: v for k, v in cr.items() if k != "internal_notes"})

        if verdict in ("PENDING_DOCUMENTS", "UNDER_INVESTIGATION"):
            if st.button("🔄 Submit a New / Updated Claim", key="resubmit_btn"):
                st.session_state.claim_result    = None
                st.session_state.claim_submitted = False
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 – POLICY CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("💬 Policy Q&A Assistant")
    st.markdown("Ask any question about your uploaded policy document.")

    # Render persistent chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    chat_input = st.chat_input("Type your question here…")

    if chat_input:
        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)

        with st.chat_message("assistant"):
            with st.spinner("Searching policy documents…"):
                try:
                    response = requests.post(
                        f"{API_BASE}/chat",
                        json={"query": chat_input},
                        timeout=API_TIMEOUT
                    )
                    answer = response.json().get("result", "Sorry, I could not find an answer.") \
                             if response.ok else f"API error: {response.text}"
                except Exception as exc:
                    answer = f"Error: {exc}"
            st.markdown(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    if st.session_state.chat_history:
        if st.button("🗑 Clear conversation", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 – WHAT-IF ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("🔮 Scenario Analysis")
    st.markdown(
        "Adjust any factor below to instantly see how it changes your **risk score**, "
        "**annual premium**, and **underwriting decision** — side by side."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📌 Current Profile")
        orig_age     = st.number_input("Age",          18, 100, 45,  key="wi_oage")
        orig_smoking = st.checkbox("Smoker",                         key="wi_osmoke", value=True)
        orig_credit  = st.slider("Credit Score", 300, 850, 580,      key="wi_ocredit")
        orig_occ     = st.text_input("Occupation", "construction worker", key="wi_oocc")
        orig_claims  = st.number_input("Prior Claims", 0, 10, 2,     key="wi_oclaims")
    with col2:
        st.markdown("### ✏️ Modified Profile")
        mod_age     = st.number_input("Age",          18, 100, 45,  key="wi_mage")
        mod_smoking = st.checkbox("Smoker",                         key="wi_msmoke", value=False)
        mod_credit  = st.slider("Credit Score", 300, 850, 750,      key="wi_mcredit")
        mod_occ     = st.text_input("Occupation", "teacher",        key="wi_mocc")
        mod_claims  = st.number_input("Prior Claims", 0, 10, 0,     key="wi_mclaims")

    wi_policy = st.selectbox("Policy Type", ["life", "health", "auto", "home"], key="wi_policy")

    if st.button("🔮 Compare Scenarios", type="primary", key="wi_btn"):
        with st.spinner("Running scenario comparison…"):
            try:
                payload = {
                    "original_data": {
                        "age": orig_age, "smoking": orig_smoking,
                        "credit_score": orig_credit, "occupation": orig_occ,
                        "claims_history": [f"c{i}" for i in range(int(orig_claims))],
                    },
                    "modified_data": {
                        "age": mod_age, "smoking": mod_smoking,
                        "credit_score": mod_credit, "occupation": mod_occ,
                        "claims_history": [f"c{i}" for i in range(int(mod_claims))],
                    },
                    "policy_type": wi_policy,
                }
                response = requests.post(f"{API_BASE}/what-if",
                                         json=payload, timeout=API_TIMEOUT)
                wi_result = response.json().get("result") if response.ok else None
            except Exception as exc:
                wi_result = None
                wi_error  = str(exc)
            else:
                wi_error = None

        if wi_result:
            st.session_state.whatif_result  = wi_result
            # Stash the inputs for chart labels
            st.session_state.wi_orig_inputs = {
                "age": orig_age, "smoking": orig_smoking,
                "credit": orig_credit, "claims": orig_claims, "occ": orig_occ,
            }
            st.session_state.wi_mod_inputs  = {
                "age": mod_age, "smoking": mod_smoking,
                "credit": mod_credit, "claims": mod_claims, "occ": mod_occ,
            }
        elif wi_error:
            st.error(f"Analysis failed: {wi_error}")
        else:
            st.error(f"API error: {response.text}")

    wi = st.session_state.whatif_result
    if wi:
        orig_r  = wi.get("original", {})
        mod_r   = wi.get("modified", {})
        changes = wi.get("changes", {})

        orig_score  = orig_r.get("risk_score", 0)
        mod_score   = mod_r.get("risk_score", 0)
        orig_annual = orig_r.get("premium_estimate", {}).get("annual", 0)
        mod_annual  = mod_r.get("premium_estimate", {}).get("annual", 0)
        orig_dec    = orig_r.get("decision", "UNKNOWN")
        mod_dec     = mod_r.get("decision", "UNKNOWN")

        delta_risk  = changes.get("risk_score_delta", mod_score - orig_score)
        delta_prem  = changes.get("premium_delta", {}).get("annual", mod_annual - orig_annual)

        st.markdown("---")
        st.subheader("📊 Comparison Dashboard")

        # ── Top KPI row ───────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Risk Score",     f"{mod_score:.1f}",
                  delta=f"{delta_risk:+.1f}", delta_color="inverse")
        k2.metric("Annual Premium", f"${mod_annual:,.0f}",
                  delta=f"${delta_prem:+,.0f}", delta_color="inverse")
        k3.metric("Decision",       mod_dec)
        savings = abs(delta_prem) if delta_prem < 0 else 0
        k4.metric("Potential Savings", f"${savings:,.0f}/yr",
                  delta=f"{(savings/orig_annual*100):+.1f}% cheaper" if orig_annual else "—",
                  delta_color="normal")

        st.markdown("---")

        # ── Chart row 1: Risk score + premium side-by-side bars ───────────
        ch1, ch2 = st.columns(2)

        with ch1:
            fig_risk = go.Figure()
            fig_risk.add_bar(
                name="Current Profile",
                x=["Risk Score"],
                y=[orig_score],
                marker_color="#e74c3c",
                text=[f"{orig_score:.1f}"],
                textposition="outside",
                width=0.35,
            )
            fig_risk.add_bar(
                name="Modified Profile",
                x=["Risk Score"],
                y=[mod_score],
                marker_color="#27ae60",
                text=[f"{mod_score:.1f}"],
                textposition="outside",
                width=0.35,
            )
            fig_risk.update_layout(
                title="⚡ Risk Score Comparison",
                barmode="group",
                yaxis=dict(range=[0, 100], title="Score /100"),
                height=320,
                margin=dict(t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_risk, use_container_width=True)

        with ch2:
            fig_prem = go.Figure()
            fig_prem.add_bar(
                name="Current Profile",
                x=["Annual Premium"],
                y=[orig_annual],
                marker_color="#e74c3c",
                text=[f"${orig_annual:,.0f}"],
                textposition="outside",
                width=0.35,
            )
            fig_prem.add_bar(
                name="Modified Profile",
                x=["Annual Premium"],
                y=[mod_annual],
                marker_color="#27ae60",
                text=[f"${mod_annual:,.0f}"],
                textposition="outside",
                width=0.35,
            )
            fig_prem.update_layout(
                title="💰 Annual Premium Comparison",
                barmode="group",
                yaxis=dict(title="USD ($)"),
                height=320,
                margin=dict(t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_prem, use_container_width=True)

        # ── Chart 2: Factor-level risk breakdown radar / bar ──────────────
        orig_bd = orig_r.get("risk_breakdown", {})
        mod_bd  = mod_r.get("risk_breakdown", {})
        if orig_bd and mod_bd:
            all_factors = list(dict.fromkeys(list(orig_bd.keys()) + list(mod_bd.keys())))
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=[orig_bd.get(f, 0) for f in all_factors],
                theta=all_factors,
                fill="toself",
                name="Current",
                line_color="#e74c3c",
                opacity=0.6,
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=[mod_bd.get(f, 0) for f in all_factors],
                theta=all_factors,
                fill="toself",
                name="Modified",
                line_color="#27ae60",
                opacity=0.6,
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="🕸️ Risk Factor Radar",
                height=380,
                showlegend=True,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # ── Chart 3: Input changes waterfall ─────────────────────────────
        oi = st.session_state.get("wi_orig_inputs", {})
        mi = st.session_state.get("wi_mod_inputs", {})
        if oi and mi:
            changes_labels = []
            changes_vals   = []
            change_colors  = []

            credit_diff = mi.get("credit", 0) - oi.get("credit", 0)
            if credit_diff:
                changes_labels.append("Credit Score")
                changes_vals.append(credit_diff)
                change_colors.append("#27ae60" if credit_diff > 0 else "#e74c3c")

            if oi.get("smoking") != mi.get("smoking"):
                val = -15 if (not mi.get("smoking") and oi.get("smoking")) else 15
                changes_labels.append("Smoking status")
                changes_vals.append(val)
                change_colors.append("#27ae60" if val < 0 else "#e74c3c")

            claims_diff = mi.get("claims", 0) - oi.get("claims", 0)
            if claims_diff:
                changes_labels.append("Prior Claims")
                changes_vals.append(-claims_diff * 5)
                change_colors.append("#27ae60" if claims_diff < 0 else "#e74c3c")

            if changes_labels:
                fig_wf = go.Figure(go.Bar(
                    x=changes_labels,
                    y=changes_vals,
                    marker_color=change_colors,
                    text=[f"{'+' if v>0 else ''}{v}" for v in changes_vals],
                    textposition="outside",
                ))
                fig_wf.update_layout(
                    title="📈 Impact of Each Changed Factor on Risk",
                    yaxis_title="Risk Impact (lower = better)",
                    height=300,
                    margin=dict(t=50, b=20),
                )
                fig_wf.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_wf, use_container_width=True)

        # ── Savings projection table ──────────────────────────────────────
        if savings > 0:
            st.markdown("---")
            st.subheader("💡 Long-term Savings Projection")
            years  = [1, 5, 10, 20]
            saving_rows = {"Year": years,
                           "Cumulative Savings ($)": [savings * y for y in years]}
            import pandas as pd
            st.dataframe(pd.DataFrame(saving_rows), use_container_width=True, hide_index=True)
            st.caption(f"Based on annual saving of **${savings:,.0f}** "
                       f"({orig_dec} → {mod_dec})")

        # ── Recommendations ───────────────────────────────────────────────
        for rec in mod_r.get("recommendations", []):
            st.info(f"💡 {rec}")

        with st.expander("📊 Full Raw Comparison Data"):
            st.json(wi)


# ════════════════════════════════════════════════════════════════════════════
# TAB 6 – GENERATE REPORTS
# ════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("📄 Generate PDF Reports")
    st.markdown("Create a professional downloadable PDF from any assessment data.")

    report_text     = st.text_area("Report Content:", height=280,
                                   placeholder="Paste your assessment results or write a custom report…")
    report_filename = st.text_input("Filename:", value="policygenie_report.pdf")

    if st.button("📥 Generate PDF", type="primary", key="pdf_btn"):
        if not report_text.strip():
            st.warning("Please enter some report content.")
        else:
            with st.spinner("Generating PDF…"):
                try:
                    response = requests.post(
                        f"{API_BASE}/download-pdf",
                        json={"text": report_text, "filename": report_filename},
                        timeout=60,
                    )
                    pdf_bytes = response.content if response.ok else None
                except Exception as exc:
                    pdf_bytes = None
                    st.error(f"Generation failed: {exc}")

            if pdf_bytes:
                st.session_state.pdf_bytes = pdf_bytes
                st.success("✅ PDF generated successfully!")
            elif response and not response.ok:
                st.error(f"API error: {response.text}")

    if st.session_state.pdf_bytes:
        st.download_button(
            label="📥 Download PDF",
            data=st.session_state.pdf_bytes,
            file_name=report_filename,
            mime="application/pdf",
        )

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#888;font-size:.85rem'>
  🏆 <strong>PolicyGenie AI</strong> — Enterprise Insurance Platform<br>
  Powered by FastAPI · OpenAI · DeBERTa v3 · FinBERT · ChromaDB<br>
  © 2024 PolicyGenie AI. All rights reserved.
</div>
""", unsafe_allow_html=True)
