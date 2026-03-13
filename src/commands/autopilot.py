from __future__ import annotations

from services.ai_service import generate_candidates
from services.article_service import (
    load_articles,
    resolve_single_article,
    select_article,
)
from services.log_service import (
    append_history_record,
    append_log,
    load_history,
    save_draft_batch,
)
from services.scoring_service import score_candidates
from services.twitter_service import post_tweet
from utils.config import AppConfig
from utils.helpers import (
    CommandError,
    now_iso,
    resolve_candidate_count,
    resolve_path_arg,
)


def register(subparsers) -> None:
    parser = subparsers.add_parser("autopilot", help="記事選定から投稿まで自動実行する")
    parser.add_argument("source", nargs="?", help="記事URL")
    parser.add_argument("--url", help="記事URL")
    parser.add_argument("--title", default="", help="記事タイトル")
    parser.add_argument("--summary", default="", help="記事要約")
    parser.add_argument("--articles-file", default="", help="記事一覧JSON")
    parser.add_argument("--count", type=int, help="生成候補数")
    parser.add_argument("--backend", default="", help="使用するAI backend")
    parser.add_argument("--use-ai", action="store_true", help="最終比較にAIを使う")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず表示のみ")
    parser.set_defaults(handler=handle)


def _resolve_article(args, config: AppConfig, history: list[dict]) -> dict:
    url = args.url or args.source
    if url:
        article = resolve_single_article(
            url=url, title=args.title, summary=args.summary
        )
        if any(item.get("url") == article["url"] for item in history):
            raise CommandError(
                "selected article URL already exists in history", exit_code=2
            )
        return article

    articles_file = (
        resolve_path_arg(args.articles_file, config.project_root)
        if args.articles_file
        else config.articles_file
    )
    articles = load_articles(articles_file)
    return select_article(articles, history)


def handle(args, config: AppConfig) -> int:
    history = load_history(config)
    article = _resolve_article(args, config, history)
    article["site_name"] = config.site_name
    count = resolve_candidate_count(args.count, config.default_candidate_count)

    candidates, backend = generate_candidates(
        article, config, count=count, backend=args.backend or None
    )
    scored = score_candidates(
        candidates,
        history,
        article=article,
        config=config,
        use_ai=args.use_ai,
        backend=args.backend or None,
    )
    if not scored:
        raise CommandError("no tweet candidates were generated", exit_code=2)
    best = scored[0]

    payload = {
        "generated_at": now_iso(),
        "article": article,
        "backend": backend,
        "candidates": candidates,
        "scored_at": now_iso(),
        "scored_candidates": scored,
    }
    save_draft_batch(config, payload)

    print(f"[INFO] article selected: {article['url']}")
    print(f"[INFO] generated {len(candidates)} candidates")
    print(f"[INFO] best score: {best['score']}")
    if args.dry_run:
        print("[DRY RUN] selected tweet:")
        print(best["text"])
        append_log(
            config, "INFO", "autopilot dry-run", url=article["url"], score=best["score"]
        )
        return 0

    if best["metrics"]["max_similarity"] >= 0.92:
        raise CommandError("best candidate is too similar to history", exit_code=2)

    result = post_tweet(config, best["text"], dry_run=False)
    if result.get("stdout"):
        append_log(config, "INFO", "twitter-cli output", stdout=result["stdout"])
    append_history_record(
        config,
        {
            "posted_at": now_iso(),
            "url": article["url"],
            "title": article.get("title", ""),
            "tweet": best["text"],
            "score": best["score"],
            "source": "autopilot",
        },
    )
    append_log(
        config, "INFO", "autopilot posted", url=article["url"], score=best["score"]
    )
    print(result["status"])
    return 0
