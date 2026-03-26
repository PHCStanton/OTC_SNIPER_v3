"""
Encrypted Credential Storage (Phase C6)
"""
import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None
    import logging
    logging.getLogger("Credentials").warning("cryptography package not installed. Credentials will not be fully encrypted.")

class CredentialManager:
    def __init__(self, data_dir: Path):
        self.creds_dir = Path(data_dir) / "auth" / "credentials"
        self.creds_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate encryption key
        self.key_file = self.creds_dir / ".key"
        if Fernet is None:
            self.fernet = None
        else:
            if not self.key_file.exists():
                key = Fernet.generate_key()
                with open(self.key_file, "wb") as f:
                    f.write(key)
            else:
                with open(self.key_file, "rb") as f:
                    key = f.read()
            self.fernet = Fernet(key)

    def _encrypt(self, data: str) -> bytes:
        if self.fernet:
            return self.fernet.encrypt(data.encode('utf-8'))
        return base64.b64encode(data.encode('utf-8'))

    def _decrypt(self, token: bytes) -> str:
        if self.fernet:
            return self.fernet.decrypt(token).decode('utf-8')
        return base64.b64decode(token).decode('utf-8')

    def save_credentials(self, broker_name: str, account_type: str, creds: Dict[str, str]) -> None:
        """Save encrypted credentials for a broker/account."""
        file_path = self.creds_dir / f"{broker_name}_{account_type}.enc"
        
        # Encrypt the JSON dump
        json_data = json.dumps(creds)
        encrypted_data = self._encrypt(json_data)
        
        with open(file_path, "wb") as f:
            f.write(encrypted_data)

    def load_credentials(self, broker_name: str, account_type: str) -> Optional[Dict[str, str]]:
        """Load and decrypt credentials."""
        file_path = self.creds_dir / f"{broker_name}_{account_type}.enc"
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
            
            json_data = self._decrypt(encrypted_data)
            return json.loads(json_data)
        except Exception as e:
            import logging
            logging.getLogger("Credentials").error(f"Failed to load credentials for {broker_name}_{account_type}: {e}")
            return None


