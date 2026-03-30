"""Runtime configuration for the OTC SNIPER v3 backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Expected integer value, got: {value!r}") from exc


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class RuntimeSettings:
    app_name: str
    version: str
    host: str
    port: int
    chrome_port: int
    chrome_profile_dir: Path
    chrome_url: str
    chrome_executable: str  # empty string = auto-detect
    enable_ops: bool
    grok_api_key: str
    ai_model: str
    ai_enabled: bool
    app_root: Path
    data_dir: Path
    default_real_ssid: str
    default_demo_ssid: str

    @property
    def legacy_reference_dir(self) -> Path:
        return self.app_root.parent / "legacy_reference"

    def get_default_ssid(self, demo: bool = False) -> str:
        return self.default_demo_ssid if demo else self.default_real_ssid

    def ensure_directories(self) -> List[Path]:
        required = [
            self.data_dir,
            self.data_dir / "tick_logs",
            self.data_dir / "signals",
            self.data_dir / "ghost_trades" / "sessions",
            self.data_dir / "ghost_trades" / "stats",
            self.data_dir / "live_trades" / "sessions",
            self.data_dir / "live_trades" / "stats",
            self.data_dir / "settings",
            self.data_dir / "settings" / "accounts",
            self.data_dir / "settings" / "brokers",
            self.data_dir / "auth",
            self.data_dir / "auth" / "sessions",
            self.data_dir / "data_output" / "logs",
        ]

        for path in required:
            path.mkdir(parents=True, exist_ok=True)
        return required

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        app_root = Path(__file__).resolve().parents[1]
        load_env_file(app_root / ".env")
        data_dir = Path(os.getenv("OTC_DATA_DIR", str(app_root / "data"))).resolve()

        # Chrome profile lives one level above app/ so it persists across rebuilds
        default_chrome_profile = str(app_root.parent / "Chrome_profile")

        return cls(
            app_name=os.getenv("OTC_APP_NAME", "OTC SNIPER v3"),
            version=os.getenv("OTC_APP_VERSION", "3.0.0"),
            host=os.getenv("OTC_HOST", "127.0.0.1"),
            port=_parse_int(os.getenv("OTC_PORT"), 8000),
            chrome_port=_parse_int(os.getenv("CHROME_PORT"), 9222),
            chrome_profile_dir=Path(os.getenv("CHROME_PROFILE_DIR", default_chrome_profile)).resolve(),
            chrome_url=os.getenv(
                "CHROME_URL",
                "https://pocket2.click/cabinet/demo-quick-high-low",
            ),
            chrome_executable=os.getenv("CHROME_PATH", ""),
            enable_ops=_parse_bool(os.getenv("QFLX_ENABLE_OPS"), False),
            grok_api_key=os.getenv("GROK_API_KEY", "").strip(),
            ai_model=os.getenv("AI_MODEL", "grok-4-1-fast-non-reasoning").strip() or "grok-4-1-fast-non-reasoning",
            ai_enabled=_parse_bool(os.getenv("AI_ENABLED"), True) and bool(os.getenv("GROK_API_KEY", "").strip()),
            app_root=app_root,
            data_dir=data_dir,
            default_real_ssid=os.getenv("PO_SSID_REAL", ""),
            default_demo_ssid=os.getenv("PO_SSID_DEMO", ""),
        )


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    settings = RuntimeSettings.from_env()
    settings.ensure_directories()
    return settings
