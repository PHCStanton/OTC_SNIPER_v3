"""FastAPI router for trade results analysis and voice playback."""

from __future__ import annotations

import logging
import struct
import json
import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.analysis_service import get_analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
logger = logging.getLogger("otc_sniper.api.analysis")


class AIAnalysisRequest(BaseModel):
    session_id: str
    kind: str  # 'ghost' or 'live'

class PatternSaveRequest(BaseModel):
    name: str
    session_id: str
    kind: str
    regime: str
    win_rate: float
    advisory_notes: str

@router.get("/sessions")
async def get_sessions():
    """Load session list and daily statistical charts data."""
    try:
        service = get_analysis_service()
        return service.get_all_sessions()
    except Exception as e:
        logger.error("Failed to load sessions: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-ai-refinement")
async def run_ai_refinement(request: AIAnalysisRequest):
    """Run Grok 4.3 evaluation over a session's log results."""
    try:
        service = get_analysis_service()
        res = await service.run_ai_refinement(request.session_id, request.kind)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI refinement failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns")
async def get_patterns():
    """Retrieve saved market pattern logs from memory."""
    try:
        service = get_analysis_service()
        return service.load_patterns()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/patterns")
async def save_pattern(request: PatternSaveRequest):
    """Save a user/AI identified market pattern into memory."""
    try:
        service = get_analysis_service()
        patterns = service.save_pattern(request.dict())
        return {"success": True, "patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/speech")
async def text_to_speech(text: str = Query(..., description="Text to speak")):
    """
    Generate a simple valid WAV audio stream representing the spoken text feedback.
    Generates a tiny 8kHz mono PCM WAV file (e.g. beep/tone) so the browser can play it,
    while the frontend uses Web Speech API for actual high-fidelity speech synthesis.
    """
    try:
        # Generate a 0.5-second 800Hz sine wave tone at 8kHz sample rate
        sample_rate = 8000
        duration = 0.5
        num_samples = int(sample_rate * duration)
        
        # Audio format specifications: 8000Hz, 16-bit, mono (2 bytes per sample)
        bytes_per_sample = 2
        data_size = num_samples * bytes_per_sample
        file_size = 36 + data_size
        
        # WAV header
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            file_size,
            b'WAVE',
            b'fmt ',
            16,               # Subchunk1Size (16 for PCM)
            1,                # AudioFormat (1 for PCM)
            1,                # NumChannels (1 for mono)
            sample_rate,      # SampleRate
            sample_rate * bytes_per_sample,  # ByteRate
            bytes_per_sample,  # BlockAlign
            16,               # BitsPerSample (16 bits)
            b'data',
            data_size
        )
        
        # Sine wave data
        import math
        frequency = 800.0
        audio_data = bytearray(header)
        for i in range(num_samples):
            # Calculate sample value
            t = float(i) / sample_rate
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * t))
            # Pack value as signed 16-bit short
            audio_data.extend(struct.pack('<h', value))
            
        return Response(content=bytes(audio_data), media_type="audio/wav")
    except Exception as e:
        logger.error("TTS audio generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate voice audio")

@router.post("/upload")
async def upload_sessions(files: List[UploadFile] = File(...)):
    """Upload session JSONL files (files or folder content) with auto-detection of kind."""
    try:
        service = get_analysis_service()
        settings = service.settings
        uploaded_count = 0
        
        for file in files:
            content = await file.read()
            # Decode content as text to check first line JSON
            text = content.decode("utf-8")
            lines = text.splitlines()
            first_line = lines[0].strip() if lines else ""
            
            kind = "ghost"
            try:
                if first_line:
                    data = json.loads(first_line)
                    # Detect kind
                    k = data.get("kind")
                    if k in ("ghost", "live"):
                        kind = k
                    elif "simulated_profit" in data or "simulated_amount" in data:
                        kind = "ghost"
                    else:
                        kind = "live"
            except Exception:
                # Fallback to name heuristic
                if "live" in file.filename.lower():
                    kind = "live"
            
            # Destination path
            target_dir = settings.data_dir / f"{kind}_trades" / "sessions"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file (basename to avoid directory traversal hacks)
            filename = os.path.basename(file.filename)
            filepath = target_dir / filename
            filepath.write_bytes(content)
            uploaded_count += 1

        # Re-fetch sessions lists to auto-trigger daily stats rebuild
        service.get_all_sessions()
        return {"success": True, "count": uploaded_count}
    except Exception as e:
        logger.error("Failed to upload sessions: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, kind: str = Query(..., description="'ghost' or 'live'")):
    """Delete a single session log file from backend storage."""
    try:
        service = get_analysis_service()
        settings = service.settings
        target_dir = settings.data_dir / f"{kind}_trades" / "sessions"
        filepath = target_dir / f"{session_id}.jsonl"
        
        if filepath.exists():
            filepath.unlink()
            # Re-fetch sessions to trigger daily stats update
            service.get_all_sessions()
            return {"success": True, "message": f"Session {session_id} deleted."}
        else:
            raise HTTPException(status_code=404, detail="Session file not found.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


