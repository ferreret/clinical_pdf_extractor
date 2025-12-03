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
import google.generativeai as genai
import time
import tempfile


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
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


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
        model = state.get("model_name", "google/gemini-3-pro-preview")

        # Initialize OpenAI client directly
        client = openai.OpenAI(
            api_key=REQUESTY_API_KEY,
            base_url=REQUESTY_BASE_URL,
            timeout=1200.0,
            max_retries=3,
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

        # --- Single Request: All Data ---
        print(f"{CYAN}[STEP] Extracting All Data (General + Tests)...{RESET}")

        system_prompt = load_prompt("vision_extraction.md")
        # Append schema instructions
        schema_json = ExtractionResult.model_json_schema()
        system_prompt += f"\n\n# JSON Schema\nRespond strictly with a JSON object satisfying this schema:\n{json.dumps(schema_json, indent=2)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": messages_content
                + [
                    {
                        "type": "text",
                        "text": "Extract all clinical data (elements, tests, urine_details) from the document.",
                    }
                ],
            },
        ]

        print(f"{CYAN}[INFO] Sending request to Requesty (timeout=1200s)...{RESET}")
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0,
        )

        full_response = ""
        print(f"{GREEN}[STREAM] Receiving response:{RESET}")
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
                full_response += content
        print()

        # Parse
        try:
            # Helper to parse JSON from potential markdown
            def parse_json(text):
                clean = text.replace("```json", "").replace("```", "").strip()
                start = clean.find("{")
                end = clean.rfind("}") + 1
                if start != -1 and end != -1:
                    return ExtractionResult.model_validate_json(clean[start:end])
                raise ValueError("Could not find JSON object")

            extracted_result = parse_json(full_response)
            extracted_dict = extracted_result.model_dump()

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
                "source": "Requesty Vision (All Images) - Single Request",
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


def node_google_genai_extraction(state: AgentState):
    """
    Uses Google GenAI SDK directly to extract data from the PDF.
    """
    try:
        print(f"{CYAN}[STEP] Extracting data using Google GenAI...{RESET}")

        # 1. Save PDF to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(state["pdf_bytes"])
            tmp_pdf_path = tmp_pdf.name

        try:
            # 2. Upload file
            print(f"{BLUE}[INFO] Uploading PDF to Gemini...{RESET}")
            uploaded_file = genai.upload_file(
                path=tmp_pdf_path, mime_type="application/pdf"
            )
            print(f"{GREEN}[SUCCESS] Uploaded. URI: {uploaded_file.uri}{RESET}")

            # 3. Wait for processing
            while uploaded_file.state.name == "PROCESSING":
                print("Processing file...")
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                raise ValueError("File processing failed.")

            print(f"{GREEN}[INFO] File active. Generating content...{RESET}")

            # 4. Generate Content - Split into two requests
            model_name = state.get("model_name", "gemini-3-pro-preview")
            model = genai.GenerativeModel(model_name=model_name)

            # Prepare prompt base
            # We ignore state system prompt for now to enforce the split prompts, or we could check if it's overriden.
            # For optimization, we use the specific files.

            from google.api_core import retry

            # --- Single Request: All Data ---
            print(f"{CYAN}[STEP] Extracting All Data (General + Tests)...{RESET}")

            system_prompt = load_prompt("vision_extraction.md")
            prompt = f"{system_prompt}\n\nPlease analyze the attached PDF and extract all clinical data (elements, tests, urine_details). Respond in JSON format."

            response_stream = model.generate_content(
                [prompt, uploaded_file],
                stream=True,
                request_options={
                    "timeout": 600,
                    "retry": retry.Retry(
                        predicate=retry.if_transient_error, timeout=600
                    ),
                },
            )

            full_text = ""
            input_tokens = 0
            output_tokens = 0

            print(f"{GREEN}[STREAM] Receiving response:{RESET}")
            for chunk in response_stream:
                try:
                    text = chunk.text
                    print(text, end="", flush=True)
                    full_text += text
                except Exception:
                    pass

                if chunk.usage_metadata:
                    input_tokens = chunk.usage_metadata.prompt_token_count
                    output_tokens = chunk.usage_metadata.candidates_token_count

            print()
            print(f"{GREEN}[SUCCESS] Response received.{RESET}")

            # Calculate Cost (Gemini 1.5 Pro Pricing as proxy)
            # Input: $1.25 / 1M tokens
            # Output: $5.00 / 1M tokens
            input_cost = (input_tokens / 1_000_000) * 1.25
            output_cost = (output_tokens / 1_000_000) * 5.00
            total_cost = input_cost + output_cost

            print(
                f"{CYAN}[COST] Input Tokens: {input_tokens}, Output Tokens: {output_tokens}{RESET}"
            )
            print(f"{CYAN}[COST] Estimated Cost: ${total_cost:.6f}{RESET}")

            # 5. Parse JSON
            def parse_json_response(text):
                clean = text.replace("```json", "").replace("```", "").strip()
                start = clean.find("{")
                end = clean.rfind("}") + 1
                if start != -1 and end != -1:
                    return json.loads(clean[start:end])
                raise ValueError("Could not find JSON object")

            try:
                extracted_data = parse_json_response(full_text)

            except Exception as parse_error:
                print(f"{RED}[ERROR] JSON Parsing failed: {parse_error}{RESET}")
                extracted_data = {"elements": [], "tests": [], "urine_details": None}

            new_data = [
                {
                    "page": "All",
                    "content": extracted_data,
                    "source": f"Google GenAI ({model_name}) - Single Request",
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "estimated_cost_usd": total_cost,
                    },
                }
            ]

            return {"extracted_data": new_data}

        finally:
            # Cleanup temporary file
            if os.path.exists(tmp_pdf_path):
                os.remove(tmp_pdf_path)

            # Cleanup GenAI files as requested
            print(f"{YELLOW}[CLEANUP] Cleaning up GenAI files...{RESET}")
            try:
                for archivo in genai.list_files():
                    print(f"Deleting residual file: {archivo.name}")
                    genai.delete_file(archivo.name)
            except Exception as cleanup_error:
                print(
                    f"{RED}[WARN] Failed to cleanup GenAI files: {cleanup_error}{RESET}"
                )

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"{RED}[ERROR] Google GenAI Extraction Error: {str(e)}{RESET}")
        return {"errors": state["errors"] + [f"Google GenAI Error: {str(e)}"]}


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

# Workflow 3: Google GenAI Direct
workflow_genai = StateGraph(AgentState)
workflow_genai.add_node("convert_pdf", node_convert_pdf_to_images)
workflow_genai.add_node("genai_extract", node_google_genai_extraction)

workflow_genai.set_entry_point("convert_pdf")
workflow_genai.add_edge("convert_pdf", "genai_extract")
workflow_genai.add_edge("genai_extract", END)

app_google_genai = workflow_genai.compile()
