"""
Shared Pydantic schemas — single source of truth for all routes.
P1 (frontend), P2 (backend/text), P3 (image/deepfake) must all reference these.
"""

from pydantic import BaseModel, Field
from typing import List, Literal


# ── Requests ──────────────────────────────────────────────────────────────────

class TextInput(BaseModel):
    text: str


# ── Shared response (used by /check-text, /check-image, /check-deepfake) ──────

class ScamAnalysisResult(BaseModel):
    danger_score: int = Field(..., ge=0, le=100, description="0 = safe, 100 = definite scam")
    type: Literal["scam", "safe"]
    scam_category: Literal[
        "credit_card", "kyc", "crypto", "lottery", "job_fraud", "safe"
    ]
    red_flags: List[str]
    explanation: str = Field(..., description="1-2 lines in simple language")
    precautions: List[str]
    block_recommended: bool
    report_to: str = "cybercrime.gov.in"


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
