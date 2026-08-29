"""
FastAPI app: one endpoint that verifies a label image against application data.

Flow: decode image -> one Gemini vision call (fuzzy match on the 4 fields +
verbatim warning transcription) -> deterministic warning validator -> assemble
a per-field VerificationResponse.
"""
import base64
import binascii
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app import warning_check
from app.config import FUZZY_FIELDS, VISION_MODEL
from app.models import FieldResult, VerificationResponse, VerifyRequest
from app.vision import VisionError, extract_and_match

app = FastAPI(title="TTB Alcohol Label Verification")

_PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def _decode_image(image_b64: str) -> tuple[bytes, str]:
    # Accept a raw base64 string or a full "data:image/png;base64,..." URL.
    if image_b64.startswith("data:"):
        image_b64 = image_b64.split(",", 1)[-1]
    try:
        data = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"invalid base64 image: {e}") from e
    if not data:
        raise HTTPException(status_code=422, detail="empty image")
    if data[:8].startswith(b"\x89PNG"):
        mime = "image/png"
    elif data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return data, mime


@app.post("/api/verify", response_model=VerificationResponse)
def verify(req: VerifyRequest) -> VerificationResponse:
    started = time.perf_counter()
    image_bytes, mime = _decode_image(req.image_b64)

    try:
        vision = extract_and_match(image_bytes, mime, req.application)
    except VisionError as e:
        raise HTTPException(status_code=502, detail=f"vision service error: {e}") from e

    fields: list[FieldResult] = []
    for name in FUZZY_FIELDS:
        obs = getattr(vision, name)
        fields.append(
            FieldResult(
                field=name,
                application_value=getattr(req.application, name),
                label_value=obs.label_value,
                match=obs.match,
                reason=obs.reason,
            )
        )

    warning = warning_check.validate(vision.government_warning)

    notes: list[str] = []
    if vision.image_quality.issues:
        notes.append(vision.image_quality.issues)

    if not vision.image_quality.readable:
        overall = "NEEDS_REVIEW"
    elif warning.match and all(f.match for f in fields):
        overall = "PASS"
    else:
        overall = "FAIL"

    return VerificationResponse(
        overall=overall,
        fields=fields,
        government_warning=warning,
        elapsed_seconds=round(time.perf_counter() - started, 2),
        model=VISION_MODEL,
        notes=notes,
    )


@app.get("/health")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_PUBLIC_DIR / "index.html")
