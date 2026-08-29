"""
Request/response schemas — the contract between the backend and the frontend.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ApplicationData(BaseModel):
    #Fields the agent types in from the COLA application.

    brand_name: str
    class_type: str
    alcohol_content: str
    net_contents: str


class VerifyRequest(BaseModel):
    #Base64 because we're sending JSON, and JSON can't carry raw binary.
    #The frontend converts the image after it downscales it.
    image_b64: str = Field(..., description="Base64-encoded label image (no data: prefix)")
    application: ApplicationData


class FieldResult(BaseModel):
    field: str
    application_value: str
    label_value: Optional[str] = None
    match: bool
    reason: str


class WarningResult(BaseModel):
    field: Literal["government_warning"] = "government_warning"
    match: bool
    reason: str
    label_text: Optional[str] = None
    checks: dict[str, bool] = Field(
        default_factory=dict,
        description="e.g. {'exact_wording': True, 'prefix_all_caps': True, 'prefix_bold': False}",
    )


class VerificationResponse(BaseModel):
    overall: Literal["PASS", "FAIL", "NEEDS_REVIEW"]
    fields: list[FieldResult]
    government_warning: WarningResult
    elapsed_seconds: float
    model: str
    notes: list[str] = Field(default_factory=list)
