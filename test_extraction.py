import os
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import utils

# Load env
load_dotenv()

REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")
REQUESTY_BASE_URL = os.getenv("REQUESTY_BASE_URL", "https://router.requesty.ai/v1")

# Define Schema
schema = {
    "name": "ExtractionResult",
    "description": "Extraction result containing elements",
    "parameters": {
        "type": "object",
        "properties": {
            "elements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "The label of the extracted element, e.g., 'NombreApellidos'",
                        },
                        "value": {
                            "type": "string",
                            "description": "The extracted value",
                        },
                        "page_number": {
                            "type": "integer",
                            "description": "The page number where this element was found (1-indexed).",
                        },
                        "bounding_box": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "The bounding box [ymin, xmin, ymax, xmax] or null",
                        },
                    },
                    "required": ["label", "value", "page_number"],
                },
            }
        },
        "required": ["elements"],
    },
}


def load_prompt(filename: str) -> str:
    """Loads a prompt from the prompts directory."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "prompts", filename)
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Failed to load prompt {filename}: {str(e)}")
        return ""


def test_extraction():
    print("Starting test extraction...")

    # Initialize LLM
    llm = ChatOpenAI(
        api_key=REQUESTY_API_KEY,
        base_url=REQUESTY_BASE_URL,
        model="vertex/gemini-3-pro-preview",
        temperature=0,
        timeout=300,
        max_retries=0,
    )

    structured_llm = llm.with_structured_output(schema)

    # Load Prompt
    system_prompt = load_prompt("vision_extraction.md")
    print(f"Loaded system prompt ({len(system_prompt)} chars).")

    # Mock Image (You might need to point to a real PDF or image if available,
    # but for now let's try to use the PDF conversion if we can access a file,
    # or just send a text message if we can't easily load the PDF here.
    # Actually, the user has 'utils.py' and likely a PDF in the workspace?)

    # Let's try to find a PDF in the directory to use.
    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("No PDF found in current directory to test.")
        return

    target_pdf = pdf_files[0]
    print(f"Using PDF: {target_pdf}")

    with open(target_pdf, "rb") as f:
        pdf_bytes = f.read()

    print("Converting PDF to images...")
    images = utils.pdf_to_images(pdf_bytes=pdf_bytes)
    print(f"Converted to {len(images)} images.")

    messages_content = [
        {
            "type": "text",
            "text": "Extract the clinical data from this document. The document is provided as a series of images.",
        }
    ]

    for image in images:
        image_url = utils.get_image_data_url(image)
        messages_content.append({"type": "image_url", "image_url": {"url": image_url}})

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=messages_content),
    ]

    print("Sending request to LLM...")
    start_time = time.time()
    try:
        response = structured_llm.invoke(messages)
        end_time = time.time()
        print(f"Success! Time taken: {end_time - start_time:.2f}s")
        print(response)
    except Exception as e:
        end_time = time.time()
        print(f"Failed after {end_time - start_time:.2f}s")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_extraction()
