from __future__ import annotations

import argparse
import sys

from commands import autopilot, generate, history, post, score
from services.log_service import ensure_storage
from utils.config import load_config
from utils.helpers import CommandError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="twitter-ai-agent: CLI-first AI-assisted posting engine",
    )
    subparsers = parser.add_subparsers(dest="command")
    generate.register(subparsers)
    score.register(subparsers)
    post.register(subparsers)
    history.register(subparsers)
    autopilot.register(subparsers)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    config = load_config()
    ensure_storage(config)

    try:
        return int(args.handler(args, config))
    except CommandError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive fallback for CLI usage
        print(f"[ERROR] unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
