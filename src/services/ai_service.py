from __future__ import annotations

import shlex
import subprocess
from typing import Any

from utils.config import AppConfig
from utils.helpers import clean_line, dedupe_texts, shorten_text


def load_prompt(config: AppConfig, name: str, fallback: str) -> str:
    prompt_path = config.prompts_dir / name
    if not prompt_path.exists():
        return fallback
    return prompt_path.read_text(encoding="utf-8")


def _fallback_candidates(article: dict[str, Any], count: int, max_length: int) -> list[str]:
    title = article.get("title") or "この記事"
    summary = article.get("summary") or "ポイントだけ先に押さえると、行動コストがかなり下がります。"
    url = article["url"]
    site_name = article.get("site_name") or ""

    seeds = [
        f"{title}で一番伝えたいのは、最初にやることを1つに絞ると迷いが消えるという点です。{url}",
        f"{title}を読む前に結論だけ。遠回りに見える作業ほど、最初に切るとかなり楽になります。{url}",
        f"{title}の話、難しいことはしていません。{summary} まず1つ試すだけで十分です。{url}",
        f"{site_name}の記事を読んで改めて思うのは、固定費もSNS運用も『先に仕組み化した人が勝つ』ということ。{url}",
        f"{title}を読むと、何をやめれば前に進めるかが見えます。無理に頑張るより先に構造を変える方が早いです。{url}",
        f"おすすめなのは気合いではなく設計です。{title}は、その差がはっきり分かる内容でした。{url}",
        f"{title}を読んで、比較するより先に不要な作業を減らすのが最短だと再確認しました。{url}",
    ]

    return [shorten_text(candidate, max_length) for candidate in seeds[:count]]


def _parse_ai_output(output: str) -> list[str]:
    lines = [clean_line(line) for line in output.splitlines()]
    return [line for line in lines if line]


def _run_external_ai(prompt: str, backend: str, config: AppConfig) -> str:
    if config.ai_command:
        template = shlex.split(config.ai_command)
        if "{prompt}" in template:
            command = [prompt if part == "{prompt}" else part for part in template]
        else:
            command = [*template, prompt]
    else:
        command = [backend]
        command.append(prompt)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.strip()


def generate_candidates(
    article: dict[str, Any],
    config: AppConfig,
    count: int,
    backend: str | None = None,
) -> tuple[list[str], str]:
    resolved_backend = backend or config.default_ai_backend
    fallback = load_prompt(
        config,
        "tweet_generation.txt",
        (
            "あなたはX運用担当です。記事URLを元に140文字以内の投稿案を5つ作ってください。"
            "出力は投稿文のみを1行ずつ返してください。"
        ),
    )
    prompt = fallback.format(
        url=article["url"],
        title=article.get("title", ""),
        summary=article.get("summary", ""),
        site_name=config.site_name,
        count=count,
    )

    candidates: list[str] = []
    if resolved_backend not in {"mock", "fallback", "none"}:
        try:
            output = _run_external_ai(prompt, resolved_backend, config)
            candidates = dedupe_texts(_parse_ai_output(output))
        except Exception:
            candidates = []

    if len(candidates) < count:
        candidates.extend(_fallback_candidates(article, count * 2, config.max_tweet_length))
        candidates = dedupe_texts(candidates)

    return candidates[:count], resolved_backend


def choose_best_with_ai(
    article: dict[str, Any],
    candidates: list[dict[str, Any]],
    config: AppConfig,
    backend: str | None = None,
) -> int | None:
    resolved_backend = backend or config.default_ai_backend
    if resolved_backend in {"mock", "fallback", "none"}:
        return None

    fallback = load_prompt(
        config,
        "tweet_scoring.txt",
        (
            "次の候補の中から最も良いX投稿を1つ選び、数字だけ返してください。"
            "評価基準: フック、読みやすさ、宣伝臭の低さ、140文字以内。"
        ),
    )
    choices = "\n".join(f"{index + 1}. {item['text']}" for index, item in enumerate(candidates))
    prompt = fallback.format(
        title=article.get("title", ""),
        summary=article.get("summary", ""),
        url=article["url"],
        candidates=choices,
    )

    try:
        output = _run_external_ai(prompt, resolved_backend, config)
    except Exception:
        return None

    for token in output.replace(",", " ").split():
        if token.isdigit():
            number = int(token)
            if 1 <= number <= len(candidates):
                return number - 1
    return None
