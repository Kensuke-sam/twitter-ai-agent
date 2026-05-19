# twitter-ai-agent

CLI-first AI-assisted posting engine for X / Twitter.

`twitter-cli-bot` をそのまま肥大化させるのではなく、投稿実行を担う CLI foundation は残したまま、その上に AI の判断層を 1 枚だけ足すための後継 repo です。

This repository focuses on a minimal working Phase 1: generate, dry-run, and publish tweets through a lightweight CLI-first AI workflow.
Phase 1 has been validated end-to-end with dry-run and live posting.

> **警告 — 使う前に必ず読んでください。** この repo は公式の X API ではなく、`twitter-cli`（[jackwener/twitter-cli](https://github.com/jackwener/twitter-cli)）経由の**非公式なブラウザ Cookie 認証**で X / Twitter に投稿します。さらに `autopilot` による自律投稿・cron 定期実行を備えます。これらは X の利用規約・自動化ルールに違反する可能性があり、アカウントが**レート制限・凍結・永久 BAN** される恐れがあります。本ツールは無保証で、技術検証・個人利用を目的に現状のまま提供されます。使用前に[免責事項](#免責事項)を必ず確認してください。

---

## 免責事項

この repo は公式の X API を使用していません。投稿の実行層は `twitter_service.py` 経由で `twitter-cli`（[jackwener/twitter-cli](https://github.com/jackwener/twitter-cli)）を呼び出し、`twitter-cli` は**ブラウザのセッション Cookie** を使ってログイン済みブラウザと同じように X / Twitter へアクセスします。

**利用規約について。** 公式 API 以外の自動的な手段による X へのアクセス（自動読み取り・スクレイピング・自動投稿）は、[X の利用規約](https://x.com/ja/tos)、[X Developer Agreement and Policy](https://developer.x.com/en/developer-terms/agreement-and-policy)、[X の自動化に関するルール](https://help.x.com/ja/rules-and-policies/x-automation)に違反する可能性があります。

**アカウントのリスク。** 本 repo の中心機能である `autopilot`（記事選定から候補生成・採点・投稿までの自律ワークフロー）と cron による定期投稿は、X のスパム対策・自動化ルールが制限している自動・大量の操作にあたります。これらを使うとアカウントが**レート制限・凍結・永久 BAN** される可能性があり、X は予告なく措置を取ることがあります。また非公式の Cookie ベースの仕組みは、X の内部仕様変更により予告なく動作しなくなる可能性があります。

**利用者の責任。**

- **自分自身が所有するアカウントでのみ**使用してください。管理権限のないアカウントには絶対に使用しないでください。
- **投稿された内容（AI が生成・採点したテキストを含む）の責任はすべて利用者にあります。** 必ず `--dry-run` で内容を確認し、`autopilot` の本番実行や cron 連携は特に慎重に扱ってください。
- スパム、大量フォロー、大量エンゲージメント、その他 X が禁止する行為に使用しないでください。
- 記事から投稿候補を生成する際は、引用元の著作権を尊重し、本文の丸写しを避け、要約と出典明記を行ってください。

**無保証。** 本ソフトウェアは「現状のまま」提供され、いかなる保証もありません。作者は、本ツールの使用により生じたアカウント凍結・データ損失・その他一切の損害について**責任を負いません**。**自己責任でご利用ください。** 規約に準拠した方法が必要な場合は、[公式の X API](https://developer.x.com/en/docs/x-api) を使用してください。

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

本番投稿の運用強化、高度なスコアリング、分析機能は [TODO.md](./TODO.md) で管理しています。

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

Known setup note: `twitter-cli` authentication depends on the browser profile that holds the active X session. If posting fails, verify which browser profile contains the current X login cookies.

## Dry-run first

最初はこの順だけで十分です。

```bash
./tweet.sh post --text "test post" --dry-run
./tweet.sh post --text "test post"
./tweet.sh autopilot --dry-run
```

実際に `post` を叩くのは `--dry-run` を確認してからにしてください。

## Commands

- `./tweet.sh generate --url "https://night-sky.example.com/winter-triangle"`
- `./tweet.sh score --input data/drafts.json`
- `./tweet.sh post --text "..." --dry-run`
- `./tweet.sh history`
- `./tweet.sh autopilot --dry-run`

For a short public demo clip, use the sequence in [docs/demo-script.md](./docs/demo-script.md).

## Not yet implemented

未実装または運用前提でまだ固めていないものは [TODO.md](./TODO.md) に分離しています。

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
./tweet.sh generate --url "https://night-sky.example.com/winter-triangle"
```

### 2. score

```bash
./tweet.sh score --input data/drafts.json
```

### 3. post

```bash
./tweet.sh post --text "星座に詳しくなくても、冬の大三角だけ覚えると夜空を見るハードルが一気に下がります。" --dry-run
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
[INFO] article selected: https://night-sky.example.com/winter-triangle
[INFO] generated 5 candidates
[INFO] best score: 95
[DRY RUN] selected tweet:
冬の大三角を見つけると夜空が少し楽しくなるの話、難しいことはしていません。明るい3つの星を先に見つけるだけで、星座に詳しくなくても冬の夜空を追いやすくなります。 まず1つ試すだけで十分です。https://night-sky.example.com/winter-triangle
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
    "url": "https://night-sky.example.com/winter-triangle",
    "title": "冬の大三角を見つけると夜空が少し楽しくなる",
    "summary": "明るい3つの星を先に見つけるだけで、星座に詳しくなくても冬の夜空を追いやすくなります。"
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

- [`twitter-cli-bot`](https://github.com/Kensuke-sam/twitter-cli-bot): CLI foundation / execution layer
- `twitter-ai-agent`: AI-assisted posting engine / lightweight autonomous workflow

役割を分けることで、元 repo は安定した実行層として残しつつ、新 repo 側で判断ロジックを素直に進化させられます。
