import streamlit as st
import os
import base64
from workflows import app_ocr, app_vision
from dotenv import load_dotenv

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Clinical PDF Extractor",
    page_icon="Rx",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #4e73df;
        color: white;
    }
    .stButton>button:hover {
        background-color: #2e59d9;
        color: white;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .css-1d391kg {
        padding-top: 3.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configuration")

    workflow_choice = st.radio(
        "Select Extraction Workflow",
        ("Mistral OCR + Requesty", "Requesty Vision (Direct)"),
    )

    st.markdown("### Model Configuration")
    model_name = st.text_input(
        "Requesty Model Name",
        value="gpt-4o-mini",
        help="Enter the model ID supported by Requesty (e.g., gpt-4o, claude-3-5-sonnet-20240620)",
    )

    st.markdown("---")
    st.markdown("### API Status")

    if os.getenv("MISTRAL_API_KEY"):
        st.success("Mistral API Key detected")
    else:
        st.error("Mistral API Key missing")

    if os.getenv("REQUESTY_API_KEY"):
        st.success("Requesty API Key detected")
    else:
        st.error("Requesty API Key missing")

# --- Main Content ---
st.title("📄 Clinical Analysis Extractor")
st.markdown("Upload a clinical analysis PDF to extract structured data.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Original Document")
        # Display PDF
        base64_pdf = base64.b64encode(uploaded_file.read()).decode("utf-8")
        uploaded_file.seek(0)  # Reset pointer
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#view=FitH" width="100%" height="1200" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

    with col2:
        st.subheader("Extracted Information")

        if st.button("Start Extraction"):
            with st.spinner("Processing document..."):
                # Prepare state
                file_bytes = uploaded_file.read()
                initial_state = {
                    "pdf_bytes": file_bytes,
                    "images": [],
                    "current_page_index": 0,
                    "extracted_data": [],
                    "errors": [],
                    "model_name": model_name,
                }

                # Run Workflow
                try:
                    if workflow_choice == "Mistral OCR + Requesty":
                        result = app_ocr.invoke(initial_state)
                    else:
                        result = app_vision.invoke(initial_state)

                    # Display Results
                    if result.get("errors"):
                        for error in result["errors"]:
                            st.error(error)

                    data = result.get("extracted_data", [])
                    if not data:
                        st.info("No data extracted.")

                    for item in data:
                        with st.expander(
                            f"Page {item['page']} - {item['source']}", expanded=True
                        ):
                            st.markdown(item["content"])

                except Exception as e:
                    st.error(f"An error occurred during execution: {str(e)}")

else:
    st.info("Please upload a PDF to begin.")
