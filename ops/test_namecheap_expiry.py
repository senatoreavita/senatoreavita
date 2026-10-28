"""Offline tests for namecheap_expiry — no network, no credentials needed.

Run:  python -I -m unittest ops/test_namecheap_expiry.py
(or:  python -I ops/test_namecheap_expiry.py)
"""

import io
import os
import sys
import datetime as dt
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import namecheap_expiry as nx  # noqa: E402

_NS = 'xmlns="http://api.namecheap.com/xml.response"'


def _ok_xml(expires: str, expired: str = "false") -> bytes:
    return (
        f'<?xml version="1.0"?>'
        f'<ApiResponse Status="OK" {_NS}>'
        f"<Errors/>"
        f'<CommandResponse Type="namecheap.domains.getList">'
        f"<DomainGetListResult>"
        f'<Domain ID="1" Name="startuplan.ai" Expires="{expires}" IsExpired="{expired}"/>'
        f"</DomainGetListResult></CommandResponse></ApiResponse>"
    ).encode()


def _err_xml() -> bytes:
    return (
        f'<?xml version="1.0"?>'
        f'<ApiResponse Status="ERROR" {_NS}>'
        f'<Errors><Error Number="1011150">Parameter ClientIp is missing</Error></Errors>'
        f"</ApiResponse>"
    ).encode()


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class NamecheapExpiryTests(unittest.TestCase):
    def setUp(self):
        for k in ("API_USER", "API_KEY", "USERNAME", "CLIENT_IP"):
            os.environ[f"NAMECHEAP_{k}"] = "x"
        self._orig = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self._orig

    def _patch(self, payload: bytes):
        urllib.request.urlopen = lambda *a, **k: _FakeResp(payload)

    def test_far_expiry_is_ok_green(self):
        future = (dt.date.today() + dt.timedelta(days=1000)).strftime("%m/%d/%Y")
        self._patch(_ok_xml(future))
        r = nx.check_domain_expiry("startuplan.ai")
        self.assertTrue(r["domain_ok"])
        self.assertEqual(r["domain_source"], "namecheap")
        self.assertAlmostEqual(r["domain_days"], 1000, delta=1)

    def test_within_warn_window_is_not_ok(self):
        soon = (dt.date.today() + dt.timedelta(days=10)).strftime("%m/%d/%Y")
        self._patch(_ok_xml(soon))
        r = nx.check_domain_expiry("startuplan.ai", warn_days=45)
        self.assertFalse(r["domain_ok"])
        self.assertIn("renewal window", r["domain_note"])

    def test_expired_flag_forces_not_ok(self):
        future = (dt.date.today() + dt.timedelta(days=1000)).strftime("%m/%d/%Y")
        self._patch(_ok_xml(future, expired="true"))
        r = nx.check_domain_expiry("startuplan.ai")
        self.assertFalse(r["domain_ok"])
        self.assertIn("EXPIRED", r["domain_note"])

    def test_api_error_degrades_gracefully(self):
        self._patch(_err_xml())
        r = nx.check_domain_expiry("startuplan.ai")
        self.assertFalse(r["domain_ok"])
        self.assertEqual(r["domain_source"], "namecheap-error")
        self.assertIn("ClientIp", r["domain_note"])

    def test_missing_credentials_never_raises(self):
        for k in ("API_USER", "API_KEY", "USERNAME", "CLIENT_IP"):
            os.environ.pop(f"NAMECHEAP_{k}", None)
        r = nx.check_domain_expiry("startuplan.ai")
        self.assertFalse(r["domain_ok"])
        self.assertIn("missing Namecheap credentials", r["domain_note"])


if __name__ == "__main__":
    unittest.main()
