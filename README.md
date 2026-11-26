# Venture 10: Autonomous Venture HQ（全事業統合オーナー監視コックピット）

**公開先リポジトリ**: `chaochenxuanhua-boop/autonomous-venture-hq`  
**公開URL**: `https://chaochenxuanhua-boop.github.io/autonomous-venture-hq/`

GCP YouTube Shorts・比較ブログ自動運用基盤（`gemini_auto_web`）および独立Web事業ポートフォリオ全10事業（`01`〜`10`）の公開URL、マネタイズ区分、自動Cronスケジュール、公開JSON API死活状態、および **Muse 14日間スプリント Go / Kill 投資判定スコアカード** を1画面で俯瞰するオーナー専用テレメトリダッシュボードです。

---

## 主な機能

1. **Active AI JSONフィード ライブ疎通監視（07・08・09）**
   - ブラウザから直接 `fetch` リクエストを実行し、以下の3つの日次自動更新JSONフィードのHTTP応答コード、レイテンシ（ms）、収録データ件数を即時に検証します：
     - `07`: `saas-shrinkflation-watch/api/v1/changes.json`（SaaS値上げ・シュリンクフレーション監視）
     - `08`: `us-seller-compliance-watch/api/v1/recalls.json`（米国FDA/CPSCリコール・出品規制監視）
     - `09`: `open-data-api-foundry/api/v1/health_status.json`（自己修復オープンデータAPIテレメトリ）
2. **全11系統マスター稼働レジストリ（GCP + Ventures `01`〜`10`）**
   - A8.net即時稼働（Level 1）、B2B専門業者送客（Level 2）、ウェイトリスト検証（Level 3）、継続SaaSアフィリエイト、米国政府コンプライアンス、自己修復API基盤の全ステータスとスケジュールを一覧化。
3. **Muse 14日間スプリント Go / Kill スコアカード計算機**
   - `07`・`08`・`09`・`06` のGSC表示回数、GA4 `cta_engagement` クリック数、成約・提携反応数、Cron稼働率（%）を入力すると、モメンタムスコア（0〜100点）と **`GO（集中投資）` / `ITERATE（改善継続）` / `KILL・凍結（無料Cronのみ無人維持）`** を自動判定し、`localStorage` 保存・JSON出力・A4経営レポート印刷・運営事務局メモ送信に対応します。

---

## ローカル実行・検証コマンド

```powershell
# パイプライン自己診断テスト・マニフェスト生成
python ventures/10_ai_company_hq/pipeline/hq_health_probe.py --self-test
python ventures/10_ai_company_hq/pipeline/hq_health_probe.py --build

# ユニットテスト実行
python -m unittest discover -s ventures/10_ai_company_hq/tests -p "test_*.py" -v

# ローカルブラウザでプレビュー起動
.\ventures\deploy_venture.ps1 -Venture 10 -LocalPreview
```
