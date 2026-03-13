from __future__ import annotations

from services.ai_service import generate_candidates
from services.article_service import resolve_single_article
from services.log_service import append_log, save_draft_batch
from utils.config import AppConfig
from utils.helpers import CommandError, now_iso, resolve_candidate_count, resolve_path_arg


def register(subparsers) -> None:
    parser = subparsers.add_parser("generate", help="記事から投稿候補を生成する")
    parser.add_argument("source", nargs="?", help="記事URL")
    parser.add_argument("--url", help="記事URL")
    parser.add_argument("--title", default="", help="記事タイトル")
    parser.add_argument("--summary", default="", help="記事要約")
    parser.add_argument("--count", type=int, help="生成する候補数")
    parser.add_argument("--backend", default="", help="使用するAI backend")
    parser.add_argument("--output", default="", help="出力先JSON")
    parser.set_defaults(handler=handle)


def handle(args, config: AppConfig) -> int:
    url = args.url or args.source
    if not url:
        raise CommandError("generate requires --url or positional URL", exit_code=2)

    count = resolve_candidate_count(args.count, config.default_candidate_count)
    article = resolve_single_article(url=url, title=args.title, summary=args.summary)
    article["site_name"] = config.site_name
    candidates, backend = generate_candidates(
        article, config, count=count, backend=args.backend or None
    )

    payload = {
        "generated_at": now_iso(),
        "article": article,
        "backend": backend,
        "candidates": candidates,
    }

    output_path = (
        resolve_path_arg(args.output, config.project_root) if args.output else None
    )
    saved_path = save_draft_batch(config, payload, output_path=output_path)
    append_log(
        config,
        "INFO",
        "generated tweet candidates",
        url=article["url"],
        count=len(candidates),
    )

    for index, candidate in enumerate(candidates, start=1):
        print(f"候補{index}: {candidate}")
    print(f"[INFO] drafts saved: {saved_path}")
    return 0
