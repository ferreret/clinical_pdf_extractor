# Clinical PDF Extractor

A Streamlit application designed to extract structured data from clinical analysis PDF documents using AI. This tool supports two workflows: a combination of Mistral OCR and Requesty (OpenAI-compatible API), and a direct Vision-based extraction using Requesty.

## Features

-   **Dual Workflows**:
    -   **Mistral OCR + Requesty**: Uses Mistral AI for Optical Character Recognition (OCR) to extract text, followed by Requesty for structured data extraction.
    -   **Requesty Vision (Direct)**: Uses Vision-capable models (like GPT-4o) via Requesty to extract data directly from document images.
-   **Streamlit Interface**: User-friendly web interface for uploading PDFs and viewing results.
-   **PDF Preview**: View the uploaded PDF alongside the extracted data.
-   **LangGraph Integration**: Uses LangGraph for robust and stateful workflow management.

## Prerequisites

-   Python 3.10+
-   `poppler-utils` (required for `pdf2image`)
    -   Linux: `sudo apt-get install poppler-utils`
    -   macOS: `brew install poppler`
-   API Keys:
    -   **Mistral API Key**: For OCR capabilities.
    -   **Requesty API Key**: For LLM and Vision capabilities.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ferreret/clinical_pdf_extractor.git
    cd clinical_pdf_extractor
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Configuration**:
    Create a `.env` file in the root directory (copy from `.env.example` if available) and add your API keys:
    ```env
    MISTRAL_API_KEY=your_mistral_api_key
    REQUESTY_API_KEY=your_requesty_api_key
    REQUESTY_BASE_URL=https://router.requesty.ai/v1
    ```

## Usage

1.  **Run the Streamlit app**:
    ```bash
    streamlit run app.py
    ```

2.  **Open your browser**:
    The app should automatically open at `http://localhost:8501`.

3.  **Extract Data**:
    -   Select your preferred workflow from the sidebar.
    -   Enter the Requesty Model Name (e.g., `gpt-4o-mini`, `gpt-4o`).
    -   Upload a clinical analysis PDF.
    -   Click "Start Extraction".

## Project Structure

-   `app.py`: Main Streamlit application entry point.
-   `workflows.py`: Defines the LangGraph workflows for OCR and Vision extraction.
-   `utils.py`: Helper functions for PDF processing and image handling.
-   `requirements.txt`: Python dependencies.

## License

[MIT](LICENSE)
