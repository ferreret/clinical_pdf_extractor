import streamlit as st
import os
import base64
import base64
from workflows import app_vision, app_google_genai
import utils
from dotenv import load_dotenv

import auth_utils

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Clinical PDF Extractor",
    page_icon="Rx",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Authentication ---
authenticator = auth_utils.setup_authenticator()
try:
    authenticator.login()
except Exception as e:
    st.error(f"Authentication error: {e}")

if st.session_state["authentication_status"]:
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

        # Logout button
        authenticator.logout("Logout", "sidebar")
        st.markdown("---")

        st.markdown("### Workflow Configuration")
        workflow_provider = st.radio(
            "Select Provider",
            options=["Google GenAI (Default)", "Requesty (OpenAI Compatible)"],
            index=0,
            help="Choose the underlying AI provider for extraction.",
        )

        st.markdown("### Model Configuration")
        model_name = st.text_input(
            "Model Name",
            value=(
                "gemini-3-pro-preview"
                if "Google" in workflow_provider
                else "google/gemini-3-pro-preview"
            ),
            help="Enter the model ID (e.g., gemini-3-pro-preview, google/gemini-3-pro-preview)",
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

    # --- System Prompt Configuration ---
    with st.expander("🛠️ System Prompt Configuration", expanded=False):
        # Load default prompt
        try:
            with open("prompts/vision_extraction.md", "r", encoding="utf-8") as f:
                default_prompt = f.read()
        except Exception:
            default_prompt = "You are an expert medical data extractor..."

        system_prompt = st.text_area(
            "Edit System Prompt",
            value=default_prompt,
            height=600,
            help="Modify the instructions for the AI extractor.",
        )

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

            col_btn, col_timer = st.columns([1, 2])
            with col_btn:
                start_btn = st.button("Start Extraction")

            timer_placeholder = col_timer.empty()

            if start_btn:
                import time

                start_time = time.time()

                with st.spinner("Processing document..."):
                    # Prepare state
                    file_bytes = uploaded_file.read()
                    initial_state = {
                        "pdf_bytes": file_bytes,
                        "images": [],
                        "extracted_data": [],
                        "errors": [],
                        "model_name": model_name,
                        "system_prompt": system_prompt,
                    }

                    # Run Workflow
                    try:
                        if "Google" in workflow_provider:
                            result = app_google_genai.invoke(initial_state)
                        else:
                            result = app_vision.invoke(initial_state)

                        end_time = time.time()
                        elapsed_time = end_time - start_time
                        timer_placeholder.success(
                            f"Extraction completed in {elapsed_time:.2f} seconds"
                        )

                        # Display Results
                        if result.get("errors"):
                            for error in result["errors"]:
                                st.error(error)

                        data = result.get("extracted_data", [])
                        if not data:
                            st.info("No data extracted.")

                        st.write(
                            f"Debug: Total images in result: {len(result.get('images', []))}"
                        )

                        # Group elements by page
                        elements_by_page = {}
                        tests_by_page = {}
                        urine_details_by_page = {}

                        all_elements = []
                        all_tests = []
                        all_urine_details = []

                        # Flatten all elements from all extraction results
                        for item in data:
                            content = item["content"]
                            if isinstance(content, str):
                                st.error(f"Debug: Content is string: {content}")
                                continue
                            all_elements.extend(content.get("elements", []))
                            all_tests.extend(content.get("tests", []))

                            urine = content.get("urine_details")
                            if urine:
                                all_urine_details.append(urine)

                        if not all_elements and not all_tests:
                            st.warning("No data found.")
                        else:
                            # Group by page number
                            for element in all_elements:
                                if isinstance(element, dict):
                                    page_num = element.get("page_number")
                                    if page_num:
                                        if page_num not in elements_by_page:
                                            elements_by_page[page_num] = []
                                        elements_by_page[page_num].append(element)

                            for test in all_tests:
                                if isinstance(test, dict):
                                    page_num = test.get("page_number")
                                    if page_num:
                                        if page_num not in tests_by_page:
                                            tests_by_page[page_num] = []
                                        tests_by_page[page_num].append(test)

                            for urine in all_urine_details:
                                if isinstance(urine, dict):
                                    page_num = urine.get("page_number")
                                    if page_num:
                                        urine_details_by_page[page_num] = urine

                            # Sort pages
                            all_pages = (
                                set(elements_by_page.keys())
                                | set(tests_by_page.keys())
                                | set(urine_details_by_page.keys())
                            )
                            sorted_pages = sorted(all_pages)

                            for page_num in sorted_pages:
                                page_elements = elements_by_page.get(page_num, [])
                                page_tests = tests_by_page.get(page_num, [])
                                page_urine = urine_details_by_page.get(page_num)

                                with st.expander(
                                    f"Page {page_num} - Extracted Data", expanded=True
                                ):
                                    # 1. Display General Elements
                                    if page_elements:
                                        st.markdown("### General Information")
                                        for element in page_elements:
                                            st.markdown(
                                                f"**{element['label']}**: {element['value']}"
                                            )

                                    # 2. Display Tests
                                    if page_tests:
                                        st.markdown("### Clinical Tests")
                                        st.table(page_tests)

                                    # 3. Display Urine Details
                                    if page_urine:
                                        st.markdown("### Urine Details")
                                        st.json(page_urine)

                                    # 4. Draw Bounding Boxes
                                    try:
                                        if "images" in result:
                                            page_idx = page_num - 1
                                            if 0 <= page_idx < len(result["images"]):
                                                st.write(
                                                    f"Debug: Drawing on image {page_idx} for page {page_num}"
                                                )
                                                # Create a copy of the image to draw on
                                                image = result["images"][
                                                    page_idx
                                                ].copy()

                                                # Define color mapping
                                                COLOR_MAPPING = {
                                                    "Paciente": "red",
                                                    "FechaNacimiento": "red",
                                                    "Sexo": "red",
                                                    "DocumentoIdentidad": "red",
                                                    "Telefono": "red",
                                                    "NombreMedico": "purple",
                                                    "NumeroColegiado": "purple",
                                                    "NumeroPeticion": "blue",
                                                }

                                                # Draw General Elements
                                                for element in page_elements:
                                                    if element.get("bounding_box"):
                                                        box_color = COLOR_MAPPING.get(
                                                            element["label"], "green"
                                                        )
                                                        image = utils.draw_bounding_box(
                                                            image,
                                                            element["bounding_box"],
                                                            label=element["label"],
                                                            color=box_color,
                                                        )

                                                # Draw Tests (Orange)
                                                # Draw Test boxes
                                                for test in page_tests:
                                                    if test.get("bounding_box"):
                                                        image = utils.draw_bounding_box(
                                                            image,
                                                            test["bounding_box"],
                                                            label=test["description"],
                                                            color="yellow",
                                                        )

                                                # Draw Urine Details (Yellow)
                                                if page_urine and page_urine.get(
                                                    "bounding_box"
                                                ):
                                                    image = utils.draw_bounding_box(
                                                        image,
                                                        page_urine["bounding_box"],
                                                        label="Urine Info",
                                                        color="#FFD700",  # Gold/Yellow
                                                    )

                                                st.image(
                                                    image,
                                                    caption=f"Visualized Page {page_num}",
                                                    width="stretch",
                                                )
                                            else:
                                                st.warning(
                                                    f"Page number {page_num} out of range for images."
                                                )
                                        else:
                                            st.warning(
                                                "Images not available for visualization."
                                            )

                                    except Exception as img_e:
                                        st.warning(
                                            f"Could not visualize bounding boxes: {img_e}"
                                        )

                    except Exception as e:
                        st.error(f"An error occurred during execution: {str(e)}")

    else:
        st.info("Please upload a PDF to begin.")

elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your username and password")
