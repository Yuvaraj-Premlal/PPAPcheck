import streamlit as st
import pandas as pd
import json
import os
from google import genai

# ======= Gemini Client =======
api_key = os.environ.get("GENIE_API_KEY")  # Set this in Streamlit secrets or env vars
client = genai.Client(api_key=api_key)

# ======= Prompts =======
pfd_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Analyze the provided Process Flow Diagram (PFD).

Use the latest AIAG guidance (APQP 3rd Edition, March 2024).

Return JSON only with two keys:

1. summary:
   - product_outline: story-like description of the product/component
   - total_steps
   - machines_tools_list
   - special_characteristics_count
   - pfmea_refs
   - control_plan_refs

2. missed_points:
   - Array of objects:
     - issue
     - severity (high/medium/low)
     - row_content (string: include the exact row content from the PFD)
     - suggestion
"""

cp_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Analyze the provided Control Plan.

Use the latest AIAG guidance (Control Plan Reference Manual 1st Edition, March 2024).

Return JSON only with two keys:

1. summary:
   - product_outline: short story-like description of what this Control Plan covers
   - total_steps
   - key_controls_list
   - special_characteristics_count
   - pfd_refs
   - pfmea_refs

2. missed_points:
   - Array of objects:
     - issue
     - severity (high/medium/low)
     - row_content (string: include the exact row content from the Control Plan)
     - suggestion
"""

pfmea_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Analyze the provided PFMEA.

Use the latest AIAG-VDA FMEA Handbook (2019) as reference.

Return JSON only with two keys:

1. summary:
   - product_outline: story-like description of the process/product
   - total_failure_modes
   - high_rpn_count
   - pfd_refs
   - control_plan_refs

2. missed_points:
   - Array of objects:
     - issue
     - severity (high/medium/low)
     - row_content (string: include the exact row content from the PFMEA)
     - suggestion
"""

consistency_prompt = """
Check consistency between PFD, Control Plan, and PFMEA.

- Ensure every process step in PFD is represented in Control Plan.
- Ensure every Control Plan entry has a corresponding PFMEA entry.
- Check that PFMEA references trace back to PFD or Control Plan.

For each mismatch, clearly include:
- source_doc (e.g., PFD)
- target_doc (e.g., Control Plan)
- content (the actual row content missing in the target doc)
- suggestion (how to correct the linkage)

Return JSON only.
"""

# ======= Schemas =======
single_doc_schema = {
    "type": "object",
    "properties": {
        "summary": {"type": "object"},
        "missed_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "severity": {"type": "string"},
                    "row_content": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["issue", "severity", "row_content", "suggestion"]
            }
        }
    },
    "required": ["summary", "missed_points"]
}

consistency_schema = {
    "type": "object",
    "properties": {
        "missing_links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_doc": {"type": "string"},
                    "target_doc": {"type": "string"},
                    "content": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["source_doc", "target_doc", "content", "suggestion"]
            }
        }
    },
    "required": ["missing_links"]
}

# ======= Streamlit UI =======
st.title("AIAG Document Analyzer (PFD, Control Plan, PFMEA, Consistency)")

tabs = st.tabs(["📘 PFD", "📗 Control Plan", "📕 PFMEA", "🔗 Consistency Checker"])

# ---- PFD ----
with tabs[0]:
    st.header("📘 Process Flow Diagram Analyzer")
    uploaded_file = st.file_uploader("Upload PFD", type=["xlsx", "csv"], key="pfd")
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.dataframe(df.head())
        content_text = df.to_csv(index=False)
        with st.spinner("Analyzing PFD..."):
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": pfd_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": single_doc_schema}
            )
        result = json.loads(response.text)
        st.json(result)
        st.download_button("Download JSON", json.dumps(result, indent=2), file_name="pfd_analysis.json")

# ---- Control Plan ----
with tabs[1]:
    st.header("📗 Control Plan Analyzer")
    uploaded_file = st.file_uploader("Upload Control Plan", type=["xlsx", "csv"], key="cp")
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.dataframe(df.head())
        content_text = df.to_csv(index=False)
        with st.spinner("Analyzing Control Plan..."):
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": cp_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": single_doc_schema}
            )
        result = json.loads(response.text)
        st.json(result)
        st.download_button("Download JSON", json.dumps(result, indent=2), file_name="cp_analysis.json")

# ---- PFMEA ----
with tabs[2]:
    st.header("📕 PFMEA Analyzer")
    uploaded_file = st.file_uploader("Upload PFMEA", type=["xlsx", "csv"], key="pfmea")
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.dataframe(df.head())
        content_text = df.to_csv(index=False)
        with st.spinner("Analyzing PFMEA..."):
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": pfmea_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": single_doc_schema}
            )
        result = json.loads(response.text)
        st.json(result)
        st.download_button("Download JSON", json.dumps(result, indent=2), file_name="pfmea_analysis.json")

# ---- Consistency Checker ----
with tabs[3]:
    st.header("🔗 Consistency Checker (PFD ↔ CP ↔ PFMEA)")
    uploaded_pfd = st.file_uploader("Upload PFD", type=["xlsx", "csv"], key="cons_pfd")
    uploaded_cp = st.file_uploader("Upload Control Plan", type=["xlsx", "csv"], key="cons_cp")
    uploaded_pfmea = st.file_uploader("Upload PFMEA", type=["xlsx", "csv"], key="cons_pfmea")

    if uploaded_pfd and uploaded_cp and uploaded_pfmea:
        df_pfd = pd.read_csv(uploaded_pfd) if uploaded_pfd.name.endswith(".csv") else pd.read_excel(uploaded_pfd)
        df_cp = pd.read_csv(uploaded_cp) if uploaded_cp.name.endswith(".csv") else pd.read_excel(uploaded_cp)
        df_pfmea = pd.read_csv(uploaded_pfmea) if uploaded_pfmea.name.endswith(".csv") else pd.read_excel(uploaded_pfmea)

        st.subheader("Preview of uploaded documents")
        st.write("📘 PFD"); st.dataframe(df_pfd.head())
        st.write("📗 Control Plan"); st.dataframe(df_cp.head())
        st.write("📕 PFMEA"); st.dataframe(df_pfmea.head())

        combined_text = f"""
=== PFD ===
{df_pfd.to_csv(index=False)}

=== CONTROL PLAN ===
{df_cp.to_csv(index=False)}

=== PFMEA ===
{df_pfmea.to_csv(index=False)}
"""

        with st.spinner("Checking cross-linkages..."):
            response_consistency = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": consistency_prompt}, {"text": combined_text}]}],
                config={"response_mime_type": "application/json", "response_schema": consistency_schema}
            )
        consistency_result = json.loads(response_consistency.text)
        st.json(consistency_result)
        st.download_button("Download JSON", json.dumps(consistency_result, indent=2), file_name="consistency_analysis.json")
