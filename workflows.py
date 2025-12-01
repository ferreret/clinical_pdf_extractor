import json
import os
from typing import Any, Dict, List, Optional, TypedDict
import base64

import openai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
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

        # Initialize OpenAI client directly
        client = openai.OpenAI(
            api_key=REQUESTY_API_KEY,
            base_url=REQUESTY_BASE_URL,
            timeout=600.0,
            max_retries=0,
        )

        # Define Pydantic models for extraction
        class Element(BaseModel):
            label: str = Field(
                description="The label of the extracted element, e.g., 'NombreApellidos'"
            )
            value: str = Field(description="The extracted value")
            page_number: int = Field(
                description="The page number where this element was found (1-indexed)."
            )
            bounding_box: Optional[List[int]] = Field(
                description="The bounding box [ymin, xmin, ymax, xmax] or null"
            )

        class Test(BaseModel):
            description: str = Field(description="Name or description of the test")
            sample_type: Optional[str] = Field(
                description="Type of sample (e.g., Suero, Orina, Sangre total)"
            )
            loinc_code: Optional[str] = Field(
                description="Proposed LOINC code based on context"
            )
            page_number: int = Field(
                description="The page number where this element was found (1-indexed)."
            )
            bounding_box: Optional[List[int]] = Field(
                description="The bounding box [ymin, xmin, ymax, xmax] or null"
            )

        class UrineDetails(BaseModel):
            collection_type: str = Field(
                description="Type of urine collection", enum=["24h", "Spot", "Random"]
            )
            volume: Optional[str] = Field(
                description="Total volume if specified (e.g., 1500 ml)"
            )
            page_number: int = Field(
                description="The page number where this element was found (1-indexed)."
            )
            bounding_box: Optional[List[int]] = Field(
                description="The bounding box [ymin, xmin, ymax, xmax] or null"
            )

        class ExtractionResult(BaseModel):
            elements: List[Element] = Field(
                description="List of general extracted elements"
            )
            tests: List[Test] = Field(description="List of clinical tests")
            urine_details: Optional[UrineDetails] = Field(
                description="Details about urine sample if present"
            )

        # Prepare messages
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

        # Append schema instructions
        # We manually create a schema description since we are not using JsonOutputParser anymore
        schema_json = ExtractionResult.model_json_schema()
        system_prompt_content += f"\n\n# JSON Schema\nRespond strictly with a JSON object satisfying this schema:\n{json.dumps(schema_json, indent=2)}"

        messages = [
            {"role": "system", "content": system_prompt_content},
            {"role": "user", "content": messages_content},
        ]

        # Call API with streaming
        print(f"{CYAN}[INFO] Sending request to Requesty (timeout=600s)...{RESET}")
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            response_format={"type": "json_object"},
            temperature=0,
        )

        # Consume stream
        full_response = ""
        print(f"{GREEN}[STREAM] Receiving response:{RESET}")
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
                full_response += content
        print()  # Newline after stream

        # Parse and Validate
        try:
            extracted_data = ExtractionResult.model_validate_json(full_response)
            extracted_dict = extracted_data.model_dump()
        except Exception as parse_error:
            print(f"{RED}[ERROR] JSON Parsing failed: {parse_error}{RESET}")
            # Attempt to recover partial JSON or return raw error
            return {
                "errors": state["errors"] + [f"JSON Parsing Error: {str(parse_error)}"]
            }

        # We now have a single extraction result for the whole document
        new_data = [
            {
                "page": "All",
                "content": extracted_dict,
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
