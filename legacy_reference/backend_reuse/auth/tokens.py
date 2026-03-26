import time
from typing import Dict, Any, Optional
import jwt
import os

# In a real application, this should be loaded from environment variables
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "quflx_v2_development_secret_key_change_in_production")
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = time.time() + expires_delta
    else:
        expire = time.time() + 15 * 60  # 15 minutes
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token."""
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.PyJWTError:
        return None
