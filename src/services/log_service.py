from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.config import AppConfig
from utils.helpers import now_iso, safe_read_json, safe_write_json


def ensure_storage(config: AppConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    if not config.articles_file.exists():
        safe_write_json(config.articles_file, [])
    if not config.drafts_file.exists():
        safe_write_json(config.drafts_file, {})
    if not config.history_file.exists():
        safe_write_json(config.history_file, [])


def load_history(config: AppConfig) -> list[dict[str, Any]]:
    data = safe_read_json(config.history_file, [])
    return data if isinstance(data, list) else []


def save_history(config: AppConfig, history: list[dict[str, Any]]) -> None:
    safe_write_json(config.history_file, history)


def append_history_record(config: AppConfig, record: dict[str, Any]) -> None:
    history = load_history(config)
    history.append(record)
    save_history(config, history)


def save_draft_batch(config: AppConfig, payload: dict[str, Any], output_path: Path | None = None) -> Path:
    target = output_path or config.drafts_file
    safe_write_json(target, payload)
    return target


def load_draft_batch(path: Path) -> dict[str, Any]:
    data = safe_read_json(path, {})
    return data if isinstance(data, dict) else {}


def append_log(config: AppConfig, level: str, message: str, **extra: Any) -> None:
    log_path = config.logs_dir / "app.log"
    entry = {
        "timestamp": now_iso(),
        "level": level.upper(),
        "message": message,
        **extra,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
