from fastapi import APIRouter, HTTPException
from models.schemas import TextInput, ScamAnalysisResult
from services.gemini_service import analyze_text
import json

router = APIRouter(prefix="", tags=["Text Analysis"])


@router.post("/check-text", response_model=ScamAnalysisResult)
async def check_text(body: TextInput):
    """
    Analyze a text message, SMS, or URL for scam indicators.
    Returns structured JSON matching ScamAnalysisResult schema.
    """
    try:
        return await analyze_text(body.text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse Gemini response as JSON: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {str(e)}")
