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
    alpha: int = 100,  # Transparency level (0-255)
) -> Image.Image:
    """
    Draws a bounding box on the image with a transparent fill.
    Assumes bbox is [ymin, xmin, ymax, xmax].
    If values are <= 1000, assumes they are normalized 0-1000 and scales them.
    """
    if not bbox or len(bbox) != 4:
        return image

    # Ensure image is RGBA for transparency
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Create a transparent overlay
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

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

    # Ensure coordinates are ordered correctly to avoid "x1 must be greater than or equal to x0"
    left = min(xmin, xmax) - 2
    right = max(xmin, xmax) + 2
    top = min(ymin, ymax) - 2
    bottom = max(ymin, ymax) + 2

    # Color mapping for common names to RGB
    COLORS = {
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "purple": (128, 0, 128),
        "orange": (255, 165, 0),
        "gold": (255, 215, 0),
    }

    rgb = COLORS.get(color.lower(), (255, 0, 0))  # Default to red
    fill_color = rgb + (alpha,)
    outline_color = rgb + (80,)  # More transparent outline

    # Draw filled rectangle on overlay
    draw.rectangle(
        [left, top, right, bottom], fill=fill_color, outline=outline_color, width=width
    )

    # Composite overlay with original image
    image = Image.alpha_composite(image, overlay)

    # Draw label on top (solid)
    if label:
        draw_label = ImageDraw.Draw(image)
        text_bbox = draw_label.textbbox((left, top), label)
        draw_label.rectangle(text_bbox, fill=outline_color)
        draw_label.text((left, top), label, fill="white")

    return image
