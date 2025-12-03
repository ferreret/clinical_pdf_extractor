from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    vertexai=True,
    project="echevarne-479918",
    location="global",
)
# If your image is stored in Google Cloud Storage, you can use the from_uri class method to create a Part object.
IMAGE_URI = "gs://generativeai-downloads/images/scones.jpg"
model = "gemini-3-pro-preview"
response = client.models.generate_content(
    model=model,
    contents=[
        "What is shown in this image?",
        types.Part.from_uri(
            file_uri=IMAGE_URI,
            mime_type="image/png",
        ),
    ],
)
print(response.text, end="")
