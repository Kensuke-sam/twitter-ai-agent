from __future__ import annotations

import os
import subprocess
from typing import Any

from utils.config import AppConfig
from utils.helpers import CommandError


def validate_tweet_text(text: str, max_length: int) -> None:
    if not text or not text.strip():
        raise CommandError("tweet text is empty", exit_code=2)
    if len(text) > max_length:
        raise CommandError(
            f"tweet text is too long: {len(text)} characters (limit: {max_length})",
            exit_code=2,
        )


def _twitter_env(config: AppConfig) -> dict[str, str]:
    env = os.environ.copy()
    if config.twitter_auth_token:
        env["TWITTER_AUTH_TOKEN"] = config.twitter_auth_token
    if config.twitter_ct0:
        env["TWITTER_CT0"] = config.twitter_ct0
    return env


def post_tweet(
    config: AppConfig,
    text: str,
    reply_to: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    validate_tweet_text(text, config.max_tweet_length)

    if dry_run:
        return {
            "status": "dry-run",
            "tweet": text,
            "reply_to": reply_to,
        }

    if not config.twitter_cli_path:
        raise CommandError("twitter_cli_path is not configured", exit_code=3)

    command = ["uv", "run", "twitter", "post", text]
    if reply_to:
        command.extend(["--reply-to", reply_to])

    try:
        result = subprocess.run(
            command,
            cwd=config.twitter_cli_path,
            env=_twitter_env(config),
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise CommandError(f"failed to run twitter-cli: {exc}", exit_code=3) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise CommandError(f"twitter-cli post failed: {stderr}", exit_code=3) from exc

    return {
        "status": "posted",
        "tweet": text,
        "stdout": result.stdout.strip(),
    }
