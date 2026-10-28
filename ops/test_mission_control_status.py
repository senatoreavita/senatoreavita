"""Offline tests for mission_control_status.  Run:
    python -I ops/test_mission_control_status.py
"""

import os
import sys
import datetime as dt
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mission_control_status as mc  # noqa: E402


def _in(days):
    return (dt.date.today() + dt.timedelta(days=days)).isoformat()


class SeverityTests(unittest.TestCase):
    def test_down_is_problem(self):
        self.assertEqual(mc.severity_for(False, 999, True), "PROBLEM")

    def test_all_healthy_is_ok(self):
        self.assertEqual(mc.severity_for(True, 999, True), "OK")

    def test_tls_in_warn_window_is_attention(self):
        self.assertEqual(mc.severity_for(True, 10, True), "ATTENTION")

    def test_domain_not_ok_is_attention(self):
        self.assertEqual(mc.severity_for(True, 999, False), "ATTENTION")


class BuildDocTests(unittest.TestCase):
    def test_full_healthy_doc(self):
        doc = mc.build_status_doc(
            http={"ok": True, "latency_ms": 72},
            tls={"ok": True, "expires": _in(300)},
            domain={"domain_ok": True, "domain_days": 1012,
                    "domain_expires": "2029-08-05", "domain_source": "namecheap"},
            now="2026-10-28T21:39:17Z",
        )
        self.assertEqual(doc["severity"], "OK")
        self.assertEqual(doc["checked_at"], "2026-10-28T21:39:17Z")
        self.assertEqual(doc["domain_expires"], "2029-08-05")
        self.assertEqual(doc["tls_days"], 300)        # recomputed from expires
        self.assertIn("2029-08-05", doc["report"])
        # every field the page reads is present
        for k in ("watched", "checked_at", "severity", "report", "http_ok",
                  "latency_ms", "tls_days", "tls_expires", "domain_ok",
                  "domain_days", "domain_expires", "source"):
            self.assertIn(k, doc)

    def test_tls_days_recomputed_when_absent(self):
        doc = mc.build_status_doc(
            http={"ok": True, "latency_ms": 50},
            tls={"ok": True, "expires": _in(20)},   # no "days" supplied
            domain={"domain_ok": True, "domain_days": 1, "domain_expires": _in(1)},
        )
        self.assertEqual(doc["tls_days"], 20)

    def test_down_site_reports_problem(self):
        doc = mc.build_status_doc(
            http={"ok": False, "latency_ms": None},
            tls={"ok": True, "expires": _in(300)},
            domain={"domain_ok": True, "domain_days": 1012, "domain_expires": "2029-08-05"},
        )
        self.assertEqual(doc["severity"], "PROBLEM")
        self.assertIn("DOWN", doc["report"])

    def test_default_checked_at_is_now_utc(self):
        doc = mc.build_status_doc(
            http={"ok": True, "latency_ms": 72},
            tls={"ok": True, "expires": _in(300)},
            domain={"domain_ok": True, "domain_days": 1012, "domain_expires": "2029-08-05"},
        )
        self.assertTrue(doc["checked_at"].endswith("Z"))
        # parseable ISO-8601 Z timestamp
        dt.datetime.strptime(doc["checked_at"], "%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    unittest.main()
