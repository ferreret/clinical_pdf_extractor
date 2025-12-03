import os
from workflows import app_google_genai
from dotenv import load_dotenv

load_dotenv()


def verify_workflow():
    pdf_path = "/media/nicolas/DATA/Tecnomedia/Echevarne/2025.11.24 Muestras IA/Muestras/04/Documento 001.pdf"

    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return

    print(f"Reading PDF from {pdf_path}...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    initial_state = {
        "pdf_bytes": pdf_bytes,
        "images": [],
        "extracted_data": [],
        "errors": [],
        "model_name": "gemini-3-pro-preview",
        "system_prompt": "Extract the clinical data from this document.",
    }

    print("Invoking Google GenAI workflow...")
    try:
        result = app_google_genai.invoke(initial_state)

        if result.get("errors"):
            print("Errors found:")
            for error in result["errors"]:
                print(f"- {error}")
        else:
            print("Extraction successful!")
            images = result.get("images", [])
            print(f"Images in state: {len(images)}")
            data = result.get("extracted_data", [])
            for item in data:
                print(f"Source: {item['source']}")
                if "usage" in item:
                    usage = item["usage"]
                    print(f"Usage: {usage}")
                    print(f"Estimated Cost: ${usage.get('estimated_cost_usd', 0):.6f}")
                print(f"Content: {item['content']}")

    except Exception as e:
        print(f"Workflow execution failed: {e}")


if __name__ == "__main__":
    verify_workflow()
