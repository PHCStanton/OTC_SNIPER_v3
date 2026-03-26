"""
Auth API Router
===============
Endpoints for login, user management, and session handling.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from sys import path
import os
# Ensure auth package is in path
path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from auth.local_provider import LocalAuthProvider
from auth.middleware import require_role, get_current_user
from pathlib import Path
from auth.credentials import CredentialManager

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
auth_provider = LocalAuthProvider(data_dir=_DATA_DIR)
cred_manager = CredentialManager(data_dir=_DATA_DIR)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    role: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    try:
        session = await auth_provider.authenticate({
            "username": request.username,
            "password": request.password
        })
        return LoginResponse(
            token=session.token,
            user_id=session.user_id,
            username=session.username,
            role=session.role
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"username": user.get("sub"), "role": user.get("role"), "user_id": user.get("user_id")}

class CredentialSaveRequest(BaseModel):
    broker_name: str
    account_type: str
    ssid: str

@router.post("/credentials")
async def save_credentials(request: CredentialSaveRequest, user: dict = Depends(require_role("admin"))):
    cred_manager.save_credentials(request.broker_name, request.account_type, {"ssid": request.ssid})
    return {"success": True}

@router.get("/credentials/{broker_name}/{account_type}")
async def get_credentials(broker_name: str, account_type: str, user: dict = Depends(require_role("admin"))):
    creds = cred_manager.load_credentials(broker_name, account_type)
    if creds and "ssid" in creds:
        ssid = creds["ssid"]
        masked = ssid[:10] + "..." + ssid[-10:] if len(ssid) > 20 else "***"
        return {"configured": True, "masked_ssid": masked}
    return {"configured": False}
