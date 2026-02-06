import streamlit as st
import re
import json
import os
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ---------------- CONFIG ----------------

st.set_page_config(page_title="Contract Risk Bot", layout="wide")
AUDIT_FILE = "audit_log.json"


# ---------------- AUDIT LOGGING ----------------

def audit(action):
    entry = {
        "timestamp": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
        "action": action
    }

    logs = []
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "r") as f:
            logs = json.load(f)

    logs.append(entry)

    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=2)


# ---------------- CONTRACT CLASSIFICATION ----------------

def classify_contract(text):
    rules = {
        "Employment Agreement": ["employee", "employer", "salary"],
        "Lease Agreement": ["lease", "rent", "premises"],
        "Service Contract": ["service", "deliverables"],
        "Vendor Agreement": ["vendor", "supplier"]
    }

    text = text.lower()
    for ctype, words in rules.items():
        if any(w in text for w in words):
            return ctype

    return "General Commercial Contract"


# ---------------- CLAUSE EXTRACTION ----------------

def extract_clauses(text):
    clauses = re.split(r"\n|\.\s+", text)
    return [c.strip() for c in clauses if len(c.strip()) > 30]


# ---------------- ENTITY EXTRACTION ----------------

def extract_entities(text):
    amount_pattern = r"""
        ₹\s?\d+(?:,\d+)*(?:\.\d+)? |
        \d+(?:\.\d+)?\s?(?:lakh|lakhs|crore|crores)
    """

    return {
        "Amounts": re.findall(amount_pattern, text.lower(), re.VERBOSE),
        "Dates": re.findall(r"\d{1,2}/\d{1,2}/\d{4}", text),
        "Jurisdiction": re.findall(r"(india|tamil nadu|delhi|mumbai)", text.lower())
    }



# ---------------- CLAUSE TYPE ----------------

def classify_clause_type(clause):
    clause = clause.lower()

    if any(k in clause for k in ["shall not", "must not", "prohibited"]):
        return "Prohibition"
    if any(k in clause for k in ["shall", "must"]):
        return "Obligation"
    if any(k in clause for k in ["may", "can"]):
        return "Right"

    return "Neutral"


# ---------------- RISK ENGINE ----------------

RISK_MAP = {
    "Penalty Clause": ["penalty", "fine", "दंड", "जुर्माना"],
    "Indemnity Clause": ["indemnify", "indemnity", "क्षतिपूर्ति"],
    "Termination Risk": ["terminate", "termination", "समाप्त"],
    "Non-Compete Clause": ["non compete", "non-compete", "प्रतिस्पर्धा"],
    "IP Transfer": ["intellectual property", "ip rights", "बौद्धिक संपदा"],
    "Unilateral Rights": ["without notice", "sole discretion", "बिना सूचना"]
}


def detect_risks(clause):
    risks = []
    for risk, keywords in RISK_MAP.items():
        if any(k in clause.lower() for k in keywords):
            risks.append(risk)
    return risks


def risk_level(score):
    if score == 0:
        return "Low"
    if score <= 2:
        return "Medium"
    return "High"


# ---------------- EXPLANATION ----------------

def explain(risks):
    if not risks:
        return "This clause appears balanced and does not pose significant legal risk."
    return "This clause may expose the business to legal risk due to: " + ", ".join(risks)


def mitigation(risks):
    if not risks:
        return "No immediate mitigation required."
    return (
        "Consider renegotiating this clause to ensure mutual obligations, "
        "clear limits on liability, and fair termination conditions."
    )


# ---------------- PDF EXPORT ----------------

def generate_pdf(clauses, results):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer)
    story = []

    story.append(Paragraph("Contract Risk Assessment Report", styles["Title"]))
    story.append(Spacer(1, 12))

    for i, r in enumerate(results):
        story.append(Paragraph(f"<b>Clause {i+1}</b>: {clauses[i]}", styles["Normal"]))
        story.append(Paragraph(f"Clause Type: {r['type']}", styles["Normal"]))
        story.append(Paragraph(f"Risk Level: {r['level']}", styles["Normal"]))
        story.append(Paragraph(f"Explanation: {r['explanation']}", styles["Normal"]))
        story.append(Paragraph(f"Mitigation Advice: {r['mitigation']}", styles["Normal"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------- UI ----------------

st.title("Contract Analysis & Risk Assessment Bot")
st.caption("Plain-language legal insights for SMEs")

text = st.text_area(
    "Paste Contract Text (English / Hindi)",
    height=260,
    value="""
The employee shall indemnify the company.
The company may terminate the agreement without notice.
A penalty of ₹1,00,000 applies for breach.
The employee shall not compete for two years.
"""
)

if st.button("Analyze Contract"):
    audit("Contract analyzed")

    clauses = extract_clauses(text)
    contract_type = classify_contract(text)
    entities = extract_entities(text)

    results = []
    scores = []

    for c in clauses:
        risks = detect_risks(c)
        score = len(risks)
        scores.append(score)

        results.append({
            "type": classify_clause_type(c),
            "level": risk_level(score),
            "explanation": explain(risks),
            "mitigation": mitigation(risks)
        })

    composite_risk = round(sum(scores) / len(scores), 2)

    st.success("Analysis Completed Successfully")

    st.subheader("Contract Overview")
    st.write(f"**Contract Type:** {contract_type}")
    st.write(f"**Overall Risk Score:** {composite_risk}")

    st.subheader("Extracted Key Information")
    st.write(f"**Amounts:** {', '.join(entities['Amounts']) or 'Not detected'}")
    st.write(f"**Dates:** {', '.join(entities['Dates']) or 'Not detected'}")
    st.write(f"**Jurisdiction:** {', '.join(entities['Jurisdiction']) or 'Not detected'}")

    st.subheader("📑 Clause-by-Clause Analysis")

    for i, c in enumerate(clauses):
        st.markdown(f"### Clause {i+1}")
        st.write(c)
        st.write(f"**Clause Type:** {results[i]['type']}")
        st.write(f"**Risk Level:** {results[i]['level']}")
        st.write(f"**Explanation:** {results[i]['explanation']}")
        st.write(f"**Mitigation Advice:** {results[i]['mitigation']}")
        st.markdown("---")

    pdf = generate_pdf(clauses, results)
    audit("PDF report generated")

    st.download_button(
        "Download PDF Report",
        pdf,
        file_name="Contract_Risk_Report.pdf",
        mime="application/pdf"
    )


# ---------------- AUDIT LOG DISPLAY (TEXT) ----------------

st.markdown("---")
if st.button("View Audit Log"):
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE) as f:
            logs = json.load(f)
        for log in logs:
            st.write(f"{log['timestamp']} — {log['action']}")
    else:
        st.info("No audit logs available.")
