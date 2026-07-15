"""Application configuration loading and saving."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def get_app_base_dir() -> Path:
    """Return the editable app directory for source or frozen execution."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


CONFIG_PATH = get_app_base_dir() / "config" / "config.json"


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration persisted in config/config.json."""

    chrome_profile: str = "C:/MailAutoProfile"
    timeout: int = 20
    save_path: str = "D:/MailScreenshot"
    mail_url: str = "https://mail.163.com/"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load application config from JSON.

    Missing files are created with defaults. Unknown keys are ignored so older
    config files remain compatible after future fields are added.
    """

    path = config_path or CONFIG_PATH
    if not path.exists():
        default_config = AppConfig()
        save_config(default_config, path)
        return default_config

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件不是有效JSON: {path}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError(f"配置文件格式错误，根节点必须是对象: {path}")

    defaults = AppConfig().to_dict()
    merged = {**defaults, **raw_data}
    timeout = _coerce_timeout(merged.get("timeout"), defaults["timeout"])

    return AppConfig(
        chrome_profile=str(merged.get("chrome_profile") or defaults["chrome_profile"]),
        timeout=timeout,
        save_path=str(merged.get("save_path") or defaults["save_path"]),
        mail_url=str(merged.get("mail_url") or defaults["mail_url"]),
    )


def save_config(config: AppConfig, config_path: Path | None = None) -> None:
    """Persist application config as UTF-8 JSON."""

    path = config_path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_config(config_path: Path | None = None, **updates: Any) -> AppConfig:
    """Load, update selected config fields, save, and return the new config."""

    current = load_config(config_path)
    data = current.to_dict()
    allowed_keys = set(data)

    for key, value in updates.items():
        if key in allowed_keys and value is not None:
            data[key] = value

    updated = AppConfig(
        chrome_profile=str(data["chrome_profile"]),
        timeout=_coerce_timeout(data["timeout"], current.timeout),
        save_path=str(data["save_path"]),
        mail_url=str(data["mail_url"]),
    )
    save_config(updated, config_path)
    return updated


def _coerce_timeout(value: Any, fallback: int) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        return fallback

    return timeout if timeout > 0 else fallback
