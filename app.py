import streamlit as st
import pandas as pd
import json
import os
from google import genai

# ======= Gemini Client =======
api_key = os.environ.get("GENIE_API_KEY")  # Set this in Streamlit secrets or env vars
client = genai.Client(api_key=api_key)

# ======= PFD Prompt =======
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
     - row_number (integer, must clearly indicate the row)
     - suggestion
"""

pfd_schema = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "product_outline": {"type": "string"},
                "total_steps": {"type": "integer"},
                "machines_tools_list": {"type": "array", "items": {"type": "string"}},
                "special_characteristics_count": {"type": "integer"},
                "pfmea_refs": {"type": "array", "items": {"type": "string"}},
                "control_plan_refs": {"type": "array", "items": {"type": "string"}}
            },
            "required": [
                "product_outline", "total_steps", "machines_tools_list",
                "special_characteristics_count", "pfmea_refs", "control_plan_refs"
            ]
        },
        "missed_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "severity": {"type": "string"},
                    "row_number": {"type": "integer"},
                    "suggestion": {"type": "string"}
                },
                "required": ["issue", "severity", "row_number", "suggestion"]
            }
        }
    },
    "required": ["summary", "missed_points"]
}

# ======= Control Plan Prompt =======
cp_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Analyze the provided Control Plan (CP).

Use the latest AIAG guidance (Control Plan Reference Manual – 1st Edition, March 2024).

Return JSON only with two keys:

1. summary:
   - product_outline: story-like description of the product/component
   - total_control_items
   - safe_launch_controls (count + description)
   - ownership_clarity (Yes/No + details)
   - automation_readiness (Yes/No + comments)

2. missed_points:
   - Array of objects:
     - issue
     - severity (high/medium/low)
     - row_number (integer, must clearly indicate the row)
     - suggestion
"""

cp_schema = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "product_outline": {"type": "string"},
                "total_control_items": {"type": "integer"},
                "safe_launch_controls": {"type": "object", "properties": {
                    "count": {"type": "integer"},
                    "description": {"type": "string"}
                }},
                "ownership_clarity": {"type": "string"},
                "automation_readiness": {"type": "string"}
            },
            "required": [
                "product_outline", "total_control_items", "safe_launch_controls",
                "ownership_clarity", "automation_readiness"
            ]
        },
        "missed_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "severity": {"type": "string"},
                    "row_number": {"type": "integer"},
                    "suggestion": {"type": "string"}
                },
                "required": ["issue", "severity", "row_number", "suggestion"]
            }
        }
    },
    "required": ["summary", "missed_points"]
}

# ======= Streamlit UI =======
st.title("📊 AIAG PPAP Analyzer Suite")
tabs = st.tabs(["🔹 PFD Analyzer", "🔹 Control Plan Analyzer"])

# --- PFD Analyzer ---
with tabs[0]:
    st.header("AIAG PFD Analyzer (APQP 3rd Edition, 2024)")
    uploaded_file = st.file_uploader("Upload PFD (Excel or CSV)", type=["xlsx", "csv"], key="pfd")

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("Preview of uploaded file")
        st.dataframe(df.head())

        content_text = df.to_csv(index=False)

        with st.spinner("Analyzing PFD..."):
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": pfd_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": pfd_schema}
            )

        result = json.loads(response.text)

        st.subheader("✅ JSON Output")
        st.json(result)

        st.download_button(
            "Download JSON",
            json.dumps(result, indent=2),
            file_name="pfd_analysis_output.json"
        )

# --- Control Plan Analyzer ---
with tabs[1]:
    st.header("AIAG Control Plan Analyzer (CP 1st Edition, 2024)")
    uploaded_cp = st.file_uploader("Upload Control Plan (Excel or CSV)", type=["xlsx", "csv"], key="cp")

    if uploaded_cp:
        if uploaded_cp.name.endswith(".csv"):
            df_cp = pd.read_csv(uploaded_cp)
        else:
            df_cp = pd.read_excel(uploaded_cp)

        st.subheader("Preview of uploaded Control Plan")
        st.dataframe(df_cp.head())

        content_text = df_cp.to_csv(index=False)

        with st.spinner("Analyzing Control Plan..."):
            response_cp = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": cp_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": cp_schema}
            )

        cp_result = json.loads(response_cp.text)

        st.subheader("✅ JSON Output")
        st.json(cp_result)

        st.download_button(
            "Download JSON",
            json.dumps(cp_result, indent=2),
            file_name="control_plan_analysis_output.json"
        )
