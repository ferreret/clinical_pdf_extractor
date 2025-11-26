import json
import os
from typing import Any, Dict, List, Optional, TypedDict

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
    current_page_index: int
    extracted_data: List[Dict[str, Any]]
    errors: List[str]
    model_name: str  # Added model name to state


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
    Uses Requesty (OpenAI compatible) with a Vision model to extract data directly from images.
    """
    try:
        idx = state["current_page_index"]
        if idx >= len(state["images"]):
            return {}

        image = state["images"][idx]
        image_url = utils.get_image_data_url(image)

        print(
            f"{CYAN}[STEP] Extracting data from image for page {idx + 1} using Vision...{RESET}"
        )

        # Use model from state or default
        model = state.get("model_name", "gpt-4o")

        llm = ChatOpenAI(
            api_key=REQUESTY_API_KEY,
            base_url=REQUESTY_BASE_URL,
            model=model,  # Assuming Requesty has a vision capable model
            temperature=0,
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
                                "bounding_box": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "The bounding box [ymin, xmin, ymax, xmax] or null",
                                },
                            },
                            "required": ["label", "value"],
                        },
                    }
                },
                "required": ["elements"],
            },
        }

        structured_llm = llm.with_structured_output(schema)

        messages = [
            SystemMessage(content=load_prompt("vision_extraction.md")),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Extract the clinical data from this document.",
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            ),
        ]

        response = structured_llm.invoke(messages)
        extracted = response  # Response is already a dict when using schema dict

        new_data = state["extracted_data"] + [
            {"page": idx + 1, "content": extracted, "source": "Requesty Vision"}
        ]

        print(
            f"{GREEN}[SUCCESS] Vision extraction completed for page {idx + 1}.{RESET}"
        )
        return {"extracted_data": new_data, "current_page_index": idx + 1}

    except Exception as e:
        print(f"{RED}[ERROR] Vision Extraction Error: {str(e)}{RESET}")
        return {
            "errors": state["errors"] + [f"Vision Extraction Error: {str(e)}"],
            "current_page_index": state["current_page_index"] + 1,
        }


def condition_check_done(state: AgentState):
    if state["current_page_index"] < len(state["images"]):
        return "continue"
    return "end"


# --- Workflow Construction ---

# Workflow 1: OCR -> Extraction


# Workflow 2: Direct Vision
workflow_vision = StateGraph(AgentState)
workflow_vision.add_node("convert_pdf", node_convert_pdf_to_images)
workflow_vision.add_node("vision_extract", node_requesty_vision_extraction)

workflow_vision.set_entry_point("convert_pdf")
workflow_vision.add_edge("convert_pdf", "vision_extract")

workflow_vision.add_conditional_edges(
    "vision_extract", condition_check_done, {"continue": "vision_extract", "end": END}
)

# Compile

app_vision = workflow_vision.compile()
