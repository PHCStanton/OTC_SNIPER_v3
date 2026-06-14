"""
AI Configuration & Profiles persistence (Phase 1 foundation).

Stores rich AI profiles, voice settings, and feature mappings in
data/settings/ai_profiles.json so the backend can eventually drive
or validate model choice + reasoning per use case.

For now primarily consumed by the frontend dedicated AI Settings.
The AIService continues to respect ai_model from RuntimeSettings (synced from active profile in UI).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_PROFILES = {
    "default": {
        "name": "Fast Confirmation (Default)",
        "modelKey": "grok-4.3-fast",
        "reasoningEffort": "none",
        "includeKB": True,
        "maxTokens": 400,
        "voice": {
            "provider": "browser",  # "browser" | "grok"
            "voiceName": "",       # for browser
            "voiceId": "eve",      # for grok (eve, ara, rex, sal, leo or custom)
            "rate": 1.05,
            "pitch": 1.0,
            "volume": 0.85,
            "speed": 1.0,          # Grok TTS speed (0.7-1.5)
            "language": "en",
        },
        "description": "Optimized for low-latency binary decisions (non-reasoning)",
    },
    "deep-review": {
        "name": "Deep Review & Analysis",
        "modelKey": "grok-4.3-balanced",
        "reasoningEffort": "low",
        "includeKB": True,
        "maxTokens": 1200,
        "voice": {
            "provider": "grok",    # prefer native Grok TTS for professional output
            "voiceName": "",
            "voiceId": "rex",      # professional voice
            "rate": 0.95,
            "pitch": 1.02,
            "volume": 0.9,
            "speed": 1.0,
            "language": "en",
        },
        "description": "Higher quality for periodic reviews, analysis, and voice-overs (Grok TTS)",
    },
}

DEFAULT_FEATURE_PROFILES = {
    "confirmation": "default",
    "review": "deep-review",
    "analysis": "deep-review",
    "chat": "default",
    "voiceover": "deep-review",
}


def get_ai_profiles_path() -> Path:
    settings = get_settings()
    path = settings.data_dir / "settings" / "ai_profiles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_ai_profiles() -> dict[str, Any]:
    path = get_ai_profiles_path()
    if not path.exists():
        data = {
            "activeProfile": "default",
            "profiles": DEFAULT_PROFILES,
            "featureProfiles": DEFAULT_FEATURE_PROFILES,
            "version": 1,
        }
        save_ai_profiles(data)
        return data
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge missing defaults
        data.setdefault("profiles", DEFAULT_PROFILES)
        data.setdefault("featureProfiles", DEFAULT_FEATURE_PROFILES)
        data.setdefault("activeProfile", "default")
        return data
    except Exception as exc:
        logger.warning("Failed to load AI profiles, using defaults: %s", exc)
        return {
            "activeProfile": "default",
            "profiles": DEFAULT_PROFILES,
            "featureProfiles": DEFAULT_FEATURE_PROFILES,
            "version": 1,
        }


def save_ai_profiles(data: dict[str, Any]) -> None:
    path = get_ai_profiles_path()
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.error("Failed to save AI profiles: %s", exc)


def get_effective_model_for_feature(feature: str = "chat") -> tuple[str, dict[str, Any]]:
    """
    Returns (model_key, params) for a given feature using the persisted profiles.
    Falls back to RuntimeSettings + MODEL_REGISTRY when profiles are not rich.
    """
    from .ai_service import MODEL_REGISTRY, DEFAULT_AI_MODEL

    data = load_ai_profiles()
    profile_key = data.get("featureProfiles", {}).get(feature) or data.get("activeProfile") or "default"
    profile = data.get("profiles", {}).get(profile_key) or {}

    model_key = profile.get("modelKey") or DEFAULT_AI_MODEL
    if model_key in MODEL_REGISTRY:
        return model_key, MODEL_REGISTRY[model_key].get("params", {})

    # Fallback
    return model_key, {"reasoning_effort": "none"}


def get_effective_voice_for_feature(feature: str = "voiceover") -> dict[str, Any]:
    """
    Returns voice config dict for a feature.
    Supports:
      - provider: "browser" | "grok"
      - voiceId: for Grok TTS (eve/ara/rex/sal/leo or custom)
      - speed, language, etc. for Grok TTS
      - voiceName, rate, pitch, volume for browser
    Falls back to sensible defaults.
    """
    data = load_ai_profiles()
    profile_key = data.get("featureProfiles", {}).get(feature) or data.get("activeProfile") or "default"
    profile = data.get("profiles", {}).get(profile_key) or {}

    voice = profile.get("voice") or {}
    # Normalize / defaults
    return {
        "provider": voice.get("provider", "browser"),
        "voiceId": voice.get("voiceId") or voice.get("voice_id") or "eve",
        "voiceName": voice.get("voiceName", ""),
        "speed": float(voice.get("speed", voice.get("rate", 1.0))),
        "rate": float(voice.get("rate", 1.0)),
        "pitch": float(voice.get("pitch", 1.0)),
        "volume": float(voice.get("volume", 0.9)),
        "language": voice.get("language", "en"),
    }