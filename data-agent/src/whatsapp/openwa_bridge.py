"""
OpenWA WhatsApp Gateway Bridge

Interacts with the OpenWA server API to dispatch WhatsApp messages,
retrieve gateway session status, and handle user command queries.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("data_agent.openwa_bridge")


class OpenWABridge:
    """
    Bridge client for OpenWA WhatsApp Gateway.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_recipient: Optional[str] = None,
        timeout_sec: float = 10.0,
    ):
        self.api_url = (api_url or os.getenv("OPENWA_API_URL", "http://localhost:8080")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENWA_API_KEY", "")
        self.default_recipient = default_recipient or os.getenv("OPENWA_RECIPIENT_PHONE", "")
        self.timeout_sec = timeout_sec

    async def check_health(self) -> Dict[str, Any]:
        """Query status of OpenWA gateway server."""
        url = f"{self.api_url}/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return {"connected": True, "details": res.json()}
                return {"connected": False, "status_code": res.status_code}
        except Exception as exc:
            logger.debug(f"OpenWA health check failed: {exc}")
            return {"connected": False, "error": str(exc)}

    async def send_message(self, message: str, recipient: Optional[str] = None) -> bool:
        """
        Send text message to target WhatsApp phone number.
        """
        target = recipient or self.default_recipient
        if not target:
            logger.warning("No recipient specified for WhatsApp message. Logging message locally.")
            logger.info(f"[WhatsApp Dispatch Mock] To (Default): \n{message}")
            return True

        url = f"{self.api_url}/sendText"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"to": target, "content": message}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    logger.info(f"Successfully sent WhatsApp message to {target}")
                    return True
                else:
                    logger.error(f"Failed to send WhatsApp message: {res.status_code} - {res.text}")
                    return False
        except Exception as exc:
            logger.error(f"Error communicating with OpenWA gateway: {exc}")
            return False
