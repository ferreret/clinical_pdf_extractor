import streamlit as st
import os
import base64
import base64
from workflows import app_vision
import utils
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

    st.markdown("### Model Configuration")
    model_name = st.text_input(
        "Requesty Model Name",
        value="vertex/gemini-3-pro-preview",
        help="Enter the model ID supported by Requesty (e.g., gpt-4o, claude-3-5-sonnet-20240620)",
    )

    st.markdown("---")
    st.markdown("### API Status")

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
                    "extracted_data": [],
                    "errors": [],
                    "model_name": model_name,
                }

                # Run Workflow
                try:
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
                            # item['content'] is now a dict (model_dump of ExtractionResult)
                            elements = item["content"].get("elements", [])
                            if not elements:
                                st.warning("No elements found.")
                            else:
                                for element in elements:
                                    st.markdown(
                                        f"**{element['label']}**: {element['value']}"
                                    )
                                    if element.get("bounding_box"):
                                        st.caption(
                                            f"Bounding Box: {element['bounding_box']} (Page {element.get('page_number', '?')})"
                                        )

                                        # Draw and display image with bounding box
                                        try:
                                            # Get the image for this page based on page_number
                                            page_num = element.get("page_number")
                                            if page_num and "images" in result:
                                                page_idx = page_num - 1
                                                if (
                                                    0
                                                    <= page_idx
                                                    < len(result["images"])
                                                ):
                                                    image = result["images"][
                                                        page_idx
                                                    ].copy()  # Copy to avoid modifying original
                                                    annotated_image = (
                                                        utils.draw_bounding_box(
                                                            image,
                                                            element["bounding_box"],
                                                            label=element["label"],
                                                        )
                                                    )
                                                    st.image(
                                                        annotated_image,
                                                        caption=f"Visualized {element['label']} on Page {page_num}",
                                                        width="stretch",
                                                    )
                                                else:
                                                    st.warning(
                                                        f"Page number {page_num} out of range."
                                                    )
                                            else:
                                                st.warning(
                                                    "Page number missing or images not available."
                                                )

                                        except Exception as img_e:
                                            st.warning(
                                                f"Could not visualize bounding box: {img_e}"
                                            )

                except Exception as e:
                    st.error(f"An error occurred during execution: {str(e)}")

else:
    st.info("Please upload a PDF to begin.")
