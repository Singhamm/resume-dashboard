import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Resume Formatter Demo", layout="wide")
st.title("📝 Resume Formatter Demo (Streamlit)")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"] )
if uploaded_file:
    st.info("Parsing your resume…")
    resp = requests.post(
        f"{API_URL}/upload-resume",
        files={"file": (uploaded_file.name, uploaded_file.getvalue())}
    )
    if resp.ok:
        data = resp.json()
        st.success("Parsed successfully!")

        st.subheader("Parsed Data")
        st.json(data)

        st.subheader("Live Preview")
        html = requests.get(f"{API_URL}/preview/{data['id']}").text
        st.components.v1.html(html, height=400, scrolling=True)

        st.subheader("Download PDF")
        pdf_resp = requests.post(f"{API_URL}/generate-pdf/{data['id']}")
        st.download_button(
            label="📄 Download PDF",
            data=pdf_resp.content,
            file_name="resume.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Oops! Something went wrong.")