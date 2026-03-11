from __future__ import annotations

from services.log_service import append_history_record, append_log, load_history
from services.twitter_service import post_tweet
from utils.config import AppConfig
from utils.helpers import CommandError, highest_similarity, now_iso


def register(subparsers) -> None:
    parser = subparsers.add_parser("post", help="投稿する")
    parser.add_argument("--text", required=True, help="投稿本文")
    parser.add_argument("--url", default="", help="紐づく記事URL")
    parser.add_argument("--title", default="", help="記事タイトル")
    parser.add_argument("--reply-to", default="", help="返信先ID")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず表示のみ")
    parser.add_argument("--force", action="store_true", help="類似チェックをスキップする")
    parser.set_defaults(handler=handle)


def handle(args, config: AppConfig) -> int:
    history = load_history(config)

    if args.url and any(item.get("url") == args.url for item in history):
        raise CommandError("this article URL has already been posted", exit_code=2)

    similarity = highest_similarity(args.text, [str(item.get("tweet", "")) for item in history if item.get("tweet")])
    if similarity >= 0.92 and not args.force:
        raise CommandError("tweet is too similar to post history; use --force to override", exit_code=2)

    result = post_tweet(config, args.text, reply_to=args.reply_to, dry_run=args.dry_run)

    if args.dry_run:
        print("[DRY RUN] selected tweet:")
        print(args.text)
        append_log(config, "INFO", "post dry-run", url=args.url, similarity=round(similarity, 3))
        return 0

    record = {
        "posted_at": now_iso(),
        "url": args.url,
        "title": args.title,
        "tweet": args.text,
        "source": "manual-post",
        "reply_to": args.reply_to,
    }
    append_history_record(config, record)
    append_log(config, "INFO", "tweet posted", url=args.url, similarity=round(similarity, 3))
    print(result["status"])
    return 0
