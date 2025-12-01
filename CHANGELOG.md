# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2025-12-01

### Changed
- **API Error Fix**: Investigated `openai.APIStatusError: Error code: 424` related to "Invalid provider response format".
- **Refactoring**: Preparing to remove strict `response_format` enforcement for better compatibility with Requesty/Gemini.

## [0.6.3] - 2025-12-01

### Added
- **Structured Extraction**: Added extraction of `tests` (array) and `urine_details` (object) with fields for description, sample type, LOINC, and bounding boxes.
- **Execution Timer**: Added a timer in the UI to display the elapsed time for the extraction process.
- **Transparent Bounding Boxes**: Implemented transparent filled rectangles and semi-transparent borders for better visibility of underlying text.
- **Custom Colors**: Set bounding box color for tests to **Yellow**.

### Changed
- **Client Refactor**: Replaced LangChain `ChatOpenAI` with pure `openai` library to resolve timeout issues and enable manual streaming.
- **Validation**: Implemented Pydantic models (`ExtractionResult`, `Test`, `UrineDetails`) for strict validation of the final JSON response.
- **Prompt Update**: Updated `prompts/vision_extraction.md` to enforce JSON mode and inject the schema dynamically.
- **Bounding Box Logic**: Updated `utils.py` to automatically sort coordinates (min/max) and expand boxes by 2 pixels to prevent errors and improve visibility.

## [0.6.2] - 2025-12-01

### Changed
- **API Client**: Increased Requesty API timeout to 600 seconds.
- **Streaming**: Enabled streaming response and terminal logging.

## [0.6.0] - 2025-11-28

### Added
- **Date of Birth Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the patient's date of birth (`FechaNacimiento`) normalized to `dd/mm/yyyy`.
- **Sex Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the patient's sex (`Sexo`) normalized to `H`/`M`/`U`.
- **UI Visualization**: Implemented custom colors for bounding boxes: Red for patient data, Blue for petition numbers, Green for others.
- **Prompt Engineering**: Added strict anti-hallucination instructions to `prompts/vision_extraction.md`.
- **Patient ID Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the patient's ID (`DocumentoIdentidad`) and visualized it in red.
- **Patient Phone Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the patient's phone number (`Telefono`) and visualized it in red.
- **Doctor Name Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the doctor's name (`NombreMedico`) and visualized it in purple.
- **Collegiate Number Extraction**: Updated `prompts/vision_extraction.md` to include extraction of the collegiate number (`NumeroColegiado`) and visualized it in purple.

## [0.5.2] - 2025-11-27

### Added
- **Editable System Prompt**: Added a collapsible section in the UI to edit the system prompt at runtime before extraction.
- **Unique Petition Numbers**: Updated the system prompt to explicitly instruct the model to extract unique petition numbers only.

### Changed
- **Sidebar**: Configured the sidebar to be collapsed by default to maximize screen space.
- **UI Layout**: Moved the System Prompt editor above the file uploader and increased its height for better visibility.
- **Deprecation Fix**: Replaced `use_container_width=True` with `width="stretch"` in Streamlit image display to resolve warning.

## [0.5.1] - 2025-11-27

### Added
- Integrated **LangSmith** for tracing and monitoring LLM calls.
- Added "Petition Number" field to vision extraction prompt.
- Added `test_extraction.py` script for isolated testing.

### Changed
- Refactored `prompts/vision_extraction.md` to be more structured and extensible.
- Increased LLM client timeout to 300s and disabled retries to prevent connection errors on large documents.
- Refactored `app.py` to group extracted bounding boxes by page, displaying each page only once.
- Replaced deprecated `use_column_width` with `use_container_width` in Streamlit image display.

## [0.5.0] - 2025-11-27

### Added
- Implemented secure authentication using `streamlit-authenticator`.
- Added `auth_utils.py` for handling authentication logic and password hashing.
- Added `Dockerfile` optimized for Dokploy deployment with `poppler-utils` support.
- Added `streamlit-authenticator` to `requirements.txt`.

### Changed
- Updated `app.py` to enforce login before accessing the application.
- Configured application to use environment variables (`ADMIN_USER`, `ADMIN_PASSWORD`, `AUTH_SECRET`) for credentials.

## [0.4.1] - 2025-11-26

### Changed
- Updated extraction workflow to send all page images in a single request (instead of direct PDF) to ensure compatibility while providing full document context.
- Updated `ExtractionResult` schema to include `page_number` for each extracted element.
- Updated `app.py` to visualize bounding boxes using the returned `page_number`.

## [0.4.0] - 2025-11-26

### Changed
- Removed "Mistral OCR + Requesty" workflow to simplify the application.
- Removed workflow selection from the Streamlit sidebar; now defaults to "Requesty Vision (Direct)".
- Updated `app.py` to fix `use_container_width` deprecation warning by using `width="stretch"`.

## [0.3.1] - 2025-11-25

### Added
- Implemented visualization of extracted bounding boxes on the document images in the application UI.
- Added debug logging for bounding box coordinates.

### Changed
- Updated vision extraction prompt to enforce normalized coordinates (0-1000) for better accuracy.

### Fixed
- Fixed Streamlit deprecation warning by replacing `use_column_width` with `use_container_width`.

## [0.3.0] - 2025-11-25

### Changed
- Updated extraction prompts to specifically extract only the patient's name and surname.
- Implemented structured data extraction using JSON schema to support bounding boxes and strict output formatting.
- Updated the application UI to display structured extraction results (Label, Value, Bounding Box).

## [0.2.1] - 2025-11-25

### Changed
- Extracted system prompts from `workflows.py` to external Markdown files in the `prompts/` directory for easier modification.

## [0.2.0] - 2025-11-25

### Added
- Execution logging in terminal with color coding for better visibility of workflow progress.

### Changed
- Default extraction workflow is now "Requesty Vision (Direct)".
- Default model is now "vertex/gemini-3-pro-preview".

## [0.1.0] - 2025-11-25

### Added
- Initial project structure.
- Streamlit application (`app.py`) for clinical PDF extraction.
- LangGraph workflows (`workflows.py`) for OCR and Vision extraction.
- Utility functions (`utils.py`) for PDF to image conversion.
- Project documentation (`README.md`).
- Git configuration (`.gitignore`).
