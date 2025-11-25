# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
