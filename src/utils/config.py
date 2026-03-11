from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_MAX_TWEET_LENGTH_MIN = 1
_MAX_TWEET_LENGTH_MAX = 280
_CANDIDATE_COUNT_MIN = 1
_CANDIDATE_COUNT_MAX = 50


def _default_project_root() -> Path:
    override = os.environ.get("TWITTER_AI_AGENT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    logs_dir: Path
    prompts_dir: Path
    articles_file: Path
    drafts_file: Path
    history_file: Path
    max_tweet_length: int
    default_candidate_count: int
    default_ai_backend: str
    twitter_cli_path: Path | None
    twitter_auth_token: str
    twitter_ct0: str
    ai_command: str
    site_name: str


def _validate_positive_int(value: int, name: str, lo: int, hi: int) -> int:
    """Return *value* after checking it is within [lo, hi], raising ValueError otherwise."""
    if not (lo <= value <= hi):
        raise ValueError(f"config '{name}' must be between {lo} and {hi}, got {value}")
    return value


def _resolve_path(base_dir: Path, raw_path: str, fallback: str) -> Path:
    candidate = Path(raw_path or fallback).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def load_config(project_root: Path | None = None) -> AppConfig:
    root = (project_root or _default_project_root()).resolve()
    config_override = os.environ.get("TWITTER_AI_AGENT_CONFIG")
    config_path = (
        Path(config_override).expanduser().resolve() if config_override else root / "config.json"
    )
    config_base = config_path.parent.resolve()

    data: dict[str, object] = {}
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))

    logs_dir = _resolve_path(config_base, str(data.get("logs_dir", "logs")), "logs")
    data_dir = _resolve_path(config_base, str(data.get("data_dir", "data")), "data")

    twitter_cli_path_raw = str(data.get("twitter_cli_path", "")).strip()
    twitter_cli_path = (
        Path(twitter_cli_path_raw).expanduser().resolve() if twitter_cli_path_raw else None
    )

    try:
        max_tweet_length = _validate_positive_int(
            int(str(data.get("max_tweet_length", 140))),
            "max_tweet_length",
            _MAX_TWEET_LENGTH_MIN,
            _MAX_TWEET_LENGTH_MAX,
        )
        default_candidate_count = _validate_positive_int(
            int(str(data.get("default_candidate_count", 5))),
            "default_candidate_count",
            _CANDIDATE_COUNT_MIN,
            _CANDIDATE_COUNT_MAX,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid config value: {exc}") from exc

    return AppConfig(
        project_root=root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        prompts_dir=(root / "src" / "prompts").resolve(),
        articles_file=_resolve_path(
            config_base,
            str(data.get("articles_file", "data/articles.json")),
            "data/articles.json",
        ),
        drafts_file=_resolve_path(
            config_base,
            str(data.get("drafts_file", "data/drafts.json")),
            "data/drafts.json",
        ),
        history_file=_resolve_path(
            config_base,
            str(data.get("history_file", "data/history.json")),
            "data/history.json",
        ),
        max_tweet_length=max_tweet_length,
        default_candidate_count=default_candidate_count,
        default_ai_backend=str(data.get("default_ai_backend", "mock")),
        twitter_cli_path=twitter_cli_path,
        twitter_auth_token=str(data.get("twitter_auth_token", "")),
        twitter_ct0=str(data.get("twitter_ct0", "")),
        ai_command=str(data.get("ai_command", "")),
        site_name=str(data.get("site_name", "twitter-ai-agent")),
    )
