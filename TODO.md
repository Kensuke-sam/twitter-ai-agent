# TODO

この repo はまず `Phase 1` と `autopilot --dry-run` を成立させる方針です。  
以下は後続で進める項目です。

## 次にやること

- `post` の本番運用確認
- `autopilot` 本番投稿時の retry と失敗ハンドリング強化
- `history` の重複検知をもう少し厳密にする
- `score --use-ai` の実運用調整
- 実 AI CLI ごとの `ai_command` テンプレート例を増やす

## Phase 2

- `history` 出力整形
- `score` の採点基準調整
- 過去投稿との簡易類似チェック改善

## Phase 3

- `autopilot` 本番投稿の監視
- cron 常用前提の運用手順
- 失敗時リトライ
- 記事選定ロジックの改善

## Phase 4

- `analyze` コマンド
- 過去投稿の傾向分析
- 伸びそうな文体の提案
