from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "data").mkdir()
        (self.root / "logs").mkdir()
        (self.root / "data" / "articles.json").write_text(
            json.dumps(
                [
                    {
                        "url": "https://example.com/article-a",
                        "title": "固定費を下げると家計管理が楽になる理由",
                        "summary": "節約は気合いより先に仕組み化した方が続きます。",
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (self.root / "data" / "drafts.json").write_text("{}", encoding="utf-8")
        (self.root / "data" / "history.json").write_text("[]", encoding="utf-8")
        (self.root / "config.json").write_text(
            json.dumps(
                {
                    "articles_file": "data/articles.json",
                    "drafts_file": "data/drafts.json",
                    "history_file": "data/history.json",
                    "logs_dir": "logs",
                    "default_ai_backend": "mock",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["TWITTER_AI_AGENT_ROOT"] = str(REPO_ROOT)
        env["TWITTER_AI_AGENT_CONFIG"] = str(self.root / "config.json")
        return subprocess.run(
            ["python3", str(REPO_ROOT / "src" / "main.py"), *args],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
        )

    def test_autopilot_dry_run(self) -> None:
        result = self._run("autopilot", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[INFO] article selected:", result.stdout)
        self.assertIn("[DRY RUN] selected tweet:", result.stdout)

    def test_generate_and_score(self) -> None:
        generate = self._run("generate", "--url", "https://example.com/article-b", "--title", "固定費を減らす")
        self.assertEqual(generate.returncode, 0, generate.stderr)

        score = self._run("score", "--input", str(self.root / "data" / "drafts.json"))
        self.assertEqual(score.returncode, 0, score.stderr)
        self.assertIn("score=", score.stdout)

    def test_manual_post_dry_run(self) -> None:
        result = self._run("post", "--text", "固定費を見直すなら最初に支払い方法を減らす方が早いです。")
        self.assertEqual(result.returncode, 3, result.stderr)

        dry_run = self._run(
            "post",
            "--text",
            "固定費を見直すなら最初に支払い方法を減らす方が早いです。",
            "--dry-run",
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("[DRY RUN] selected tweet:", dry_run.stdout)


if __name__ == "__main__":
    unittest.main()
