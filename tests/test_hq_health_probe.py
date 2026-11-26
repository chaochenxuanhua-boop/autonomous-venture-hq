#!/usr/bin/env python3
"""Unit test suite for Venture 10: Autonomous Venture HQ (`hq_health_probe.py` & static UI)."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

VENTURE_ROOT = pathlib.Path(__file__).resolve().parent.parent
PIPELINE_PATH = VENTURE_ROOT / "pipeline" / "hq_health_probe.py"
SITE_DIR = VENTURE_ROOT / "site"
WORKFLOW_PATH = VENTURE_ROOT / ".github" / "workflows" / "deploy.yml"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
TEXT_SUFFIXES = {".py", ".html", ".css", ".js", ".json", ".yml", ".yaml", ".md", ".xml"}


def _load_hq_module():
    spec = importlib.util.spec_from_file_location("hq_health_probe", str(PIPELINE_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {PIPELINE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hq_health_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


hq_mod = _load_hq_module()


class TestAutonomousVentureHq(unittest.TestCase):
    """Verify manifest registry, Muse 14-Day Go/Kill math, workflow safety, and static cleanliness."""

    def test_manifest_covers_gcp_and_all_ten_ventures(self) -> None:
        ok, errors = hq_mod.validate_manifest_systems(hq_mod.PORTFOLIO_SYSTEMS)
        self.assertTrue(ok, f"Manifest validation failed: {errors}")
        ids = {item["id"] for item in hq_mod.PORTFOLIO_SYSTEMS}
        expected = {"GCP", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10"}
        self.assertEqual(ids, expected)

    def test_active_json_feed_probes_target_07_08_09(self) -> None:
        by_id = {p["venture_id"]: p for p in hq_mod.ACTIVE_FEED_PROBES}
        self.assertEqual(set(by_id.keys()), {"07", "08", "09"})
        self.assertTrue(by_id["07"]["url"].endswith("/saas-shrinkflation-watch/api/v1/changes.json"))
        self.assertTrue(by_id["08"]["url"].endswith("/us-seller-compliance-watch/api/v1/recalls.json"))
        self.assertTrue(by_id["09"]["url"].endswith("/open-data-api-foundry/api/v1/health_status.json"))

    def test_muse_14d_go_kill_scorecard_boundaries(self) -> None:
        go_res = hq_mod.evaluate_experiment_row(
            {
                "venture_id": "07",
                "name_ja": "SaaS Watch",
                "elapsed_days": 14,
                "gsc_impressions": 260,
                "cta_clicks": 20,
                "conversions": 2,
                "cron_uptime_pct": 100.0,
            }
        )
        self.assertEqual(go_res["decision"], "GO")
        self.assertGreaterEqual(go_res["momentum_score"], 70.0)

        kill_res = hq_mod.evaluate_experiment_row(
            {
                "venture_id": "06",
                "name_ja": "Low Signal Case",
                "elapsed_days": 15,
                "gsc_impressions": 12,
                "cta_clicks": 1,
                "conversions": 0,
                "cron_uptime_pct": 100.0,
            }
        )
        self.assertEqual(kill_res["decision"], "KILL_FREEZE")
        self.assertLess(kill_res["momentum_score"], 40.0)

        fix_cron_res = hq_mod.evaluate_experiment_row(
            {
                "venture_id": "09",
                "name_ja": "Broken Cron Case",
                "elapsed_days": 10,
                "gsc_impressions": 500,
                "cta_clicks": 40,
                "conversions": 5,
                "cron_uptime_pct": 65.0,
            }
        )
        self.assertEqual(fix_cron_res["decision"], "FIX_CRON")

        summary = hq_mod.evaluate_scorecard(hq_mod.DEFAULT_MUSE_EXPERIMENTS)
        self.assertEqual(summary["evaluated_count"], 4)
        exp_ids = {r["venture_id"] for r in summary["results"]}
        self.assertEqual(exp_ids, {"07", "08", "09", "06"})

    def test_build_and_validate_in_temp_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_site = pathlib.Path(tmp) / "site"
            build_res = hq_mod.build_hq_artifacts(tmp_site, live_check=False)
            self.assertEqual(build_res["status"], "ok")
            self.assertTrue((tmp_site / "data" / "portfolio_manifest.json").is_file())
            self.assertTrue((tmp_site / "api" / "v1" / "hq_status.json").is_file())
            self.assertTrue((tmp_site / "sitemap.xml").is_file())
            self.assertTrue((tmp_site / ".nojekyll").is_file())

            val_res = hq_mod.validate_on_disk(tmp_site)
            self.assertEqual(val_res["status"], "validated")
            self.assertEqual(val_res["systems_count"], 11)

    def test_cli_self_test_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(PIPELINE_PATH), "--self-test"],
            cwd=str(VENTURE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("SELF-TEST PASS", proc.stdout)

    def test_workflow_uses_safe_event_inputs_and_daily_cron(self) -> None:
        yml_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("schedule:", yml_text)
        self.assertIn("cron:", yml_text)
        self.assertIn("github.event.inputs.live_check", yml_text)
        self.assertIsNone(re.search(r"\$\{\{\s*inputs\.", yml_text))

    def test_site_html_has_ga4_and_dom_id_parity(self) -> None:
        html_text = (SITE_DIR / "index.html").read_text(encoding="utf-8")
        js_text = (SITE_DIR / "app.js").read_text(encoding="utf-8")
        self.assertIn("G-F0ZLS15LNQ", html_text)
        self.assertIn("cta_engagement", html_text)

        defined_ids = set(re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', html_text))
        referenced_ids = set(re.findall(r'getElementById\(\s*["\']([^"\']+)["\']\s*\)', js_text))
        missing = sorted(referenced_ids - defined_ids)
        self.assertEqual(missing, [], f"Missing DOM IDs referenced by app.js: {missing}")

    def test_zero_forbidden_markers_and_safe_git_exclusion(self) -> None:
        forbidden = [
            re.compile(r"\bTODO\b"),
            re.compile(r"\bFIXME\b"),
            re.compile("\\u7701\\u7565"),
        ]
        violations = []
        for fpath in sorted(VENTURE_ROOT.rglob("*")):
            if not fpath.is_file():
                continue
            if any(part in SKIP_DIRS for part in fpath.parts):
                continue
            if fpath.suffix.lower() not in TEXT_SUFFIXES:
                continue
            content = fpath.read_text(encoding="utf-8")
            for pat in forbidden:
                m = pat.search(content)
                if m:
                    line_no = content[: m.start()].count("\n") + 1
                    violations.append(f"{fpath.relative_to(VENTURE_ROOT)}:{line_no}")
        self.assertEqual(violations, [], f"Forbidden markers detected: {violations}")


if __name__ == "__main__":
    unittest.main()
