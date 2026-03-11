from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class CommandError(Exception):
    """Raised by command handlers to signal a known failure with an exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_path_arg(raw: str, base_dir: Path) -> Path:
    """Resolve a CLI path argument against *base_dir* when it is relative.

    Absolute paths (and paths starting with ``~``) are expanded as-is.
    Relative paths are resolved relative to *base_dir* (typically
    ``config.project_root``).
    """
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def safe_write_json(path: Path, data: Any) -> None:
    ensure_parent(path)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_path.replace(path)


def clean_line(text: str) -> str:
    text = re.sub(r"^\s*[-*•\d\.\)\(]+\s*", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def dedupe_texts(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item.strip())
    return result


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"https?://\S+", "", lowered)
    lowered = re.sub(r"[^\wぁ-んァ-ヶ一-龠]+", "", lowered)
    return lowered


def similarity_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def highest_similarity(text: str, history_texts: list[str]) -> float:
    if not history_texts:
        return 0.0
    return max(similarity_ratio(text, past) for past in history_texts)


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text).strip()


def first_sentence(text: str) -> str:
    parts = re.split(r"[。.!?！？]", strip_urls(text), maxsplit=1)
    return parts[0].strip()


def hashtag_count(text: str) -> int:
    return len(re.findall(r"#\w+", text))


def contains_digit(text: str) -> bool:
    return any(char.isdigit() for char in text)


def contains_strong_word(text: str) -> bool:
    strong_words = (
        "おすすめ",
        "比較",
        "やめた",
        "やめろ",
        "最短",
        "危険",
        "損",
        "得",
        "無料",
        "時短",
        "固定費",
        "改善",
    )
    return any(word in text for word in strong_words)


def title_from_url(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
    slug = slug.replace("-", " ").replace("_", " ").strip()
    return slug.title() if slug else "Untitled Article"


def shorten_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
