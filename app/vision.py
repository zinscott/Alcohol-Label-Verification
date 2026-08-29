import textwrap
from google import genai
from google.genai import types
from pydantic import BaseModel
from app.config import GEMINI_API_KEY,VISION_MODEL
from app.models import ApplicationData

client = genai.Client(api_key=GEMINI_API_KEY)

class FieldObs(BaseModel):
    label_value: str | None
    match: bool
    reason: str

class WarningObs(BaseModel):
    found: bool
    verbatim_text: str | None
    prefix_is_all_caps: bool
    prefix_is_bold: bool
    is_separate_paragraph: bool

class ImageQuality(BaseModel):
    readable: bool
    issues: str | None

class VisionResult(BaseModel):
    brand_name: FieldObs
    class_type: FieldObs
    alcohol_content: FieldObs
    net_contents: FieldObs
    government_warning: WarningObs
    image_quality: ImageQuality

def build_prompt(application: ApplicationData) -> str:
    return textwrap.dedent(
        f"""\
        You are helping a TTB agent verify an alcohol label against its application.

        The application says:
        - Brand name: {application.brand_name}
        - Class/type designation: {application.class_type}
        - Alcohol content: {application.alcohol_content}
        - Net contents: {application.net_contents}

        Look at the label image and return JSON matching the provided schema.

        For brand_name, class_type, alcohol_content, and net_contents:
        - label_value: the value exactly as printed on the label, or null if not visible.
        - match: true if the label value refers to the SAME thing as the application value,
          ignoring differences in capitalization, punctuation, spacing, word order, and
          formatting. Examples that are matches: "STONE'S THROW" vs "Stone's Throw";
          "40% ALC/VOL" vs "40"; "750 ML" vs "750 mL". Set match false only for a real
          substantive difference (different name, different number, different class of product).
        - reason: one short sentence explaining the decision, for a reviewer to read.

        For government_warning, only OBSERVE — do not judge whether it is correct:
        - found: whether a government warning statement appears on the label.
        - verbatim_text: transcribe the warning EXACTLY as printed, character for character,
          including the "GOVERNMENT WARNING:" prefix, all punctuation, and the (1) and (2)
          markers. Do not fix spelling, spacing, or wording. null if not found.
        - prefix_is_all_caps: whether the literal words "GOVERNMENT WARNING:" are in all capitals.
        - prefix_is_bold: whether those same words are visually bolder (heavier weight) than
          the sentence text that follows them.
        - is_separate_paragraph: whether the warning is its own distinct block of text, not
          run together with other label copy.

        For image_quality:
        - readable: false if glare, blur, angle, or resolution makes any required field a guess.
        - issues: brief description of the problem, or null.
        """
    )

class VisionError(Exception):
    """Hard failure talking to the vision model (network, quota, unparseable)."""


def extract_and_match(image_bytes: bytes, mime_type: str, application: ApplicationData) -> VisionResult:
    if not GEMINI_API_KEY:
        raise VisionError("GEMINI_API_KEY is not set")

    try:
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                build_prompt(application),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VisionResult,
                temperature=0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except Exception as e:
        raise VisionError(f"vision API call failed: {e}") from e

    result = response.parsed
    if result is None:
        raise VisionError("vision model returned no parseable result")
    return result


if __name__ == "__main__":
    import sys

    path = sys.argv[1]  # python -m app.vision sample_data/good.png
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    demo_app = ApplicationData(
        brand_name="Stone's Throw",
        class_type="Kentucky Straight Bourbon Whiskey",
        alcohol_content="40% ALC/VOL",
        net_contents="750 mL",
    )
    with open(path, "rb") as f:
        out = extract_and_match(f.read(), mime, demo_app)
    print(out.model_dump_json(indent=2))