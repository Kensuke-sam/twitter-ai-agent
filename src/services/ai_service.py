from __future__ import annotations

from itertools import product
import shlex
import subprocess
from typing import Any

from utils.config import AppConfig
from utils.helpers import clean_line, dedupe_texts, shorten_text


# Lazy import to avoid circular dependency at module level; only used for logging.
def _append_log(config: AppConfig, level: str, message: str, **extra: Any) -> None:
    try:
        from services.log_service import append_log  # noqa: PLC0415

        append_log(config, level, message, **extra)
    except Exception:
        pass


def load_prompt(config: AppConfig, name: str, fallback: str) -> str:
    prompt_path = config.prompts_dir / name
    if not prompt_path.exists():
        return fallback
    return prompt_path.read_text(encoding="utf-8")


def _fallback_candidates(
    article: dict[str, Any], count: int, max_length: int
) -> list[str]:
    title = article.get("title") or "この記事"
    summary = (
        article.get("summary")
        or "ポイントだけ先に押さえると、行動コストがかなり下がります。"
    )
    url = article["url"]
    site_name = article.get("site_name") or ""

    lead_ins = [
        f"{title}で一番伝えたいのは、",
        f"{title}を読む前に結論だけ。 ",
        f"{title}の話、難しいことはしていません。 ",
        "先に要点だけ言うと、",
        "いちばん大事なのは、",
        "遠回りに見えても、",
        "最初に整理したいのは、",
        "読んでいて強く思ったのは、",
        "おすすめなのは気合いではなく、",
        "比較するより先に見るべきなのは、",
    ]
    bodies = [
        f"{summary} ",
        "最初にやることを1つに絞ると迷いがかなり減るという点です。 ",
        "不要な作業を先に切ると、動き出しが一気に軽くなるという話です。 ",
        "構造を少し変えるだけで続けやすさがかなり変わる、という内容です。 ",
        "難しく見えるものほど入口をシンプルにすると続きやすい、という話です。 ",
        f"{site_name}の記事らしく、最初のハードルを下げる視点が分かりやすいです。 ",
    ]
    closings = [
        "まず1つ試すだけで十分です。",
        "最初の一歩を軽くしたい人ほど刺さる内容でした。",
        "迷って止まりがちなときほど効く視点でした。",
        "無理に頑張る前に読んでおくとかなり楽になります。",
        "始め方を整えたいときの参考になります。",
        "次に何をするかがすぐ決まる記事でした。",
    ]

    candidates: list[str] = []
    for lead_in, body, closing in product(lead_ins, bodies, closings):
        candidate = f"{lead_in}{body}{closing}{url}"
        candidates.append(shorten_text(candidate, max_length))
        if len(candidates) >= count * 2:
            break

    return candidates[:count]


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
    try:
        prompt = fallback.format(
            url=article["url"],
            title=article.get("title", ""),
            summary=article.get("summary", ""),
            site_name=config.site_name,
            count=count,
        )
    except KeyError as exc:
        _append_log(
            config,
            "WARNING",
            "tweet_generation prompt has unknown placeholder, using raw template",
            missing_key=str(exc),
        )
        prompt = fallback

    candidates: list[str] = []
    if resolved_backend not in {"mock", "fallback", "none"}:
        try:
            output = _run_external_ai(prompt, resolved_backend, config)
            candidates = dedupe_texts(_parse_ai_output(output))
        except Exception as exc:
            _append_log(
                config,
                "WARNING",
                "AI candidate generation failed, using fallback",
                backend=resolved_backend,
                error=str(exc),
            )
            candidates = []

    if len(candidates) < count:
        candidates.extend(
            _fallback_candidates(article, count * 2, config.max_tweet_length)
        )
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
    choices = "\n".join(
        f"{index + 1}. {item['text']}" for index, item in enumerate(candidates)
    )
    try:
        prompt = fallback.format(
            title=article.get("title", ""),
            summary=article.get("summary", ""),
            url=article["url"],
            candidates=choices,
        )
    except KeyError as exc:
        _append_log(
            config,
            "WARNING",
            "tweet_scoring prompt has unknown placeholder, using raw template",
            missing_key=str(exc),
        )
        prompt = fallback

    try:
        output = _run_external_ai(prompt, resolved_backend, config)
    except Exception as exc:
        _append_log(
            config,
            "WARNING",
            "AI best-candidate selection failed",
            backend=resolved_backend,
            error=str(exc),
        )
        return None

    for token in output.replace(",", " ").split():
        if token.isdigit():
            number = int(token)
            if 1 <= number <= len(candidates):
                return number - 1
    return None
