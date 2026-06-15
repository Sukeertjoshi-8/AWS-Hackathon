"""
Gemini service — single shared helper for all routes.
Uses the current google-genai SDK (google.genai), NOT the deprecated google.generativeai.

Usage (from any route file):
    from services.gemini_service import analyze_text

    result = await analyze_text(input_text)   # always await — it's async
"""

import asyncio
import json
import os
from google import genai

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_SCAM_PROMPT = """
You are a scam detection expert for Indian users.

Analyze this content: {input_text}

Reply in JSON only, no extra text, no markdown fences:
{{
  "danger_score": <integer 0-100>,
  "type": "scam or safe",
  "scam_category": "credit_card or kyc or crypto or lottery or job_fraud or safe",
  "red_flags": ["flag1", "flag2"],
  "explanation": "1-2 lines in simple language",
  "precautions": ["action1", "action2"],
  "block_recommended": true or false,
  "report_to": "cybercrime.gov.in"
}}
"""


def _call_gemini(prompt: str) -> dict:
    """Synchronous Gemini call (runs in a thread via async wrappers)."""
    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text.strip()

    # Strip markdown code fences if Gemini wraps output
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


async def analyze_text(input_text: str) -> dict:
    """
    Async wrapper for scam text analysis via Gemini 1.5 Flash.

    Args:
        input_text: Raw text to analyse (SMS, message, URL, etc.)

    Returns:
        Parsed dict matching ScamAnalysisResult schema.
    """
    prompt = _SCAM_PROMPT.format(input_text=input_text)
    return await asyncio.to_thread(_call_gemini, prompt)


async def analyze_with_custom_prompt(prompt: str) -> dict:
    """
    For P3 (image/deepfake routes) — pass a fully-formed prompt,
    get back a parsed ScamAnalysisResult-compatible dict.
    """
    return await asyncio.to_thread(_call_gemini, prompt)
