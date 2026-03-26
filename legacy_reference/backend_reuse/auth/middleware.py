"""
Authentication Middleware (FastAPI dependencies)
================================================
"""
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from typing import Optional

from .local_provider import LocalAuthProvider
from .tokens import decode_access_token

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
auth_provider = LocalAuthProvider(data_dir=_DATA_DIR)

# Auto_error=False allows public routes to handle missing tokens gracefully if needed
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """FastAPI dependency to get the current authenticated user."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    token = credentials.credentials
    if not await auth_provider.validate_session(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    decoded = decode_access_token(token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    return decoded

def require_role(required_role: str):
    """FastAPI dependency factory for role-based access control."""
    async def role_checker(user: dict = Security(get_current_user)):
        roles_hierarchy = {"viewer": 1, "trader": 2, "admin": 3}
        user_role = user.get("role", "viewer")
        
        if roles_hierarchy.get(user_role, 0) < roles_hierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker
