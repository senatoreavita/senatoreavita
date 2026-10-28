"""Namecheap domain-expiry check for the ops-watcher.

Why this exists
---------------
The ops-watcher confirms the domain registration isn't about to lapse via RDAP
(the modern WHOIS). The ``.ai`` registry exposes **no public RDAP endpoint**, so
that lookup returns HTTP 403 for everyone — which is why Mission Control's Live
status shows the domain line amber ("check (.ai RDAP)"). This module asks
**Namecheap** (the registrar) directly for the true expiry date instead, so the
check can resolve and the line goes green.

Design
------
- **Stdlib only** (urllib + xml.etree + datetime) so it drops into the watcher
  with no new dependencies.
- **Reads credentials from the environment** — never hard-code keys. Mount these
  from Secret Manager on the Cloud Run job (see ops/README.md):
    NAMECHEAP_API_USER   — your Namecheap account username (API user)
    NAMECHEAP_API_KEY    — the API key from Namecheap → Profile → Tools → API Access
    NAMECHEAP_USERNAME   — usually the same as API_USER
    NAMECHEAP_CLIENT_IP  — the whitelisted egress IP the job calls from
  Optional:
    NAMECHEAP_DOMAIN     — domain to check (default "startuplan.ai")
    NAMECHEAP_WARN_DAYS  — green only if more days than this remain (default 45)
    NAMECHEAP_SANDBOX    — "1" to hit api.sandbox.namecheap.com

Return contract
---------------
``check_domain_expiry()`` returns a dict the watcher can merge into its status
document (the fields Mission Control reads/can show):
    {
      "domain": "startuplan.ai",
      "domain_ok": True/False,          # False when days <= warn, or on any error
      "domain_days": 1011,              # days to expiry, or None if unknown
      "domain_expires": "2029-08-05",   # ISO date, or None
      "domain_source": "namecheap",     # or "namecheap-error"
      "domain_note": "...",             # human-readable, set on error/warn
    }
It never raises: on any failure it returns domain_ok=False with a note, so the
watcher degrades to the same amber state it has today rather than crashing.
"""

from __future__ import annotations

import os
import datetime as _dt
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_PROD_HOST = "https://api.namecheap.com/xml.response"
_SANDBOX_HOST = "https://api.sandbox.namecheap.com/xml.response"
_TIMEOUT = 15  # seconds — the watcher runs daily; a short timeout keeps it snappy


def _local(tag: str) -> str:
    """Strip the ``{namespace}`` prefix ElementTree keeps on each tag."""
    return tag.rsplit("}", 1)[-1]


def _find_domain_node(root: ET.Element, domain: str):
    """Return the <Domain> element whose Name matches, namespace-agnostic."""
    want = domain.lower()
    for el in root.iter():
        if _local(el.tag) == "Domain" and (el.get("Name", "").lower() == want):
            return el
    return None


def _collect_errors(root: ET.Element) -> str:
    msgs = []
    for el in root.iter():
        if _local(el.tag) == "Error" and (el.text or "").strip():
            num = el.get("Number", "")
            msgs.append(f"{num}: {el.text.strip()}" if num else el.text.strip())
    return "; ".join(msgs)


def _parse_expires(value: str) -> _dt.date | None:
    """Namecheap returns Expires as MM/DD/YYYY; be lenient about a time suffix."""
    value = (value or "").strip().split(" ")[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def check_domain_expiry(
    domain: str | None = None,
    *,
    warn_days: int | None = None,
    timeout: int = _TIMEOUT,
) -> dict:
    """Query Namecheap for the domain's expiry. Never raises."""
    domain = (domain or os.environ.get("NAMECHEAP_DOMAIN") or "startuplan.ai").strip()
    if warn_days is None:
        try:
            warn_days = int(os.environ.get("NAMECHEAP_WARN_DAYS", "45"))
        except ValueError:
            warn_days = 45

    def _fail(note: str) -> dict:
        return {
            "domain": domain,
            "domain_ok": False,
            "domain_days": None,
            "domain_expires": None,
            "domain_source": "namecheap-error",
            "domain_note": note,
        }

    api_user = os.environ.get("NAMECHEAP_API_USER")
    api_key = os.environ.get("NAMECHEAP_API_KEY")
    username = os.environ.get("NAMECHEAP_USERNAME") or api_user
    client_ip = os.environ.get("NAMECHEAP_CLIENT_IP")
    if not (api_user and api_key and username and client_ip):
        return _fail(
            "missing Namecheap credentials "
            "(NAMECHEAP_API_USER / NAMECHEAP_API_KEY / NAMECHEAP_USERNAME / NAMECHEAP_CLIENT_IP)"
        )

    host = _SANDBOX_HOST if os.environ.get("NAMECHEAP_SANDBOX") == "1" else _PROD_HOST
    # A keyword search narrows the (paginated) list to our domain.
    params = {
        "ApiUser": api_user,
        "ApiKey": api_key,
        "UserName": username,
        "ClientIp": client_ip,
        "Command": "namecheap.domains.getList",
        "SearchTerm": domain.split(".")[0],
        "PageSize": "100",
        "Page": "1",
    }
    url = f"{host}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "startuplan-ops-watcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed host)
            body = resp.read()
    except Exception as exc:  # network / timeout / HTTP error
        return _fail(f"Namecheap request failed: {exc!r}")

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        return _fail(f"could not parse Namecheap response: {exc}")

    if (root.get("Status") or "").upper() == "ERROR":
        return _fail("Namecheap API error — " + (_collect_errors(root) or "unknown"))

    node = _find_domain_node(root, domain)
    if node is None:
        return _fail(f"{domain} not found in the Namecheap account's domain list")

    expires = _parse_expires(node.get("Expires", ""))
    if expires is None:
        return _fail(f"could not read an Expires date for {domain}")

    days = (expires - _dt.date.today()).days
    ok = days > warn_days
    note = "" if ok else f"renewal window: {days} days to expiry (warn <= {warn_days})"
    # Namecheap also carries IsExpired — treat an expired flag as not-ok regardless.
    if (node.get("IsExpired", "false") or "").lower() == "true":
        ok, note = False, "Namecheap reports the domain as EXPIRED"

    return {
        "domain": domain,
        "domain_ok": ok,
        "domain_days": days,
        "domain_expires": expires.isoformat(),
        "domain_source": "namecheap",
        "domain_note": note,
    }


if __name__ == "__main__":
    # Manual test: run with -I so the sandbox CWD can't shadow stdlib imports.
    #   python -I ops/namecheap_expiry.py
    import json

    print(json.dumps(check_domain_expiry(), indent=2))
