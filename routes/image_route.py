# image_route.py
# P3's route — plugs into P2's main FastAPI app via APIRouter.
#
# DEPENDS ON P2:
#   - from services.gemini_service import analyze_text
#     P2 must expose this function: analyze_text(text: str) -> dict
#     It should return the same JSON shape used by /check-text so the
#     frontend result card renders identically for image submissions.
#
# SYSTEM DEPENDENCY (tell P2 before deploy):
#   Tesseract binary must be installed on the server.
#   Local  : brew install tesseract  /  sudo apt-get install tesseract-ocr
#   Render : add the binary install step to the build script, or switch to
#            a Dockerfile that runs `apt-get install -y tesseract-ocr`.

import io
import logging

import pytesseract
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

# ── Import P2's shared Claude helper ────────────────────────────────────────
# TODO (P3 → P2): confirm the import path once P2 finalises the module name.
# Expected signature:  async def analyze_text(text: str) -> dict
from services.gemini_service import analyze_text  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/check-image",
    tags=["Image OCR Check"],
)

# ── Allowed MIME types ───────────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

# ── Max upload size: 10 MB ───────────────────────────────────────────────────
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


# ── Pydantic response model ──────────────────────────────────────────────────
# TODO (P3 → P2): replace this placeholder with the *exact* model P2 uses for
# /check-text so the frontend result card receives identical JSON for both
# text and image submissions.
#
# Example (update fields to match P2's actual model):
#
# from pydantic import BaseModel
# class AnalysisResult(BaseModel):
#     verdict: str          # e.g. "AI-generated" | "Human-written"
#     confidence: float     # 0.0 – 1.0
#     explanation: str
#     extracted_text: str | None = None   # P3 adds this extra field


# ── Route ────────────────────────────────────────────────────────────────────
@router.post(
    "/",
    summary="Upload an image, extract text via OCR, then analyse with Claude",
    # response_model=AnalysisResult,   # uncomment once P2 shares the model
)
async def check_image(file: UploadFile = File(...)):
    """
    Pipeline
    --------
    1. Validate the uploaded file (type + size).
    2. Open the image with Pillow.
    3. Extract text using Tesseract OCR (pytesseract).
    4. Pass extracted text to P2's `analyze_text()` helper.
    5. Return the same JSON structure as /check-text, plus the raw OCR text.
    """

    # ── 1. Validate content type ─────────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}."
            ),
        )

    # ── 2. Read & size-check the raw bytes ───────────────────────────────────
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    # ── 3. Open image with Pillow ─────────────────────────────────────────────
    try:
        image = Image.open(io.BytesIO(raw_bytes))
    except Exception as exc:
        logger.exception("Pillow could not open the uploaded file.")
        raise HTTPException(
            status_code=422,
            detail="Could not decode image. Ensure the file is a valid image.",
        ) from exc

    # ── 4. Run Tesseract OCR ──────────────────────────────────────────────────
    try:
        extracted_text: str = pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError as exc:
        logger.critical(
            "Tesseract binary not found. "
            "Install it: `brew install tesseract` or `apt-get install tesseract-ocr`."
        )
        raise HTTPException(
            status_code=500,
            detail="OCR engine not available on this server. Contact the admin.",
        ) from exc
    except Exception as exc:
        logger.exception("Tesseract OCR failed unexpectedly.")
        raise HTTPException(
            status_code=500,
            detail="OCR processing failed. Please try again.",
        ) from exc

    # ── 5. Guard: nothing to analyse if OCR returned nothing ─────────────────
    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "No text could be extracted from the image. "
                "Ensure the image contains readable text."
            ),
        )

    # ── 6. Pass extracted text to P2's Claude helper ──────────────────────────
    try:
        analysis_result: dict = await analyze_text(extracted_text)
    except Exception as exc:
        logger.exception("Claude analysis via analyze_text() failed.")
        raise HTTPException(
            status_code=502,
            detail=f"AI analysis service is currently unavailable: {str(exc)}",
        ) from exc

    # ── 7. Append OCR text to the response so the frontend can display it ────
    # TODO (P3 → P2): confirm with P2 whether adding `extracted_text` to their
    # response dict is acceptable, or whether it should live in a wrapper key.
    return {
        **analysis_result,
        "extracted_text": extracted_text,
    }
