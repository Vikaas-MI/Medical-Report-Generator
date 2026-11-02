import requests
import streamlit as st

# Base URL of the FastAPI backend. Change if the backend runs elsewhere.
API_BASE_URL = "http://localhost:8000"
GENERATE_ENDPOINT = f"{API_BASE_URL}/generate-report"

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

st.set_page_config(page_title="Medical Report Generator", page_icon="🩺")

st.title("🩺 Medical Report Generator")
st.caption(
    "Upload a report template and the supporting medical data. "
    "The backend drafts, validates, and generates a formatted report."
)

with st.form("report_form"):
    template_file = st.file_uploader(
        "Template document (.docx)",
        type=["docx"],
        help="A Word document whose headings define the report structure.",
    )
    support_file = st.file_uploader(
        "Supporting medical data (.docx)",
        type=["docx"],
        help="A Word document containing the source clinical information.",
    )

    submitted = st.form_submit_button("Generate report")

if submitted:
    if template_file is None or support_file is None:
        st.warning("Please upload both the template and the supporting document.")
    else:
        with st.spinner("Generating report. This may take a moment..."):
            try:
                files = {
                    "template": (
                        template_file.name,
                        template_file.getvalue(),
                        DOCX_MIME,
                    ),
                    "support": (
                        support_file.name,
                        support_file.getvalue(),
                        DOCX_MIME,
                    ),
                }

                response = requests.post(GENERATE_ENDPOINT, files=files, timeout=300)
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not reach the backend. "
                    f"Is the API running at {API_BASE_URL}?"
                )
            except requests.exceptions.Timeout:
                st.error("The request timed out. Try again or increase the timeout.")
            except requests.exceptions.RequestException as exc:
                st.error(f"Request failed: {exc}")
            else:
                if response.status_code == 200:
                    st.success("Report generated successfully.")
                    st.download_button(
                        label="Download report.docx",
                        data=response.content,
                        file_name="report.docx",
                        mime=DOCX_MIME,
                    )
                else:
                    st.error(
                        f"Backend returned {response.status_code}:\n\n{response.text}"
                    )
