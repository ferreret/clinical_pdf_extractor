import base64
import io
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image

def pdf_to_images(pdf_path: str = None, pdf_bytes: bytes = None):
    """
    Convert a PDF to a list of PIL Images.
    Accepts either a file path or bytes.
    """
    if pdf_path:
        return convert_from_path(pdf_path)
    elif pdf_bytes:
        return convert_from_bytes(pdf_bytes)
    else:
        raise ValueError("Either pdf_path or pdf_bytes must be provided")

def encode_image_to_base64(image: Image.Image) -> str:
    """
    Convert a PIL Image to a base64 string.
    """
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def get_image_data_url(image: Image.Image) -> str:
    """
    Get the data URL for an image (e.g., for passing to an LLM).
    """
    base64_str = encode_image_to_base64(image)
    return f"data:image/jpeg;base64,{base64_str}"
