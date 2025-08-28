import streamlit as st
import pandas as pd
import json
import os
import io
from google import genai

# ======= Gemini Client =======
api_key = os.environ.get("GENIE_API_KEY")
client = genai.Client(api_key=api_key)

# ======= Helper: Convert JSON to Excel =======
def json_to_excel(json_data, sheet_name="Analysis"):
    output = io.BytesIO()
    df = pd.json_normalize(json_data) if isinstance(json_data, dict) else pd.DataFrame(json_data)
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# ======= Prompts =======
# (Same as before, skipping for brevity...)

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

        st.subheader("✅ JSON Output")
        st.json(result)

        st.subheader("📊 Missed Points (Table)")
        if result.get("missed_points"):
            df_out = pd.DataFrame(result["missed_points"])
            st.dataframe(df_out)

            # Download Excel
            excel_data = json_to_excel(result["missed_points"], "PFD_Missed_Points")
            st.download_button("Download Excel", excel_data, "pfd_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # JSON download
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

        st.subheader("✅ JSON Output")
        st.json(result)

        st.subheader("📊 Missed Points (Table)")
        if result.get("missed_points"):
            df_out = pd.DataFrame(result["missed_points"])
            st.dataframe(df_out)
            excel_data = json_to_excel(result["missed_points"], "CP_Missed_Points")
            st.download_button("Download Excel", excel_data, "cp_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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

        st.subheader("✅ JSON Output")
        st.json(result)

        st.subheader("📊 Missed Points (Table)")
        if result.get("missed_points"):
            df_out = pd.DataFrame(result["missed_points"])
            st.dataframe(df_out)
            excel_data = json_to_excel(result["missed_points"], "PFMEA_Missed_Points")
            st.download_button("Download Excel", excel_data, "pfmea_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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

        st.subheader("✅ JSON Output")
        st.json(consistency_result)

        st.subheader("📊 Missing Links (Table)")
        if consistency_result.get("missing_links"):
            df_out = pd.DataFrame(consistency_result["missing_links"])
            st.dataframe(df_out)
            excel_data = json_to_excel(consistency_result["missing_links"], "Consistency_Check")
            st.download_button("Download Excel", excel_data, "consistency_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.download_button("Download JSON", json.dumps(consistency_result, indent=2), file_name="consistency_analysis.json")
