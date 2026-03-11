from __future__ import annotations

from typing import Any

from utils.config import AppConfig
from utils.helpers import (
    contains_digit,
    contains_strong_word,
    first_sentence,
    hashtag_count,
    highest_similarity,
    strip_urls,
)


def _score_single_candidate(
    text: str,
    history: list[dict[str, Any]],
    article: dict[str, Any],
    max_length: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    history_texts = [str(item.get("tweet", "")) for item in history if item.get("tweet")]

    length = len(text)
    score = 40

    if length <= max_length:
        if 120 <= length <= max_length:
            score += 20
            reasons.append("120〜140字に収まっている")
        elif 90 <= length < 120:
            score += 12
            reasons.append("短すぎず長すぎない")
        else:
            score += 5
            reasons.append("長さは許容範囲")
    else:
        score -= 30
        reasons.append("140字を超えている")

    lead = first_sentence(text)
    if 8 <= len(lead) <= 36:
        score += 15
        reasons.append("1文目が短くフックになっている")

    if contains_digit(text):
        score += 10
        reasons.append("数字が入っている")

    if contains_strong_word(text):
        score += 10
        reasons.append("強い語が入っている")

    if hashtag_count(text) > 2:
        score -= 15
        reasons.append("ハッシュタグが多すぎる")

    non_url_length = len(strip_urls(text))
    if non_url_length > 110:
        score -= 10
        reasons.append("URL以外の本文が長い")
    else:
        score += 10
        reasons.append("URL以外の本文が読みやすい長さ")

    max_similarity = highest_similarity(text, history_texts)
    if max_similarity >= 0.85:
        score -= 30
        reasons.append("過去投稿との類似度が高い")
    elif max_similarity >= 0.70:
        score -= 20
        reasons.append("過去投稿とやや似ている")

    if article["url"] and article["url"] in text:
        score += 5
        reasons.append("記事URLが含まれている")

    return {
        "text": text,
        "score": max(score, 0),
        "reasons": reasons,
        "metrics": {
            "length": length,
            "non_url_length": non_url_length,
            "max_similarity": round(max_similarity, 3),
        },
    }


def score_candidates(
    candidates: list[str],
    history: list[dict[str, Any]],
    article: dict[str, Any],
    config: AppConfig,
    use_ai: bool = False,
    backend: str | None = None,
) -> list[dict[str, Any]]:
    scored = [
        _score_single_candidate(candidate, history, article, config.max_tweet_length)
        for candidate in candidates
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)

    if use_ai and scored:
        from services.ai_service import choose_best_with_ai

        top_candidates = scored[: min(3, len(scored))]
        winner_index = choose_best_with_ai(article, top_candidates, config, backend=backend)
        if winner_index is not None:
            for index, candidate in enumerate(top_candidates):
                if index == winner_index:
                    candidate["score"] += 8
                    candidate["reasons"].append("AI最終比較で優先")
            scored.sort(key=lambda item: item["score"], reverse=True)

    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank
    return scored
