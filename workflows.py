import json
import os
from typing import Any, Dict, List, Optional, TypedDict
import base64

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph import END, StateGraph

import utils


load_dotenv()

# --- Logging Colors ---
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# --- Configuration ---
# --- Configuration ---
REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")
REQUESTY_BASE_URL = os.getenv("REQUESTY_BASE_URL", "https://router.requesty.ai/v1")


# --- State Definition ---
class AgentState(TypedDict):
    pdf_bytes: bytes
    images: List[Any]  # PIL Images
    extracted_data: List[Dict[str, Any]]
    errors: List[str]
    model_name: str  # Added model name to state
    system_prompt: Optional[str]  # Added system prompt to state


# --- Node Definitions ---


def load_prompt(filename: str) -> str:
    """Loads a prompt from the prompts directory."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "prompts", filename)
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"{RED}[ERROR] Failed to load prompt {filename}: {str(e)}{RESET}")
        return ""


def node_convert_pdf_to_images(state: AgentState):
    """Converts PDF bytes to images."""
    try:
        print(f"{BLUE}[INFO] Converting PDF to images...{RESET}")
        images = utils.pdf_to_images(pdf_bytes=state["pdf_bytes"])
        print(f"{GREEN}[SUCCESS] Converted PDF to {len(images)} images.{RESET}")
        return {
            "images": images,
            "current_page_index": 0,
            "extracted_data": [],
            "errors": [],
        }
    except Exception as e:
        print(f"{RED}[ERROR] PDF Conversion Error: {str(e)}{RESET}")
        return {"errors": [f"PDF Conversion Error: {str(e)}"]}


def node_requesty_vision_extraction(state: AgentState):
    """
    Uses Requesty (OpenAI compatible) with a Vision model to extract data directly from images (all at once).
    """
    try:
        if not state["images"]:
            print(f"{YELLOW}[WARN] No images found in state.{RESET}")
            return {}

        print(
            f"{CYAN}[STEP] Extracting data from {len(state['images'])} images using Vision...{RESET}"
        )

        # Use model from state or default
        model = state.get("model_name", "gpt-4o")

        llm = ChatOpenAI(
            api_key=REQUESTY_API_KEY,
            base_url=REQUESTY_BASE_URL,
            model=model,
            temperature=0,
            timeout=300,
            max_retries=0,
        )

        # Define schema manually to avoid $defs
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

        structured_llm = llm.with_structured_output(schema)

        messages_content = [
            {
                "type": "text",
                "text": "Extract the clinical data from this document. The document is provided as a series of images.",
            }
        ]

        for image in state["images"]:
            image_url = utils.get_image_data_url(image)
            messages_content.append(
                {"type": "image_url", "image_url": {"url": image_url}}
            )

        # Use system prompt from state or load default
        system_prompt_content = state.get("system_prompt")
        if not system_prompt_content:
            system_prompt_content = load_prompt("vision_extraction.md")

        messages = [
            SystemMessage(content=system_prompt_content),
            HumanMessage(content=messages_content),
        ]

        response = structured_llm.invoke(messages)
        extracted = response  # Response is already a dict when using schema dict

        # We now have a single extraction result for the whole document
        new_data = [
            {
                "page": "All",
                "content": extracted,
                "source": "Requesty Vision (All Images)",
            }
        ]

        print(f"{GREEN}[SUCCESS] Vision extraction completed for all images.{RESET}")
        return {"extracted_data": new_data}

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(
            f"{RED}[ERROR] Vision Extraction Error: {type(e).__name__}: {str(e)}{RESET}"
        )
        return {
            "errors": state["errors"] + [f"Vision Extraction Error: {str(e)}"],
        }


# --- Workflow Construction ---

# Workflow 1: OCR -> Extraction


# Workflow 2: Direct Vision
workflow_vision = StateGraph(AgentState)
workflow_vision.add_node("convert_pdf", node_convert_pdf_to_images)
workflow_vision.add_node("vision_extract", node_requesty_vision_extraction)

workflow_vision.set_entry_point("convert_pdf")
workflow_vision.add_edge("convert_pdf", "vision_extract")

workflow_vision.add_edge("vision_extract", END)

# Compile

app_vision = workflow_vision.compile()
