"""Avatar speech and lipsync payloads.

OWNER: Member 1 (AI Avatar Tutor & Intelligent Learning).
See plan.md §6.6.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.deps import CurrentUser
from app.services.prompts import text_to_visemes

router = APIRouter(prefix="/api/avatar", tags=["avatar"])


class SpeakRequest(BaseModel):
    text: str
    expression: str | None = "neutral"


@router.get("/status")
def avatar_status() -> dict[str, Any]:
    """Which tier is live. The frontend uses this to pick its renderer.

    Tier A = browser TTS + viseme lipsync (always available).
    Tier B = SyncTalk on a GPU box (only when AVATAR_SERVICE_URL is set).
    """
    return {
        "tier": "B" if settings.avatar_service_url else "A",
        "service_url": settings.avatar_service_url or None,
    }


@router.get("/config")
def avatar_config() -> dict[str, Any]:
    """Expression states and viseme set the frontend should support."""
    return {
        "expressions": ["neutral", "thinking", "explaining", "encouraging"],
        "visemes": ["sil", "AA", "E", "I", "O", "U", "M", "F", "L", "S"],
        "idle": {"blink_interval_ms": [3000, 6000], "sway": True},
    }


@router.post("/speak")
async def speak(body: SpeakRequest, user: CurrentUser) -> dict[str, Any]:
    """Turn text into audio plus a viseme timeline.

    Body: {text, expression?}
    Returns: {audio_url, visemes, video_stream_url?}

    video_stream_url is present only on Tier B. The frontend falls back to Tier A
    when it is absent - same endpoint, graceful degradation (plan.md 6.6).
    """
    text = body.text.strip()
    visemes = text_to_visemes(text) if text else []
    return {
        "text": text,
        "expression": body.expression or "neutral",
        "audio_url": None,
        "visemes": visemes,
        "video_stream_url": None,
    }
