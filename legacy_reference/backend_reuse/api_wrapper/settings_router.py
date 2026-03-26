"""
Settings API Router (Phase C5)
"""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# We will need the SettingsManager
from src.settings_manager import SettingsManager
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
settings_manager = SettingsManager(data_dir=_DATA_DIR)

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class SettingUpdateRequest(BaseModel):
    value: Any

@router.get("/global")
async def get_global_settings():
    return settings_manager.get_global()

@router.put("/global/{key}")
async def update_global_setting(key: str, request: SettingUpdateRequest):
    # Basic type validation to prevent JSON serialization errors or corruption
    valid_types = (str, int, float, bool, dict, list)
    if not isinstance(request.value, valid_types) and request.value is not None:
        raise HTTPException(status_code=400, detail="Invalid value type. Must be JSON serializable.")

    # Load current
    current = settings_manager.get_global()
    # Support nested keys like "ghost_trading.enabled"
    keys = key.split(".")
    
    # Traverse and update
    target = current
    for k in keys[:-1]:
        if k not in target:
            target[k] = {}
        target = target[k]
        
    target[keys[-1]] = request.value
    
    # Save back (Need to add update method to SettingsManager properly)
    try:
        import json
        with open(settings_manager.global_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except IOError as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"ok": True, "settings": current}


