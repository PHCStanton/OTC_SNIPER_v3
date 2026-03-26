"""
Local Authentication Provider
=============================
File-based auth provider using bcrypt and JWT.
"""
import json
import uuid
import time
from pathlib import Path
from typing import Dict, Optional, Any
import bcrypt

from .base import AuthProvider, Session
from .tokens import create_access_token, decode_access_token

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class LocalAuthProvider(AuthProvider):
    def __init__(self, data_dir: Path):
        self.auth_dir = Path(data_dir) / "auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.auth_dir / "users.json"
        
        if not self.users_file.exists():
            self._write_default_users()
            
    def _write_default_users(self):
        # Create a default admin user
        default_users = {
            "admin": {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": hash_password("admin"),
                "role": "admin",
                "created_at": time.time()
            }
        }
        with open(self.users_file, "w") as f:
            json.dump(default_users, f, indent=2)
            
    def _load_users(self) -> Dict[str, dict]:
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return {}

    def _save_users(self, users: Dict[str, dict]):
        with open(self.users_file, "w") as f:
            json.dump(users, f, indent=2)

    async def authenticate(self, credentials: Dict[str, str]) -> Session:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise ValueError("Username and password required")
            
        users = self._load_users()
        user = users.get(username)
        
        if not user or not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid credentials")
            
        expires_delta = 24 * 3600  # 24 hours
        token = create_access_token(
            data={"sub": username, "role": user["role"], "user_id": user["id"]},
            expires_delta=expires_delta
        )
        
        return Session(
            token=token,
            user_id=user["id"],
            username=username,
            role=user["role"],
            expires_at=time.time() + expires_delta
        )

    async def validate_session(self, token: str) -> bool:
        decoded = decode_access_token(token)
        if not decoded:
            return False
        return True

    async def refresh_session(self, token: str) -> Session:
        decoded = decode_access_token(token)
        if not decoded:
            raise ValueError("Invalid or expired token")
            
        username = decoded.get("sub")
        users = self._load_users()
        user = users.get(username)
        if not user:
            raise ValueError("User not found")
            
        expires_delta = 24 * 3600
        new_token = create_access_token(
            data={"sub": username, "role": user["role"], "user_id": user["id"]},
            expires_delta=expires_delta
        )
        
        return Session(
            token=new_token,
            user_id=user["id"],
            username=username,
            role=user["role"],
            expires_at=time.time() + expires_delta
        )

    async def revoke_session(self, token: str) -> None:
        # In a stateless JWT setup, true revocation requires a blacklist.
        # For simplicity in this local provider, we do nothing.
        pass
