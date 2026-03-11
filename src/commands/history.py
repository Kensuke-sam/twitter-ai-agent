from __future__ import annotations

import json

from services.log_service import load_history
from utils.config import AppConfig


def register(subparsers) -> None:
    parser = subparsers.add_parser("history", help="投稿履歴を表示する")
    parser.add_argument("--limit", type=int, default=20, help="表示件数")
    parser.add_argument("--json", action="store_true", help="JSONで表示")
    parser.set_defaults(handler=handle)


def handle(args, config: AppConfig) -> int:
    history = list(reversed(load_history(config)))[: args.limit]
    if args.json:
        print(json.dumps(history, ensure_ascii=False, indent=2))
        return 0

    if not history:
        print("history is empty")
        return 0

    for item in history:
        print(f"{item.get('posted_at', '-')}: {item.get('tweet', '')}")
        if item.get("url"):
            print(f"  url: {item['url']}")
    return 0
