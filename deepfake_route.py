# deepfake_route.py
# P3's route — plugs into P2's main FastAPI app via APIRouter.
#
# DEPENDS ON P2:
#   - P2 must register this router in their main.py:
#       from deepfake_route import router as deepfake_router
#       app.include_router(deepfake_router)
#
# ENVIRONMENT VARIABLES (add to shared .env.example — tell P2):
#   SIGHTENGINE_API_USER   — Sightengine account user key
#   SIGHTENGINE_API_SECRET — Sightengine account secret key
#
#   Sightengine is used here because it has a straightforward REST API,
#   a free tier for prototyping, and no binary system dependency.
#   Docs: https://sightengine.com/docs/detect-ai-generated-images
#
# SYSTEM DEPENDENCY:
#   None beyond `pip install httpx python-dotenv` — no binary like Tesseract.
#   This makes Render deployment straightforward (no Dockerfile needed for
#   this route specifically).

import logging
import os

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/check-deepfake",
    tags=["Deepfake Detection"],
)

# ── Sightengine credentials (from environment) ───────────────────────────────
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")
SIGHTENGINE_ENDPOINT = "https://api.sightengine.com/1.0/check.json"

# ── Allowed MIME types ───────────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# ── Max upload size: 10 MB ───────────────────────────────────────────────────
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


# ── Response model ───────────────────────────────────────────────────────────
# Intentionally kept flat and parallel to P2's /check-text response shape so
# the frontend result card can render both with the same component.
#
# TODO (P3 → P2): confirm field names match whatever P2 finalises for their
# AnalysisResult model. At minimum `verdict`, `confidence`, `explanation`
# should be identical keys so the frontend doesn't need a special case.
class DeepfakeResult(BaseModel):
    verdict: str          # "AI-generated" | "Likely AI-generated" | "Likely Real" | "Real"
    confidence: float     # 0.0 – 1.0  (maps directly from Sightengine's ai_generated score)
    explanation: str      # Human-readable summary for the result card
    ai_score_raw: float   # Raw Sightengine score, kept for transparency / debugging


# ── Internal helper ───────────────────────────────────────────────────────────
def _interpret_score(ai_score: float) -> tuple[str, str]:
    """
    Map Sightengine's ai_generated probability (0.0–1.0) to a
    human-readable verdict and explanation string.

    Thresholds chosen to be conservative — bias toward flagging rather
    than missing AI-generated content.
    """
    if ai_score >= 0.85:
        verdict = "AI-generated"
        explanation = (
            f"The image shows very strong signals of AI generation "
            f"(score: {ai_score:.0%}). It is almost certainly synthetic."
        )
    elif ai_score >= 0.60:
        verdict = "Likely AI-generated"
        explanation = (
            f"The image shows notable signals of AI generation "
            f"(score: {ai_score:.0%}). Treat with caution."
        )
    elif ai_score >= 0.35:
        verdict = "Likely Real"
        explanation = (
            f"The image shows limited AI generation signals "
            f"(score: {ai_score:.0%}). It is probably authentic."
        )
    else:
        verdict = "Real"
        explanation = (
            f"The image shows very few AI generation signals "
            f"(score: {ai_score:.0%}). It appears to be authentic."
        )
    return verdict, explanation


# ── Route ─────────────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=DeepfakeResult,
    summary="Upload an image and detect whether it is AI-generated / a deepfake",
)
async def check_deepfake(file: UploadFile = File(...)):
    """
    Pipeline
    --------
    1. Validate credentials are present (fast-fail on misconfigured env).
    2. Validate the uploaded file (type + size).
    3. Forward the image to Sightengine's AI-generated image detection model.
    4. Parse the response and map the score to a verdict.
    5. Return a flat JSON response matching P2's result card schema.
    """

    # ── 1. Guard: credentials must be set ────────────────────────────────────
    if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
        logger.critical(
            "SIGHTENGINE_API_USER or SIGHTENGINE_API_SECRET is not set. "
            "Add both to your .env file (see .env.example)."
        )
        raise HTTPException(
            status_code=500,
            detail="Deepfake detection service is not configured. Contact the admin.",
        )

    # ── 2. Validate content type ──────────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}."
            ),
        )

    # ── 3. Read & size-check the raw bytes ───────────────────────────────────
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    # ── 4. Call Sightengine REST API ──────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                SIGHTENGINE_ENDPOINT,
                data={
                    "models": "genai",          # Sightengine's AI-generated image model
                    "api_user": SIGHTENGINE_API_USER,
                    "api_secret": SIGHTENGINE_API_SECRET,
                },
                files={
                    "media": (file.filename, raw_bytes, file.content_type),
                },
            )
            response.raise_for_status()
            payload: dict = response.json()

    except httpx.TimeoutException as exc:
        logger.exception("Sightengine request timed out.")
        raise HTTPException(
            status_code=504,
            detail="Deepfake detection service timed out. Please try again.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "Sightengine returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=502,
            detail="Deepfake detection service returned an error. Please try again.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error calling Sightengine.")
        raise HTTPException(
            status_code=502,
            detail="Deepfake detection service is unavailable. Please try again later.",
        ) from exc

    # ── 5. Validate Sightengine response structure ────────────────────────────
    # Sightengine returns: { "status": "success", "type": { "ai_generated": 0.97, ... }, ... }
    try:
        sightengine_status = payload.get("status")
        if sightengine_status != "success":
            error_msg = payload.get("error", {}).get("message", "Unknown error")
            logger.error("Sightengine non-success response: %s", payload)
            raise HTTPException(
                status_code=502,
                detail=f"Deepfake detection API error: {error_msg}",
            )

        ai_score: float = float(payload["type"]["ai_generated"])

    except HTTPException:
        raise  # re-raise our own HTTP exceptions untouched
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception(
            "Unexpected Sightengine response shape: %s", payload
        )
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from deepfake detection service.",
        ) from exc

    # ── 6. Map score → verdict and build response ─────────────────────────────
    verdict, explanation = _interpret_score(ai_score)

    return DeepfakeResult(
        verdict=verdict,
        confidence=round(ai_score, 4),
        explanation=explanation,
        ai_score_raw=ai_score,
    )
