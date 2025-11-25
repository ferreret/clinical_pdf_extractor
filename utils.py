import base64
import io
from typing import List

from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image, ImageDraw

# --- Logging Colors ---
YELLOW = "\033[93m"
RESET = "\033[0m"


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
    base64_str = encode_image_to_base64(image)
    return f"data:image/jpeg;base64,{base64_str}"


def draw_bounding_box(
    image: Image.Image,
    bbox: List[int],
    label: str = None,
    color: str = "red",
    width: int = 3,
) -> Image.Image:
    """
    Draws a bounding box on the image.
    Assumes bbox is [ymin, xmin, ymax, xmax].
    If values are <= 1000, assumes they are normalized 0-1000 and scales them.
    """
    if not bbox or len(bbox) != 4:
        return image

    draw = ImageDraw.Draw(image)
    width_px, height_px = image.size
    ymin, xmin, ymax, xmax = bbox
    print(
        f"{YELLOW}[DEBUG] Drawing bbox: {bbox} (Image size: {width_px}x{height_px}){RESET}"
    )

    # Check for normalization (0-1000)
    if all(val <= 1000 for val in bbox):
        ymin = int(ymin / 1000 * height_px)
        xmin = int(xmin / 1000 * width_px)
        ymax = int(ymax / 1000 * height_px)
        xmax = int(xmax / 1000 * width_px)

    draw.rectangle([xmin, ymin, xmax, ymax], outline=color, width=width)

    if label:
        # Draw label background
        text_bbox = draw.textbbox((xmin, ymin), label)
        draw.rectangle(text_bbox, fill=color)
        draw.text((xmin, ymin), label, fill="white")

    return image
