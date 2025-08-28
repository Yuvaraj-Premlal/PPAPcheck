import streamlit as st
import pandas as pd
import json
import os
from google import genai

# ======= Gemini Client =======
api_key = os.environ.get("GENIE_API_KEY")  # Set this in Streamlit secrets or env vars
client = genai.Client(api_key=api_key)

# ======= PFD Prompt =======
# ======= PFD Prompt (updated for row_content) =======
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
     - row_content (string: include the full row content from the PFD)
     - suggestion
"""

# ======= Updated schema =======
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
                    "row_content": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["issue", "severity", "row_content", "suggestion"]
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

# ======= PFMEA Prompt =======
pfmea_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Analyze the provided PFMEA.

Use the latest AIAG–VDA FMEA Handbook (1st Edition, 2019).

Return JSON only with two keys:

1. summary:
   - product_outline: story-like description of the product/component
   - total_failure_modes
   - high_rpn_count
   - action_priority_summary (High/Medium/Low distribution)
   - linkage_to_pfd (Yes/No + examples)
   - linkage_to_control_plan (Yes/No + examples)

2. missed_points:
   - Array of objects:
     - issue
     - severity (high/medium/low)
     - row_number (integer, must clearly indicate the row)
     - suggestion
"""

pfmea_schema = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "product_outline": {"type": "string"},
                "total_failure_modes": {"type": "integer"},
                "high_rpn_count": {"type": "integer"},
                "action_priority_summary": {"type": "object", "properties": {
                    "high": {"type": "integer"},
                    "medium": {"type": "integer"},
                    "low": {"type": "integer"}
                }},
                "linkage_to_pfd": {"type": "string"},
                "linkage_to_control_plan": {"type": "string"}
            },
            "required": [
                "product_outline", "total_failure_modes", "high_rpn_count",
                "action_priority_summary", "linkage_to_pfd", "linkage_to_control_plan"
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
# ======= Consistency Prompt =======
consistency_prompt = """
You are a Quality Assurance assistant for PPAP documentation.
Check the consistency between Process Flow Diagram (PFD), Control Plan (CP), and PFMEA.

Rules:
- Every process step in PFD must appear in Control Plan.
- Every control in Control Plan must be referenced in PFMEA.
- Any missing linkage must be identified.

Return JSON only with two keys:

1. summary:
   - total_pfd_steps
   - total_cp_controls
   - total_pfmea_entries
   - linked_pfd_to_cp (count)
   - linked_cp_to_pfmea (count)
   - linkage_completeness (percentage of proper linkages)

2. missing_links:
   - Array of objects:
     - from_document (PFD / CP)
     - missing_in (CP / PFMEA)
     - row_number (integer where the issue occurs)
     - description
     - suggestion
"""

consistency_schema = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "total_pfd_steps": {"type": "integer"},
                "total_cp_controls": {"type": "integer"},
                "total_pfmea_entries": {"type": "integer"},
                "linked_pfd_to_cp": {"type": "integer"},
                "linked_cp_to_pfmea": {"type": "integer"},
                "linkage_completeness": {"type": "number"}
            },
            "required": [
                "total_pfd_steps", "total_cp_controls", "total_pfmea_entries",
                "linked_pfd_to_cp", "linked_cp_to_pfmea", "linkage_completeness"
            ]
        },
        "missing_links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from_document": {"type": "string"},
                    "missing_in": {"type": "string"},
                    "row_number": {"type": "integer"},
                    "description": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["from_document", "missing_in", "row_number", "description", "suggestion"]
            }
        }
    },
    "required": ["summary", "missing_links"]
}

# ======= Streamlit UI =======
st.title("📊 AIAG PPAP Analyzer Suite")
tabs = st.tabs([
    "🔹 PFD Analyzer",
    "🔹 Control Plan Analyzer",
    "🔹 PFMEA Analyzer",
    "🔹 Consistency Checker"
])

# --- PFD Analyzer ---
with tabs[0]:
# ======= Streamlit UI =======
   st.title("📘 AIAG PFD Analyzer (APQP 3rd Edition)")

   uploaded_file = st.file_uploader("Upload PFD (Excel or CSV)", type=["xlsx", "csv"])

   if uploaded_file:
       if uploaded_file.name.endswith(".csv"):
           df = pd.read_csv(uploaded_file)
       else:
           df = pd.read_excel(uploaded_file)

       st.subheader("Preview of uploaded file")
       st.dataframe(df.head())

       content_text = df.to_csv(index=False)

       # Call Gemini
       with st.spinner("Analyzing PFD..."):
           response = client.models.generate_content(
               model="gemini-1.5-flash",
               contents=[{"parts": [{"text": pfd_prompt}, {"text": content_text}]}],
               config={"response_mime_type": "application/json", "response_schema": pfd_schema}
        )

       result = json.loads(response.text)

       st.subheader("✅ JSON Output")
       st.json(result)

    # ======= Display as HTML table =======
       if result.get("missed_points"):
           df_missed = pd.DataFrame(result["missed_points"])
           st.subheader("📊 Missed Points (HTML Table)")
           st.write(df_missed.to_html(index=False, escape=False), unsafe_allow_html=True)

    # Download JSON
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

# --- PFMEA Analyzer ---
with tabs[2]:
    st.header("AIAG–VDA PFMEA Analyzer (1st Edition, 2019)")
    uploaded_pfmea = st.file_uploader("Upload PFMEA (Excel or CSV)", type=["xlsx", "csv"], key="pfmea")

    if uploaded_pfmea:
        if uploaded_pfmea.name.endswith(".csv"):
            df_pfmea = pd.read_csv(uploaded_pfmea)
        else:
            df_pfmea = pd.read_excel(uploaded_pfmea)

        st.subheader("Preview of uploaded PFMEA")
        st.dataframe(df_pfmea.head())

        content_text = df_pfmea.to_csv(index=False)

        with st.spinner("Analyzing PFMEA..."):
            response_pfmea = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": pfmea_prompt}, {"text": content_text}]}],
                config={"response_mime_type": "application/json", "response_schema": pfmea_schema}
            )

        pfmea_result = json.loads(response_pfmea.text)

        st.subheader("✅ JSON Output")
        st.json(pfmea_result)

        st.download_button(
            "Download JSON",
            json.dumps(pfmea_result, indent=2),
            file_name="pfmea_analysis_output.json"
        )
#consistency checker
with tabs[3]:
    st.header("🔗 Consistency Checker (PFD ↔ CP ↔ PFMEA)")
    uploaded_pfd = st.file_uploader("Upload PFD", type=["xlsx", "csv"], key="cons_pfd")
    uploaded_cp = st.file_uploader("Upload Control Plan", type=["xlsx", "csv"], key="cons_cp")
    uploaded_pfmea = st.file_uploader("Upload PFMEA", type=["xlsx", "csv"], key="cons_pfmea")

    if uploaded_pfd and uploaded_cp and uploaded_pfmea:
        # Load all three
        df_pfd = pd.read_csv(uploaded_pfd) if uploaded_pfd.name.endswith(".csv") else pd.read_excel(uploaded_pfd)
        df_cp = pd.read_csv(uploaded_cp) if uploaded_cp.name.endswith(".csv") else pd.read_excel(uploaded_cp)
        df_pfmea = pd.read_csv(uploaded_pfmea) if uploaded_pfmea.name.endswith(".csv") else pd.read_excel(uploaded_pfmea)

        st.subheader("Preview of uploaded documents")
        st.write("📘 PFD"); st.dataframe(df_pfd.head())
        st.write("📗 Control Plan"); st.dataframe(df_cp.head())
        st.write("📕 PFMEA"); st.dataframe(df_pfmea.head())

        # Convert all three to text
        pfd_text = df_pfd.to_csv(index=False)
        cp_text = df_cp.to_csv(index=False)
        pfmea_text = df_pfmea.to_csv(index=False)

        combined_text = f"""
=== PFD ===
{pfd_text}

=== CONTROL PLAN ===
{cp_text}

=== PFMEA ===
{pfmea_text}
"""

        with st.spinner("Checking cross-linkages..."):
            response_consistency = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"parts": [{"text": consistency_prompt}, {"text": combined_text}]}],
                config={"response_mime_type": "application/json", "response_schema": consistency_schema}
            )

        consistency_result = json.loads(response_consistency.text)

        st.subheader("✅ JSON Output")
        st.json(consistency_result)

        st.download_button(
            "Download JSON",
            json.dumps(consistency_result, indent=2),
            file_name="consistency_analysis_output.json"
        )


