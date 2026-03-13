from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_ARTICLE_A = {
    "url": "https://example.com/article-a",
    "title": "冬の大三角を見つけると夜空が少し楽しくなる",
    "summary": "明るい3つの星を先に見つけるだけで、星座に詳しくなくても冬の夜空を追いやすくなります。",
}

_ARTICLE_B = {
    "url": "https://example.com/article-b",
    "title": "双眼鏡で月を見る前に知っておきたいこと",
    "summary": "満月より半月前後のほうが影が濃く出るので、クレーターの凹凸が見えやすくなります。",
}


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "data").mkdir()
        (self.root / "logs").mkdir()
        (self.root / "data" / "articles.json").write_text(
            json.dumps([_ARTICLE_A, _ARTICLE_B], ensure_ascii=False, indent=2),
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

    def _write_history(self, records: list[dict]) -> None:
        (self.root / "data" / "history.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Existing core tests
    # ------------------------------------------------------------------

    def test_autopilot_dry_run(self) -> None:
        result = self._run("autopilot", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[INFO] article selected:", result.stdout)
        self.assertIn("[DRY RUN] selected tweet:", result.stdout)

    def test_generate_and_score(self) -> None:
        generate = self._run(
            "generate",
            "--url",
            "https://example.com/article-b",
            "--title",
            "冬の大三角を見つける",
        )
        self.assertEqual(generate.returncode, 0, generate.stderr)
        self.assertIn("候補1:", generate.stdout)

        score = self._run("score", "--input", str(self.root / "data" / "drafts.json"))
        self.assertEqual(score.returncode, 0, score.stderr)
        self.assertIn("score=", score.stdout)

    def test_manual_post_dry_run(self) -> None:
        # Without --dry-run and without twitter_cli_path configured → exit 3
        result = self._run(
            "post", "--text", "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。"
        )
        self.assertEqual(result.returncode, 3, result.stderr)

        dry_run = self._run(
            "post",
            "--text",
            "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。",
            "--dry-run",
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("[DRY RUN] selected tweet:", dry_run.stdout)

    # ------------------------------------------------------------------
    # generate command
    # ------------------------------------------------------------------

    def test_generate_positional_url(self) -> None:
        """Positional URL argument should work the same as --url."""
        result = self._run("generate", "https://example.com/positional")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("候補1:", result.stdout)

    def test_generate_requires_url(self) -> None:
        result = self._run("generate")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_generate_custom_output(self) -> None:
        output_path = self.root / "data" / "custom_drafts.json"
        result = self._run(
            "generate",
            "--url",
            "https://example.com/custom",
            "--output",
            str(output_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output_path.exists(), "custom output file should be created")
        batch = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertIn("candidates", batch)
        self.assertIsInstance(batch["candidates"], list)

    def test_generate_respects_count(self) -> None:
        result = self._run(
            "generate",
            "--url",
            "https://example.com/count-test",
            "--count",
            "3",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("候補")]
        self.assertEqual(len(candidate_lines), 3)

    def test_generate_uses_config_default_candidate_count(self) -> None:
        (self.root / "config.json").write_text(
            json.dumps(
                {
                    "articles_file": "data/articles.json",
                    "drafts_file": "data/drafts.json",
                    "history_file": "data/history.json",
                    "logs_dir": "logs",
                    "default_ai_backend": "mock",
                    "default_candidate_count": 3,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result = self._run("generate", "--url", "https://example.com/default-count")
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("候補")]
        self.assertEqual(len(candidate_lines), 3)

    def test_generate_rejects_invalid_count(self) -> None:
        result = self._run(
            "generate",
            "--url",
            "https://example.com/invalid-count",
            "--count",
            "0",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("candidate count must be between", result.stderr)

    def test_generate_supports_more_than_seven_candidates_in_mock_mode(self) -> None:
        result = self._run(
            "generate",
            "--url",
            "https://example.com/more-than-seven",
            "--count",
            "8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("候補")]
        self.assertEqual(len(candidate_lines), 8)

    # ------------------------------------------------------------------
    # score command
    # ------------------------------------------------------------------

    def test_score_missing_draft_file(self) -> None:
        result = self._run("score", "--input", str(self.root / "data" / "no_such.json"))
        self.assertNotEqual(result.returncode, 0)

    def test_score_empty_draft_file(self) -> None:
        (self.root / "data" / "drafts.json").write_text(
            json.dumps({"article": {"url": "https://example.com/x"}, "candidates": []}),
            encoding="utf-8",
        )
        result = self._run("score", "--input", str(self.root / "data" / "drafts.json"))
        self.assertNotEqual(result.returncode, 0)

    def test_score_persists_ranked_results(self) -> None:
        self._run(
            "generate",
            "--url",
            "https://example.com/persist-test",
            "--output",
            str(self.root / "data" / "drafts.json"),
        )
        self._run("score", "--input", str(self.root / "data" / "drafts.json"))
        batch = json.loads((self.root / "data" / "drafts.json").read_text(encoding="utf-8"))
        self.assertIn("scored_candidates", batch)
        first = batch["scored_candidates"][0]
        self.assertIn("rank", first)
        self.assertIn("score", first)
        self.assertIn("text", first)

    # ------------------------------------------------------------------
    # post command
    # ------------------------------------------------------------------

    def test_post_duplicate_url_rejected(self) -> None:
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T00:00:00+00:00",
                    "url": "https://example.com/article-a",
                    "title": "星空",
                    "tweet": "テスト投稿です。",
                    "source": "manual-post",
                }
            ]
        )
        result = self._run(
            "post",
            "--text",
            "全く別の文面ですが同じURLです。",
            "--url",
            "https://example.com/article-a",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("already been posted", result.stderr)

    def test_post_similarity_check_blocks_near_duplicate(self) -> None:
        tweet = "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。"
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T00:00:00+00:00",
                    "url": "https://example.com/old",
                    "title": "星空",
                    "tweet": tweet,
                    "source": "manual-post",
                }
            ]
        )
        result = self._run("post", "--text", tweet, "--dry-run")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("similar", result.stderr)

    def test_post_force_overrides_similarity_check(self) -> None:
        tweet = "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。"
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T00:00:00+00:00",
                    "url": "https://example.com/old",
                    "title": "星空",
                    "tweet": tweet,
                    "source": "manual-post",
                }
            ]
        )
        result = self._run("post", "--text", tweet, "--dry-run", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DRY RUN]", result.stdout)

    def test_post_empty_text_rejected(self) -> None:
        result = self._run("post", "--text", "   ", "--dry-run")
        self.assertEqual(result.returncode, 2, result.stderr)

    # ------------------------------------------------------------------
    # history command
    # ------------------------------------------------------------------

    def test_history_empty(self) -> None:
        result = self._run("history")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("empty", result.stdout)

    def test_history_displays_entries(self) -> None:
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": "https://example.com/article-a",
                    "title": "星空",
                    "tweet": "冬の大三角だけ覚えると夜空を見るハードルが下がります。",
                    "source": "manual-post",
                },
                {
                    "posted_at": "2024-01-02T09:00:00+09:00",
                    "url": "https://example.com/article-b",
                    "title": "月観察",
                    "tweet": "半月前後はクレーターの凹凸が見えやすく、双眼鏡でも月面がかなり楽しいです。",
                    "source": "autopilot",
                },
            ]
        )
        result = self._run("history")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("冬の大三角だけ覚えると夜空を見るハードルが下がります。", result.stdout)
        self.assertIn("半月前後はクレーターの凹凸が見えやすく、双眼鏡でも月面がかなり楽しいです。", result.stdout)

    def test_history_json_flag(self) -> None:
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": "https://example.com/article-a",
                    "title": "星空",
                    "tweet": "テスト投稿。",
                    "source": "manual-post",
                }
            ]
        )
        result = self._run("history", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["url"], "https://example.com/article-a")

    def test_history_limit(self) -> None:
        records = [
            {
                "posted_at": f"2024-01-{i:02d}T09:00:00+09:00",
                "url": f"https://example.com/article-{i}",
                "title": f"記事{i}",
                "tweet": f"テスト投稿{i}。",
                "source": "manual-post",
            }
            for i in range(1, 11)
        ]
        self._write_history(records)
        result = self._run("history", "--limit", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        # 3 entries means at most 6 output lines (tweet + url per entry)
        output_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        self.assertLessEqual(len(output_lines), 6)

    def test_history_json_newest_first(self) -> None:
        """--json output should be ordered newest-first."""
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": "https://example.com/older",
                    "title": "古い記事",
                    "tweet": "古い投稿。",
                    "source": "manual-post",
                },
                {
                    "posted_at": "2024-01-02T09:00:00+09:00",
                    "url": "https://example.com/newer",
                    "title": "新しい記事",
                    "tweet": "新しい投稿。",
                    "source": "manual-post",
                },
            ]
        )
        result = self._run("history", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed[0]["url"], "https://example.com/newer")
        self.assertEqual(parsed[1]["url"], "https://example.com/older")

    # ------------------------------------------------------------------
    # autopilot command
    # ------------------------------------------------------------------

    def test_autopilot_skips_posted_articles(self) -> None:
        """autopilot should select the second article when the first is already posted."""
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": _ARTICLE_A["url"],
                    "title": _ARTICLE_A["title"],
                    "tweet": "過去の投稿文。",
                    "source": "autopilot",
                }
            ]
        )
        result = self._run("autopilot", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(_ARTICLE_B["url"], result.stdout)

    def test_autopilot_all_posted_exits_nonzero(self) -> None:
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": _ARTICLE_A["url"],
                    "title": _ARTICLE_A["title"],
                    "tweet": "投稿A。",
                    "source": "autopilot",
                },
                {
                    "posted_at": "2024-01-02T09:00:00+09:00",
                    "url": _ARTICLE_B["url"],
                    "title": _ARTICLE_B["title"],
                    "tweet": "投稿B。",
                    "source": "autopilot",
                },
            ]
        )
        result = self._run("autopilot", "--dry-run")
        self.assertNotEqual(result.returncode, 0)

    def test_autopilot_explicit_url_already_posted(self) -> None:
        self._write_history(
            [
                {
                    "posted_at": "2024-01-01T09:00:00+09:00",
                    "url": "https://example.com/explicit",
                    "title": "明示的な記事",
                    "tweet": "過去の投稿。",
                    "source": "manual-post",
                }
            ]
        )
        result = self._run(
            "autopilot",
            "--url",
            "https://example.com/explicit",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_autopilot_explicit_url_dry_run(self) -> None:
        result = self._run(
            "autopilot",
            "--url",
            "https://example.com/explicit-new",
            "--title",
            "明示的な新記事",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("https://example.com/explicit-new", result.stdout)
        self.assertIn("[DRY RUN]", result.stdout)

    def test_autopilot_saves_draft_batch(self) -> None:
        self._run("autopilot", "--dry-run")
        drafts_path = self.root / "data" / "drafts.json"
        self.assertTrue(drafts_path.exists())
        batch = json.loads(drafts_path.read_text(encoding="utf-8"))
        self.assertIn("article", batch)
        self.assertIn("candidates", batch)
        self.assertIn("scored_candidates", batch)

    def test_autopilot_rejects_invalid_count(self) -> None:
        result = self._run("autopilot", "--dry-run", "--count", "0")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("candidate count must be between", result.stderr)

    # ------------------------------------------------------------------
    # CLI meta
    # ------------------------------------------------------------------

    def test_no_args_prints_help(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage", result.stdout.lower())

    def test_unknown_command_exits_nonzero(self) -> None:
        result = self._run("nonexistent-command")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
