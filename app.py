import streamlit as st
import pandas as pd
import json
import os
from google import genai

# ======= Gemini Client =======
api_key = os.environ.get("GENIE_API_KEY")  # Set this in Streamlit secrets or env vars
client = genai.Client(api_key=api_key)

# ======= Prompt =======
prompt_text = """
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

# ======= JSON Schema =======
schema = {
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

# ======= Streamlit UI =======
st.title("AIAG PFD Analyzer (APQP 3rd Edition)")
st.write("Upload your PFD (Excel or CSV) and get a structured JSON analysis.")

uploaded_file = st.file_uploader("Upload PFD", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Preview of uploaded file")
    st.dataframe(df.head())

    # Convert dataframe to text
    content_text = df.to_csv(index=False)

    # Call Gemini
    with st.spinner("Analyzing PFD..."):
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[{"parts": [{"text": prompt_text}, {"text": content_text}]}],
            config={"response_mime_type": "application/json", "response_schema": schema}
        )

    result = json.loads(response.text)

    st.subheader("✅ JSON Output")
    st.json(result)

    # Download button
    st.download_button(
        "Download JSON",
        json.dumps(result, indent=2),
        file_name="pfd_analysis_output.json"
    )
