"""
Claude service — single shared helper for all routes.

Usage (from any route file):
    from services.claude_service import analyze_text

    result = await analyze_text(prompt_str)   # always await — it's async
"""

import asyncio
import json
import os
import anthropic

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SCAM_PROMPT = """
You are a scam detection expert for Indian users.

Analyze this content: {input_text}

Reply in JSON only, no extra text:
{{
  "danger_score": 0-100,
  "type": "scam|safe",
  "scam_category": "credit_card|kyc|crypto|lottery|job_fraud|safe",
  "red_flags": ["flag1", "flag2"],
  "explanation": "1-2 lines, simple language",
  "precautions": ["action1", "action2"],
  "block_recommended": true,
  "report_to": "cybercrime.gov.in"
}}
"""


def _call_claude(prompt: str) -> dict:
    """Synchronous Claude call (runs in a thread via analyze_text)."""
    message = _client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wraps output
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


async def analyze_text(input_text: str) -> dict:
    """
    Async wrapper around the (sync) Anthropic SDK.
    Runs the blocking network call in a thread pool so it doesn't block the event loop.

    Args:
        input_text: Raw text to analyse (SMS, message, URL, etc.)

    Returns:
        Parsed dict matching ScamAnalysisResult schema.
    """
    prompt = _SCAM_PROMPT.format(input_text=input_text)
    return await asyncio.to_thread(_call_claude, prompt)


async def analyze_with_custom_prompt(prompt: str) -> dict:
    """
    For P3 (image/deepfake routes) — pass a fully-formed prompt,
    get back a parsed ScamAnalysisResult-compatible dict.
    """
    return await asyncio.to_thread(_call_claude, prompt)
