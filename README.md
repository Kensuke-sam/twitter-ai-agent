# twitter-ai-agent

CLI-first AI-assisted posting engine for X / Twitter.

`twitter-cli-bot` をそのまま肥大化させるのではなく、投稿実行を担う CLI foundation は残したまま、その上に AI の判断層を 1 枚だけ足すための後継 repo です。

## What this repo does

- Generate tweet candidates from an article URL
- Dry-run tweet posting before touching the real account
- Run `autopilot --dry-run` safely with local JSON history and logs
- Keep the execution layer simple and move lightweight decision-making into AI

## Current scope

This repository currently focuses on Phase 1.

- `generate`: 記事 URL から投稿候補を作る
- `post --dry-run`: 投稿前に本文を確認する
- `autopilot --dry-run`: 記事選定から候補生成、採点、最終案の表示まで通す
- `score` / `history`: 補助コマンドとして追加済み

本番投稿の運用強化、高度なスコアリング、分析機能は [TODO.md](/Users/hanesoubukensuke/twitter-ai-agent/TODO.md) で管理しています。

## Quick start

```bash
git clone <your-new-repo-url> twitter-ai-agent
cd twitter-ai-agent
cp config.json.sample config.json
chmod +x tweet.sh
```

`config.json` に最低限これだけ入れます。

```json
{
  "twitter_cli_path": "/path/to/twitter-cli",
  "default_ai_backend": "mock"
}
```

`twitter_cli_path` はローカルに clone 済みの `twitter-cli` ディレクトリです。  
`default_ai_backend` を `mock` にしておくと、外部 AI CLI が無くても `autopilot --dry-run` を確認できます。

## Dry-run first

最初はこの順だけで十分です。

```bash
./tweet.sh post --text "test post" --dry-run
./tweet.sh post --text "test post"
./tweet.sh autopilot --dry-run
```

実際に `post` を叩くのは `--dry-run` を確認してからにしてください。

## Commands

- `./tweet.sh generate --url "https://koteihi-zero.com/sample"`
- `./tweet.sh score --input data/drafts.json`
- `./tweet.sh post --text "..." --dry-run`
- `./tweet.sh history`
- `./tweet.sh autopilot --dry-run`

## Not yet implemented

未実装または運用前提でまだ固めていないものは [TODO.md](/Users/hanesoubukensuke/twitter-ai-agent/TODO.md) に分離しています。

## この repo を分ける理由

`twitter-cli-bot` は「投稿する」「検索する」「下書きを作る」ための実行ツールとして優秀です。  
一方で、この repo では「どの記事を投稿するか選ぶ」「候補を比較して最終案を選ぶ」「履歴で重複を避ける」といった判断層を扱います。  
CLI ラッパーの責務を増やしすぎず、運用ロジックだけを別 repo で進化させるために切り分けています。

## 3 層アーキテクチャ

### 1. 実行層

X へ投稿する層です。  
`twitter_service.py` が担当します。

### 2. 判断層

AI とルールベースの薄いオーケストレーションです。

### 3. スケジュール層

cron で定期実行する層です。

## ディレクトリ構成

```text
twitter-ai-agent/
├── README.md
├── tweet.sh
├── requirements.txt
├── pyproject.toml
├── config.json.sample
├── src/
│   ├── main.py
│   ├── commands/
│   │   ├── autopilot.py
│   │   ├── generate.py
│   │   ├── history.py
│   │   ├── post.py
│   │   └── score.py
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── article_service.py
│   │   ├── log_service.py
│   │   ├── scoring_service.py
│   │   └── twitter_service.py
│   ├── prompts/
│   │   ├── tweet_generation.txt
│   │   └── tweet_scoring.txt
│   └── utils/
│       ├── config.py
│       └── helpers.py
├── data/
│   ├── articles.json
│   ├── drafts.json
│   └── history.json
├── logs/
└── tests/
```

実際に AI CLI を使う場合は `gemini` / `claude` / `codex` などを指定し、必要なら `ai_command` で呼び出しを調整してください。  
例:

```json
{
  "default_ai_backend": "codex",
  "ai_command": "codex exec {prompt}"
}
```

## 使い方

### 1. generate

```bash
./tweet.sh generate --url "https://koteihi-zero.com/sample"
```

### 2. score

```bash
./tweet.sh score --input data/drafts.json
```

### 3. post

```bash
./tweet.sh post --text "固定費を減らしたいなら、最初に支払い方法を減らす方が早いです。" --dry-run
```

### 4. history

```bash
./tweet.sh history
./tweet.sh history --json
```

### 5. autopilot

まずは dry-run で確認します。

```bash
./tweet.sh autopilot --dry-run
```

出力例:

```text
[INFO] article selected: https://koteihi-zero.com/sample
[INFO] generated 5 candidates
[INFO] best score: 95
[DRY RUN] selected tweet:
固定費を減らしたいなら、最初に見直すべきものの話、難しいことはしていません。節約は気合いより設計です。毎月の固定費を先に削ると、家計管理はかなり楽になります。 まず1つ試すだけで十分です。https://koteihi-zero.com/sample
```

本番投稿:

```bash
./tweet.sh autopilot
```

## データファイル

### `data/articles.json`

投稿候補にしたい記事一覧を置きます。

```json
[
  {
    "url": "https://koteihi-zero.com/sample",
    "title": "固定費を減らしたいなら、最初に見直すべきもの",
    "summary": "節約は気合いより設計です。毎月の固定費を先に削ると、家計管理はかなり楽になります。"
  }
]
```

### `data/history.json`

投稿済み URL と本文を残します。  
同一 URL の重複投稿防止と、過去文面との簡易類似チェックに使います。

## cron 例

最初は必ず dry-run から始めてください。

```cron
0 9 * * * cd /Users/ken/twitter-ai-agent && ./tweet.sh autopilot --dry-run >> logs/cron.log 2>&1
0 18 * * * cd /Users/ken/twitter-ai-agent && ./tweet.sh autopilot >> logs/cron.log 2>&1
```

## 安全性

- `--dry-run` を先に実装
- 140 文字チェック
- `history.json` 自動生成
- 同一 URL の重複投稿防止
- 過去投稿との簡易類似チェック
- 外部 AI が使えない場合は fallback 候補生成に自動退避
- 実行ログを `logs/app.log` に保存

## 今回あえて広げていないもの

- DB
- task queue
- vector DB
- multi-agent
- web UI
- 複雑な分析基盤

最初から完璧な自律エージェントにせず、まずは `autopilot --dry-run` を安全に回すことを優先しています。

## 旧 repo との関係

- `twitter-cli-bot`: CLI foundation / execution layer
- `twitter-ai-agent`: AI-assisted posting engine / lightweight autonomous workflow

役割を分けることで、元 repo は安定した実行層として残しつつ、新 repo 側で判断ロジックを素直に進化させられます。
