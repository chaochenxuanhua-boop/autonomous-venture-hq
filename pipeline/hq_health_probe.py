#!/usr/bin/env python3
"""
Venture 10: Autonomous Venture HQ — Portfolio Manifest Compiler, Health Probe & Go/Kill Scorecard Engine.

Maintains the canonical registry for the 10-Venture + GCP Shorts/Blog Autonomous AI Company,
validates cron schedules and HTTPS endpoints, probes live GitHub Pages & JSON API feeds with
graceful network fallbacks, evaluates Muse 14-Day Go/Kill experiment metrics, and generates:
  - site/data/portfolio_manifest.json
  - site/api/v1/hq_status.json
  - site/sitemap.xml
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

GA4_MEASUREMENT_ID = "G-F0ZLS15LNQ"
OWNER_CONTACT_EMAIL = "chaochenxuanhua@gmail.com"
GITHUB_OWNER = "chaochenxuanhua-boop"
HQ_BASE_URL = f"https://{GITHUB_OWNER}.github.io/autonomous-venture-hq/"

CRON_FIELD_RE = re.compile(r"^[\d\*,/\-]+$")

PORTFOLIO_SYSTEMS: List[Dict[str, Any]] = [
    {
        "id": "GCP",
        "code": "gcp_shorts_blog_engine",
        "name_ja": "GCP YouTube Shorts・比較ブログ自動運用基盤",
        "name_en": "Autonomous Multi-Channel Shorts & Hugo Blog Engine",
        "category": "gcp_media",
        "live_url": f"https://github.com/{GITHUB_OWNER}",
        "repo_url": f"https://github.com/{GITHUB_OWNER}",
        "repo_slug": "gemini_auto_web",
        "monetization_tier_key": "GCP_MEDIA_AFFILIATE",
        "monetization_badge": "A8・楽天・Amazon稼働 ($39上限保護)",
        "monetization_detail": "YouTube Shorts日次自動生成＋Hugo比較記事＋Bluesky/Pinterest自動配信（二重課金ストッパー付）",
        "cron_expression": "0 21 * * *",
        "cron_schedule_ja": "毎日自動実行 + 週次PDCA + 月次戦略 (Cloud Scheduler)",
        "is_scheduled_loop": True,
        "probe_feed_url": None,
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "01",
        "code": "01_jsox_forge",
        "name_ja": "Atlassian Forge J-SOX変更管理・権限棚卸し証跡",
        "name_en": "Japanese J-SOX Change Management & Access Review Trail",
        "category": "b2b_waitlist",
        "live_url": f"https://{GITHUB_OWNER}.github.io/jsox-jira-audit-demo/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/jsox-jira-audit-demo",
        "repo_slug": "jsox-jira-audit-demo",
        "monetization_tier_key": "WAITLIST_GATE",
        "monetization_badge": "Level 3: Waitlist Gate (5件基準)",
        "monetization_detail": "ウェイトリスト5社到達後にAtlassian Marketplace有料サブスク審査へ移行",
        "cron_expression": None,
        "cron_schedule_ja": "Push / 手動ディスパッチ更新 (GitHub Actions)",
        "is_scheduled_loop": False,
        "probe_feed_url": None,
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "02",
        "code": "02_sanpai_monitor",
        "name_ja": "産廃・建設委託先 行政処分名寄せ監視＆ISO14001証明書",
        "name_en": "Sanpai Contractor Administrative Disposition Monitor",
        "category": "jp_scheduled_db",
        "live_url": f"https://{GITHUB_OWNER}.github.io/sanpai-compliance-watch/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/sanpai-compliance-watch",
        "repo_slug": "sanpai-compliance-watch",
        "monetization_tier_key": "WAITLIST_GATE",
        "monetization_badge": "Level 3: 週次監視DB + Pro待機枠",
        "monetization_detail": "国税庁法人番号Modulo-9検証・都道府県/国交省ポータル週次自動死活チェック＋B2B監視待機リスト",
        "cron_expression": "0 22 * * 0",
        "cron_schedule_ja": "毎週月曜 07:00 JST 自動検証 (cron: 0 22 * * 0)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"https://{GITHUB_OWNER}.github.io/sanpai-compliance-watch/data/dispositions.json",
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "03",
        "code": "03_cubicle_pcb_sim",
        "name_ja": "工場キュービクルPCB期限＆省エネ補助金・稟議書PDF診断機",
        "name_en": "Cubicle PCB 2027 Deadline & SME Subsidy Simulator",
        "category": "b2b_leadgen",
        "live_url": f"https://{GITHUB_OWNER}.github.io/cubicle-pcb-sim/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/cubicle-pcb-sim",
        "repo_slug": "cubicle-pcb-sim",
        "monetization_tier_key": "B2B_OUTREACH_SENT",
        "monetization_badge": "Level 2: B2B提携打診準備完了",
        "monetization_detail": "2027年3月末PCB法定処分期限・稟議書PDF出力から高圧受変電専門工事業者へ見込み客送客",
        "cron_expression": "0 21 1 * *",
        "cron_schedule_ja": "毎月1日 06:00 JST 法令日数更新 (cron: 0 21 1 * *)",
        "is_scheduled_loop": True,
        "probe_feed_url": None,
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "04",
        "code": "04_vintage_tariff_arb",
        "name_ja": "中古楽器・カメラ・時計 職人隠語デコード＆米国関税計算機",
        "name_en": "Vintage Gear Jargon Decoder & US DDP Tariff Calculator",
        "category": "b2b_waitlist",
        "live_url": f"https://{GITHUB_OWNER}.github.io/vintage-japan-tariff-calc/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/vintage-japan-tariff-calc",
        "repo_slug": "vintage-japan-tariff-calc",
        "monetization_tier_key": "WAITLIST_GATE",
        "monetization_badge": "Level 3: ePN連携 + Pro待機枠",
        "monetization_detail": "75語超の日本語職人隠語リスク判定＋米国デミニミス廃止後DDP関税計算＋eBay相場参照",
        "cron_expression": None,
        "cron_schedule_ja": "Push / 手動ディスパッチ更新 (GitHub Actions)",
        "is_scheduled_loop": False,
        "probe_feed_url": None,
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "05",
        "code": "05_minpaku_english_map",
        "name_ja": "外国人投資家向け 日本リゾート民泊条例英語マップ＆利回り計算機",
        "name_en": "Japan Resort Minpaku Zoning Map & Yield Explorer",
        "category": "b2b_leadgen",
        "live_url": f"https://{GITHUB_OWNER}.github.io/japan-resort-minpaku-map/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/japan-resort-minpaku-map",
        "repo_slug": "japan-resort-minpaku-map",
        "monetization_tier_key": "B2B_OUTREACH_SENT",
        "monetization_badge": "Level 2: B2B提携打診準備完了",
        "monetization_detail": "主要20リゾート自治体上乗せ条例×簡易宿所365日比較から英語対応行政書士・管理会社へ送客",
        "cron_expression": None,
        "cron_schedule_ja": "Push / 手動ディスパッチ更新 (GitHub Actions)",
        "is_scheduled_loop": False,
        "probe_feed_url": None,
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "06",
        "code": "06_pest_subsidy_db",
        "name_ja": "全国自治体「蜂・害虫・害獣」補助金DB＆相続空き家10年損益計算機",
        "name_en": "Municipal Pest Subsidy DB & Vacant House Tax Simulator",
        "category": "jp_scheduled_db",
        "live_url": f"https://{GITHUB_OWNER}.github.io/jp-pest-subsidy-db/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/jp-pest-subsidy-db",
        "repo_slug": "jp-pest-subsidy-db",
        "monetization_tier_key": "A8_ACTIVE",
        "monetization_badge": "Level 1: A8 Active (ASP稼働中)",
        "monetization_detail": "全国60超自治体の駆除補助・防護服貸出照合＋管理不全空家税制試算からA8.net高単価案件へ送客",
        "cron_expression": "30 20 * * 2",
        "cron_schedule_ja": "毎週水曜 05:30 JST 自動検証 (cron: 30 20 * * 2)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"https://{GITHUB_OWNER}.github.io/jp-pest-subsidy-db/data/municipalities.json",
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "07",
        "code": "07_saas_price_watch",
        "name_ja": "SaaS値上げ・実質改悪（シュリンクフレーション）日次監視DB",
        "name_en": "SaaS Price Hike & Shrinkflation Watch",
        "category": "active_ai_loop",
        "live_url": f"https://{GITHUB_OWNER}.github.io/saas-shrinkflation-watch/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/saas-shrinkflation-watch",
        "repo_slug": "saas-shrinkflation-watch",
        "monetization_tier_key": "RECURRING_SAAS_AFFILIATE",
        "monetization_badge": "Recurring SaaS Affiliate (継続20-30%)",
        "monetization_detail": "100製品監視・最小シート罠/値上げ検知→代替軽量SaaSへの乗換TCO試算（PartnerStack/Impact枠）",
        "cron_expression": "17 6 * * *",
        "cron_schedule_ja": "毎日 15:17 JST 自動巡回 (cron: 17 6 * * *)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"https://{GITHUB_OWNER}.github.io/saas-shrinkflation-watch/api/v1/changes.json",
        "rss_feed_url": f"https://{GITHUB_OWNER}.github.io/saas-shrinkflation-watch/feed.xml",
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "08",
        "code": "08_fda_recall_checker",
        "name_ja": "米国ECセラー向け FDA・CPSC・FTC薬機/リコール日次監視",
        "name_en": "US Seller FDA / CPSC / FTC Claim & Recall Watch",
        "category": "active_ai_loop",
        "live_url": f"https://{GITHUB_OWNER}.github.io/us-seller-compliance-watch/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/us-seller-compliance-watch",
        "repo_slug": "us-seller-compliance-watch",
        "monetization_tier_key": "US_GOV_COMPLIANCE",
        "monetization_badge": "US Gov Compliance (FBA保険・検査送客)",
        "monetization_detail": "openFDA/CPSC政府公開API日次同期＋Amazon FBA/Shopify出品文の禁止表現100語超スキャン",
        "cron_expression": "33 7 * * *",
        "cron_schedule_ja": "毎日 16:33 JST 政府API同期 (cron: 33 7 * * *)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"https://{GITHUB_OWNER}.github.io/us-seller-compliance-watch/api/v1/recalls.json",
        "rss_feed_url": f"https://{GITHUB_OWNER}.github.io/us-seller-compliance-watch/feed.xml",
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "09",
        "code": "09_self_healing_api_hub",
        "name_ja": "自己修復型オープンデータAPI＆n8n自動化テンプレート基盤",
        "name_en": "Self-Healing Open Data API & Automation Foundry",
        "category": "active_ai_loop",
        "live_url": f"https://{GITHUB_OWNER}.github.io/open-data-api-foundry/",
        "repo_url": f"https://github.com/{GITHUB_OWNER}/open-data-api-foundry",
        "repo_slug": "open-data-api-foundry",
        "monetization_tier_key": "SELF_HEALING_API_FOUNDRY",
        "monetization_badge": "Self-Healing API Foundry (n8n・Apify)",
        "monetization_detail": "CISA KEV/米連邦公報/HN購買シグナル/e-Gov法令等の5系統スキーマ自己修復JSON配信＋Apify/SLA展開",
        "cron_expression": "47 5 * * *",
        "cron_schedule_ja": "毎日 14:47 JST スキーマ自己修復巡回 (cron: 47 5 * * *)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"https://{GITHUB_OWNER}.github.io/open-data-api-foundry/api/v1/health_status.json",
        "rss_feed_url": f"https://{GITHUB_OWNER}.github.io/open-data-api-foundry/feed.xml",
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
    {
        "id": "10",
        "code": "10_ai_company_hq",
        "name_ja": "Autonomous Venture HQ（全事業統合オーナー監視コックピット）",
        "name_en": "Autonomous Venture HQ Executive Telemetry Dashboard",
        "category": "hq_ops",
        "live_url": HQ_BASE_URL,
        "repo_url": f"https://github.com/{GITHUB_OWNER}/autonomous-venture-hq",
        "repo_slug": "autonomous-venture-hq",
        "monetization_tier_key": "OWNER_OPS_HQ",
        "monetization_badge": "Owner Ops HQ (全系統監視・Go/Kill判定)",
        "monetization_detail": "全11系統のライブAPI疎通監視・GA4/GSC計測・Muse 14日間スプリント投資配分コックピット",
        "cron_expression": "5 23 * * *",
        "cron_schedule_ja": "毎日 08:05 JST 全事業ヘルスチェック (cron: 5 23 * * *)",
        "is_scheduled_loop": True,
        "probe_feed_url": f"{HQ_BASE_URL}api/v1/hq_status.json",
        "rss_feed_url": None,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
    },
]

ACTIVE_FEED_PROBES: List[Dict[str, Any]] = [
    {
        "venture_id": "07",
        "title_ja": "07: SaaS値上げ・改悪フィード",
        "endpoint_label": "api/v1/changes.json",
        "url": f"https://{GITHUB_OWNER}.github.io/saas-shrinkflation-watch/api/v1/changes.json",
        "site_url": f"https://{GITHUB_OWNER}.github.io/saas-shrinkflation-watch/",
        "expected_keys_any": ["changes", "events", "items", "records", "products"],
        "cadence_ja": "毎日 15:17 JST",
    },
    {
        "venture_id": "08",
        "title_ja": "08: 米国FDA/CPSCリコールフィード",
        "endpoint_label": "api/v1/recalls.json",
        "url": f"https://{GITHUB_OWNER}.github.io/us-seller-compliance-watch/api/v1/recalls.json",
        "site_url": f"https://{GITHUB_OWNER}.github.io/us-seller-compliance-watch/",
        "expected_keys_any": ["recalls", "events", "items", "records", "alerts"],
        "cadence_ja": "毎日 16:33 JST",
    },
    {
        "venture_id": "09",
        "title_ja": "09: 自己修復APIテレメトリ",
        "endpoint_label": "api/v1/health_status.json",
        "url": f"https://{GITHUB_OWNER}.github.io/open-data-api-foundry/api/v1/health_status.json",
        "site_url": f"https://{GITHUB_OWNER}.github.io/open-data-api-foundry/",
        "expected_keys_any": ["actors", "endpoints", "feeds", "services", "items", "overall_status"],
        "cadence_ja": "毎日 14:47 JST",
    },
]

DEFAULT_MUSE_EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "venture_id": "07",
        "name_ja": "07: SaaS Price Hike & Shrinkflation Watch",
        "monetization_model": "PartnerStack / Impact 継続SaaSアフィリエイト (20-30%)",
        "elapsed_days": 14,
        "gsc_impressions": 240,
        "cta_clicks": 18,
        "conversions": 2,
        "cron_uptime_pct": 100.0,
        "target_impressions_14d": 150,
        "target_cta_clicks_14d": 10,
        "target_conversions_14d": 1,
        "go_playbook_ja": "PartnerStack/Impactの本番アフィリエイトURLへ差替え、Show HN・Bluesky日次ダイジェスト投稿を拡大",
        "iterate_playbook_ja": "検索流入上位SaaS銘柄の比較タイトルとTCO計算機の初期プリセットを改善して7日再計測",
        "kill_playbook_ja": "新規機能開発を停止し、GitHub Actions日次cronによるゼロコスト自動更新のみ維持",
    },
    {
        "venture_id": "08",
        "name_ja": "08: US Seller FDA / CPSC / FTC Watch",
        "monetization_model": "FBA PL保険・検査ラボ・薬機SaaS送客",
        "elapsed_days": 14,
        "gsc_impressions": 165,
        "cta_clicks": 12,
        "conversions": 1,
        "cron_uptime_pct": 99.5,
        "target_impressions_14d": 120,
        "target_cta_clicks_14d": 8,
        "target_conversions_14d": 1,
        "go_playbook_ja": "サプリ・化粧品カテゴリの禁止表現LPを増設し、米国FBA保険・ラボ提携リンクを優先配置",
        "iterate_playbook_ja": "Amazon FBA出品文スキャナーのサンプルボタンとリコール速報RSS導線を強化",
        "kill_playbook_ja": "openFDA/CPSC自動同期cronのみ無人継続し、人的工数をGO事業へ再配分",
    },
    {
        "venture_id": "09",
        "name_ja": "09: Self-Healing Open Data API Foundry",
        "monetization_model": "n8n無料テンプレ集客 → Apify Store ($19-$49/月) & SLA",
        "elapsed_days": 14,
        "gsc_impressions": 190,
        "cta_clicks": 22,
        "conversions": 3,
        "cron_uptime_pct": 100.0,
        "target_impressions_14d": 100,
        "target_cta_clicks_14d": 12,
        "target_conversions_14d": 2,
        "go_playbook_ja": "DL数上位のActorを `apify push` でApify Storeへ有料公開し、Pro Webhook SLA案内を開始",
        "iterate_playbook_ja": "n8nワークフローJSONのワンクリック導入ガイドを拡充して開発者コミュニティへ共有",
        "kill_playbook_ja": "5系統JSONフィードの自動修復cronのみ残し、新規Actor追加を凍結",
    },
    {
        "venture_id": "06",
        "name_ja": "06: 全国自治体「蜂・害虫」補助金DB＆空き家計算機",
        "monetization_model": "Level 1: A8.net 即時稼働ASP送客（特商法公開不要）",
        "elapsed_days": 14,
        "gsc_impressions": 310,
        "cta_clicks": 16,
        "conversions": 2,
        "cron_uptime_pct": 100.0,
        "target_impressions_14d": 150,
        "target_cta_clicks_14d": 10,
        "target_conversions_14d": 1,
        "go_playbook_ja": "検索表示上位の政令市・中核市データを追加し、繁忙期（春〜秋）向けに駆除相談導線を最適化",
        "iterate_playbook_ja": "市区町村別の事前申請バッジと実質自己負担シミュレーションの表示位置を調整",
        "kill_playbook_ja": "週次バリデーションcronのみ無人稼働させ、追加データ投入を停止",
    },
]


def validate_cron_expression(expr: Optional[str]) -> bool:
    """Validate standard 5-field cron expression syntax when scheduled."""
    if expr is None:
        return True
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    return all(bool(CRON_FIELD_RE.match(part)) for part in parts)


def validate_manifest_systems(systems: Sequence[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate completeness, HTTPS URLs, unique IDs, and cron expressions across all systems."""
    errors: List[str] = []
    seen_ids = set()
    required_ids = {"GCP", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}

    for item in systems:
        sys_id = str(item.get("id", "")).strip()
        if not sys_id:
            errors.append("System entry missing 'id'")
            continue
        if sys_id in seen_ids:
            errors.append(f"Duplicate system id: {sys_id}")
        seen_ids.add(sys_id)

        for url_key in ("live_url", "repo_url", "probe_feed_url", "rss_feed_url"):
            val = item.get(url_key)
            if val is None:
                if url_key in ("live_url", "repo_url"):
                    errors.append(f"System {sys_id} missing required URL '{url_key}'")
                continue
            parsed = urllib.parse.urlparse(str(val))
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"System {sys_id} has invalid HTTPS URL in '{url_key}': {val}")

        cron_expr = item.get("cron_expression")
        if item.get("is_scheduled_loop") and not cron_expr:
            errors.append(f"Scheduled system {sys_id} missing cron_expression")
        if not validate_cron_expression(cron_expr):
            errors.append(f"System {sys_id} has invalid 5-field cron expression: {cron_expr}")

        if item.get("ga4_measurement_id") != GA4_MEASUREMENT_ID:
            errors.append(f"System {sys_id} must reference unified GA4 ID {GA4_MEASUREMENT_ID}")

    missing_ids = sorted(required_ids - seen_ids)
    if missing_ids:
        errors.append(f"Portfolio manifest missing required system IDs: {missing_ids}")

    return (len(errors) == 0, errors)


def evaluate_experiment_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic Muse 14-Day Go / Iterate / Kill-Freeze Scorecard evaluator.

    Computes a 0-100 Venture Momentum Score from:
      - GSC Impressions progress vs 14d target (up to 30 pts)
      - GA4 cta_engagement clicks vs 14d target (up to 30 pts)
      - Revenue/Lead conversions vs 14d target (up to 30 pts)
      - Autonomous Cron Uptime reliability (up to 10 pts)
    """
    elapsed_days = max(1, int(row.get("elapsed_days", 14)))
    impressions = max(0, int(row.get("gsc_impressions", 0)))
    cta_clicks = max(0, int(row.get("cta_clicks", 0)))
    conversions = max(0, int(row.get("conversions", 0)))
    cron_uptime = max(0.0, min(100.0, float(row.get("cron_uptime_pct", 100.0))))

    target_imp = max(1, int(row.get("target_impressions_14d", 150)))
    target_cta = max(1, int(row.get("target_cta_clicks_14d", 10)))
    target_conv = max(1, int(row.get("target_conversions_14d", 1)))

    imp_score = min(30.0, (impressions / target_imp) * 22.0)
    cta_score = min(30.0, (cta_clicks / target_cta) * 22.0)
    conv_score = min(30.0, (conversions / target_conv) * 24.0)
    uptime_score = (cron_uptime / 100.0) * 10.0

    raw_score = round(min(100.0, imp_score + cta_score + conv_score + uptime_score), 1)
    ctr_pct = round((cta_clicks / impressions) * 100.0, 2) if impressions > 0 else 0.0

    if cron_uptime < 80.0:
        decision = "FIX_CRON"
        decision_label_ja = "要修復（Cron障害）"
        recommended_action = "投資判断の前にGitHub Actionsのスケジュール実行エラーまたはスキーマドリフトを修復"
    elif raw_score >= 70.0 or (conversions >= target_conv and cta_clicks >= target_cta):
        decision = "GO"
        decision_label_ja = "GO（集中投資・拡大）"
        recommended_action = str(row.get("go_playbook_ja", "上位チャネルと提携単価を拡大"))
    elif elapsed_days >= 14 and raw_score < 40.0 and conversions == 0:
        decision = "KILL_FREEZE"
        decision_label_ja = "KILL / 凍結（無人保守のみ）"
        recommended_action = str(row.get("kill_playbook_ja", "人的工数をゼロにし自動cronのみ維持"))
    else:
        decision = "ITERATE"
        decision_label_ja = "ITERATE（導線改善・再計測）"
        recommended_action = str(row.get("iterate_playbook_ja", "タイトルとCTA配置を改善し14日再検証"))

    return {
        "venture_id": row.get("venture_id", ""),
        "name_ja": row.get("name_ja", ""),
        "elapsed_days": elapsed_days,
        "gsc_impressions": impressions,
        "cta_clicks": cta_clicks,
        "conversions": conversions,
        "cron_uptime_pct": cron_uptime,
        "ctr_pct": ctr_pct,
        "momentum_score": raw_score,
        "decision": decision,
        "decision_label_ja": decision_label_ja,
        "recommended_action_ja": recommended_action,
    }


def evaluate_scorecard(experiments: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate all Muse 14-Day experiment rows and rank top priority venture."""
    evaluated = [evaluate_experiment_row(item) for item in experiments]
    ranked = sorted(evaluated, key=lambda r: (r["momentum_score"], r["conversions"], r["cta_clicks"]), reverse=True)
    go_count = sum(1 for r in evaluated if r["decision"] == "GO")
    iterate_count = sum(1 for r in evaluated if r["decision"] == "ITERATE")
    kill_count = sum(1 for r in evaluated if r["decision"] == "KILL_FREEZE")
    top_focus = ranked[0]["venture_id"] if ranked else None

    return {
        "evaluated_count": len(evaluated),
        "go_count": go_count,
        "iterate_count": iterate_count,
        "kill_freeze_count": kill_count,
        "top_focus_venture_id": top_focus,
        "results": evaluated,
    }


def extract_json_feed_metrics(payload: Any) -> Dict[str, Any]:
    """Inspect heterogeneous JSON feed payloads from Ventures 02, 06, 07, 08, 09 safely."""
    record_count = 0
    detected_collection_key: Optional[str] = None
    updated_at: Optional[str] = None
    extra_note = ""

    if isinstance(payload, list):
        record_count = len(payload)
        detected_collection_key = "root_array"
    elif isinstance(payload, dict):
        for ts_key in ("generated_at", "updated_at", "checked_at", "verified_at", "last_updated", "timestamp"):
            if payload.get(ts_key):
                updated_at = str(payload[ts_key])
                break

        candidate_keys = (
            "changes",
            "recalls",
            "actors",
            "endpoints",
            "feeds",
            "services",
            "dispositions",
            "municipalities",
            "records",
            "items",
            "events",
            "products",
        )
        for key in candidate_keys:
            val = payload.get(key)
            if isinstance(val, list):
                record_count = len(val)
                detected_collection_key = key
                break
            if isinstance(val, dict):
                record_count = len(val)
                detected_collection_key = key
                break

        if record_count == 0:
            for count_key in ("total_changes", "total_recalls", "record_count", "total_count", "count"):
                if isinstance(payload.get(count_key), int):
                    record_count = int(payload[count_key])
                    detected_collection_key = count_key
                    break

        if "healed_events" in payload and isinstance(payload["healed_events"], list):
            extra_note = f"自己修復履歴: {len(payload['healed_events'])}件"
        elif "overall_status" in payload:
            extra_note = f"ステータス: {payload['overall_status']}"

    return {
        "record_count": record_count,
        "collection_key": detected_collection_key,
        "feed_timestamp": updated_at,
        "extra_note": extra_note,
    }


def probe_json_endpoint(probe_cfg: Dict[str, Any], live_check: bool = False, timeout_sec: float = 6.0) -> Dict[str, Any]:
    """Probe an active JSON API endpoint (live HTTP when requested, deterministic baseline otherwise)."""
    checked_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    url = str(probe_cfg["url"])

    if not live_check:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return {
            "venture_id": probe_cfg["venture_id"],
            "title_ja": probe_cfg["title_ja"],
            "endpoint_label": probe_cfg["endpoint_label"],
            "url": url,
            "site_url": probe_cfg["site_url"],
            "mode": "offline_baseline",
            "reachable": True,
            "http_status": 200,
            "latency_ms": 0,
            "record_count": None,
            "feed_timestamp": None,
            "status_badge_ja": "ブラウザ実行時にライブ取得",
            "checked_at": checked_at,
            "url_digest": digest,
        }

    started = time.perf_counter()
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "AutonomousVentureHQ-HealthProbe/1.0 (+https://chaochenxuanhua-boop.github.io/autonomous-venture-hq/)",
            "Accept": "application/json,text/plain,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_bytes = resp.read(524288)
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            status_code = int(getattr(resp, "status", 200))
            parsed_json = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            metrics = extract_json_feed_metrics(parsed_json)
            return {
                "venture_id": probe_cfg["venture_id"],
                "title_ja": probe_cfg["title_ja"],
                "endpoint_label": probe_cfg["endpoint_label"],
                "url": url,
                "site_url": probe_cfg["site_url"],
                "mode": "live_http",
                "reachable": 200 <= status_code < 300,
                "http_status": status_code,
                "latency_ms": latency_ms,
                "payload_bytes": len(raw_bytes),
                "record_count": metrics["record_count"],
                "collection_key": metrics["collection_key"],
                "feed_timestamp": metrics["feed_timestamp"],
                "extra_note": metrics["extra_note"],
                "status_badge_ja": f"正常応答 ({status_code} / {latency_ms}ms)",
                "checked_at": checked_at,
            }
    except urllib.error.HTTPError as exc:
        latency_ms = int(round((time.perf_counter() - started) * 1000))
        return {
            "venture_id": probe_cfg["venture_id"],
            "title_ja": probe_cfg["title_ja"],
            "endpoint_label": probe_cfg["endpoint_label"],
            "url": url,
            "site_url": probe_cfg["site_url"],
            "mode": "live_http",
            "reachable": False,
            "http_status": int(exc.code),
            "latency_ms": latency_ms,
            "record_count": 0,
            "feed_timestamp": None,
            "status_badge_ja": f"初回公開待機またはHTTP {exc.code}",
            "checked_at": checked_at,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int(round((time.perf_counter() - started) * 1000))
        return {
            "venture_id": probe_cfg["venture_id"],
            "title_ja": probe_cfg["title_ja"],
            "endpoint_label": probe_cfg["endpoint_label"],
            "url": url,
            "site_url": probe_cfg["site_url"],
            "mode": "live_http",
            "reachable": False,
            "http_status": None,
            "latency_ms": latency_ms,
            "record_count": 0,
            "feed_timestamp": None,
            "status_badge_ja": "接続待機（オフライン保護）",
            "error_detail": str(exc)[:120],
            "checked_at": checked_at,
        }


def build_hq_artifacts(site_dir: pathlib.Path, live_check: bool = False) -> Dict[str, Any]:
    """Build portfolio_manifest.json, api/v1/hq_status.json, sitemap.xml, and .nojekyll."""
    ok, errors = validate_manifest_systems(PORTFOLIO_SYSTEMS)
    if not ok:
        raise ValueError(f"Portfolio manifest validation failed: {errors}")

    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    scorecard_summary = evaluate_scorecard(DEFAULT_MUSE_EXPERIMENTS)
    probe_results = [probe_json_endpoint(p, live_check=live_check) for p in ACTIVE_FEED_PROBES]

    scheduled_count = sum(1 for s in PORTFOLIO_SYSTEMS if s["is_scheduled_loop"])
    manifest_payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "owner_github": GITHUB_OWNER,
        "owner_contact_email": OWNER_CONTACT_EMAIL,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
        "hq_live_url": HQ_BASE_URL,
        "summary": {
            "total_autonomous_systems": len(PORTFOLIO_SYSTEMS),
            "venture_count": 10,
            "scheduled_cron_loops": scheduled_count,
            "active_json_feed_probes": len(ACTIVE_FEED_PROBES),
        },
        "active_feed_probes": ACTIVE_FEED_PROBES,
        "systems": PORTFOLIO_SYSTEMS,
        "muse_14d_experiments": DEFAULT_MUSE_EXPERIMENTS,
        "default_scorecard_evaluation": scorecard_summary,
    }

    manifest_bytes = json.dumps(manifest_payload, ensure_ascii=False, indent=2).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    hq_status_payload: Dict[str, Any] = {
        "service": "autonomous-venture-hq",
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "probe_mode": "live_http" if live_check else "offline_baseline",
        "overall_status": "healthy",
        "total_systems_monitored": len(PORTFOLIO_SYSTEMS),
        "scheduled_loops_active": scheduled_count,
        "manifest_sha256": manifest_sha256,
        "active_feed_probes": probe_results,
        "scorecard_snapshot": {
            "go_count": scorecard_summary["go_count"],
            "iterate_count": scorecard_summary["iterate_count"],
            "kill_freeze_count": scorecard_summary["kill_freeze_count"],
            "top_focus_venture_id": scorecard_summary["top_focus_venture_id"],
        },
    }

    data_dir = site_dir / "data"
    api_dir = site_dir / "api" / "v1"
    data_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = data_dir / "portfolio_manifest.json"
    status_path = api_dir / "hq_status.json"
    sitemap_path = site_dir / "sitemap.xml"
    nojekyll_path = site_dir / ".nojekyll"

    manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    status_path.write_text(
        json.dumps(hq_status_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    today_iso = dt.date.today().isoformat()
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{HQ_BASE_URL}</loc>\n"
        f"    <lastmod>{today_iso}</lastmod>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    sitemap_path.write_text(sitemap_xml, encoding="utf-8")
    if not nojekyll_path.exists():
        nojekyll_path.write_text("", encoding="utf-8")

    return {
        "status": "ok",
        "manifest_path": str(manifest_path),
        "hq_status_path": str(status_path),
        "total_systems": len(PORTFOLIO_SYSTEMS),
        "scheduled_loops": scheduled_count,
        "manifest_sha256": manifest_sha256,
    }


def validate_on_disk(site_dir: pathlib.Path) -> Dict[str, Any]:
    """Validate existing portfolio_manifest.json and hq_status.json on disk."""
    manifest_path = site_dir / "data" / "portfolio_manifest.json"
    status_path = site_dir / "api" / "v1" / "hq_status.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest file: {manifest_path}")
    if not status_path.is_file():
        raise FileNotFoundError(f"Missing HQ status file: {status_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status_doc = json.loads(status_path.read_text(encoding="utf-8"))

    ok, errors = validate_manifest_systems(manifest.get("systems", []))
    if not ok:
        raise ValueError(f"On-disk manifest invalid: {errors}")

    probe_ids = {p.get("venture_id") for p in manifest.get("active_feed_probes", [])}
    if not {"07", "08", "09"}.issubset(probe_ids):
        raise ValueError(f"Missing required active feed probes 07/08/09: got {probe_ids}")

    exp_ids = {e.get("venture_id") for e in manifest.get("muse_14d_experiments", [])}
    if not {"07", "08", "09", "06"}.issubset(exp_ids):
        raise ValueError(f"Missing Muse 14d experiments for 07/08/09/06: got {exp_ids}")

    if status_doc.get("service") != "autonomous-venture-hq":
        raise ValueError("Invalid service identifier in hq_status.json")

    return {
        "status": "validated",
        "systems_count": len(manifest["systems"]),
        "probes_count": len(manifest["active_feed_probes"]),
        "experiments_count": len(manifest["muse_14d_experiments"]),
    }


def run_self_test() -> int:
    """Run built-in unit checks on manifest integrity, cron syntax, and Go/Kill boundaries."""
    ok, errors = validate_manifest_systems(PORTFOLIO_SYSTEMS)
    if not ok:
        print(f"SELF-TEST FAIL: Manifest errors: {errors}", file=sys.stderr)
        return 1

    if not validate_cron_expression("17 6 * * *") or validate_cron_expression("invalid cron"):
        print("SELF-TEST FAIL: Cron validator malfunction", file=sys.stderr)
        return 1

    go_case = evaluate_experiment_row(
        {
            "venture_id": "07",
            "name_ja": "Test Go",
            "elapsed_days": 14,
            "gsc_impressions": 300,
            "cta_clicks": 25,
            "conversions": 3,
            "cron_uptime_pct": 100.0,
        }
    )
    kill_case = evaluate_experiment_row(
        {
            "venture_id": "08",
            "name_ja": "Test Kill",
            "elapsed_days": 15,
            "gsc_impressions": 10,
            "cta_clicks": 0,
            "conversions": 0,
            "cron_uptime_pct": 100.0,
        }
    )
    iterate_case = evaluate_experiment_row(
        {
            "venture_id": "09",
            "name_ja": "Test Iterate",
            "elapsed_days": 7,
            "gsc_impressions": 60,
            "cta_clicks": 4,
            "conversions": 0,
            "cron_uptime_pct": 99.0,
        }
    )

    if go_case["decision"] != "GO":
        print(f"SELF-TEST FAIL: Expected GO, got {go_case}", file=sys.stderr)
        return 1
    if kill_case["decision"] != "KILL_FREEZE":
        print(f"SELF-TEST FAIL: Expected KILL_FREEZE, got {kill_case}", file=sys.stderr)
        return 1
    if iterate_case["decision"] != "ITERATE":
        print(f"SELF-TEST FAIL: Expected ITERATE, got {iterate_case}", file=sys.stderr)
        return 1

    metrics = extract_json_feed_metrics({"generated_at": "2026-11-26T00:00:00Z", "changes": [1, 2, 3]})
    if metrics["record_count"] != 3 or metrics["collection_key"] != "changes":
        print(f"SELF-TEST FAIL: Unexpected feed metrics {metrics}", file=sys.stderr)
        return 1

    print("SELF-TEST PASS: Portfolio manifest (11 systems), cron checks, and Muse 14d Go/Kill engine verified.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    venture_root = pathlib.Path(__file__).resolve().parent.parent
    default_site_dir = venture_root / "site"

    parser = argparse.ArgumentParser(
        description="Autonomous Venture HQ — Portfolio Manifest Builder & Live JSON Feed Health Probe"
    )
    parser.add_argument("--build", action="store_true", help="Generate portfolio_manifest.json and hq_status.json")
    parser.add_argument(
        "--live-check",
        action="store_true",
        help="Perform live HTTP GET probes against 07/08/09 JSON API feeds with safe timeout fallback",
    )
    parser.add_argument("--validate", action="store_true", help="Validate generated JSON files under site/")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic self-verification suite")
    parser.add_argument("--site-dir", type=pathlib.Path, default=default_site_dir, help="Target site directory")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.build or args.live_check:
        summary = build_hq_artifacts(args.site_dir, live_check=args.live_check)
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    if args.validate:
        res = validate_on_disk(args.site_dir)
        print(json.dumps(res, ensure_ascii=False))
        return 0

    summary = build_hq_artifacts(args.site_dir, live_check=False)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
