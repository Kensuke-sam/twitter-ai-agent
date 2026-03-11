from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.helpers import CommandError, title_from_url


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    url = str(article.get("url", "")).strip()
    if not url:
        raise CommandError("article data is missing a url", exit_code=2)
    title = str(article.get("title", "")).strip() or title_from_url(url)
    summary = str(article.get("summary", "")).strip()
    tags = article.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    return {
        "url": url,
        "title": title,
        "summary": summary,
        "tags": [str(tag) for tag in tags],
        "published_at": str(article.get("published_at", "")).strip(),
    }


def resolve_single_article(
    url: str, title: str = "", summary: str = ""
) -> dict[str, Any]:
    if not url:
        raise CommandError("article url is required", exit_code=2)
    return _normalize_article(
        {
            "url": url,
            "title": title,
            "summary": summary,
        }
    )


def load_articles(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise CommandError(f"articles file not found: {path}", exit_code=2)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CommandError("articles file must be a JSON array", exit_code=2)
    return [_normalize_article(article) for article in raw]


def filter_unposted_articles(
    articles: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    posted_urls = {str(item.get("url", "")).strip() for item in history}
    return [article for article in articles if article["url"] not in posted_urls]


def select_article(
    articles: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    available = filter_unposted_articles(articles, history)
    if not available:
        raise CommandError("no unposted articles were found", exit_code=2)
    return available[0]
