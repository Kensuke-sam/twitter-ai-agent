from __future__ import annotations

from pathlib import Path

from services.log_service import append_log, load_draft_batch, load_history, save_draft_batch
from services.scoring_service import score_candidates
from utils.config import AppConfig
from utils.helpers import CommandError, now_iso


def register(subparsers) -> None:
    parser = subparsers.add_parser("score", help="投稿候補を採点する")
    parser.add_argument("--input", default="data/drafts.json", help="採点対象のJSON")
    parser.add_argument("--use-ai", action="store_true", help="上位候補の最終比較にAIを使う")
    parser.add_argument("--backend", default="", help="使用するAI backend")
    parser.set_defaults(handler=handle)


def handle(args, config: AppConfig) -> int:
    input_path = Path(args.input).expanduser()
    if not input_path.is_absolute():
        input_path = (config.project_root / input_path).resolve()

    batch = load_draft_batch(input_path)
    article = batch.get("article")
    candidates = batch.get("candidates", [])
    if not isinstance(article, dict) or not isinstance(candidates, list) or not candidates:
        raise CommandError("draft file does not contain candidates", exit_code=2)

    scored = score_candidates(
        [str(candidate) for candidate in candidates],
        load_history(config),
        article=article,
        config=config,
        use_ai=args.use_ai,
        backend=args.backend or None,
    )
    batch["scored_at"] = now_iso()
    batch["scored_candidates"] = scored
    save_draft_batch(config, batch, output_path=input_path)
    append_log(config, "INFO", "scored tweet candidates", input=str(input_path), count=len(scored))

    for item in scored:
        print(f"[{item['rank']}] score={item['score']} text={item['text']}")
    return 0
