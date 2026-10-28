"""Build (and describe how to post) the Mission Control live-status document.

The **Live status** card on Mission Control reads ONE shared-db document:

    collection "status", document "site"   (path: status/site)

The ops-watcher is meant to refresh it on every run. If it stops writing, the
card silently freezes at the last write (that is exactly what happened — the
card sat on the 5 Oct run for 23 days). This module assembles that document in
*exactly* the shape the page renders, from the check results, so the watcher has
one source of truth for the payload — and always stamps a fresh ``checked_at``
so the card can't go stale without it being obvious.

How it is written back
----------------------
The watcher "has Claude summarise the health", so the write happens through
Claude's artifact-db tool (``ArtifactData``) during the daily check-in — an
``update`` (merge) to ``status/site`` with the dict from ``build_status_doc``:

    ArtifactData(action="update",
                 url=MISSION_CONTROL_URL,
                 collection="status", doc_id="site",
                 if_version=<version last read>,
                 data=build_status_doc(http, tls, domain))

Pin ``if_version`` to the version last read so a concurrent edit isn't clobbered
(read status/site first, use its ``version``). If the watcher ever writes the db
directly over the artifact HTTP API instead of via a Claude session, the same
dict is the request body.

The returned dict carries every field the page reads:
    watched, checked_at, severity, report,
    http_ok, latency_ms, tls_ok, tls_days, tls_expires,
    domain_ok, domain_days, domain_expires, domain_source, source
"""

from __future__ import annotations

import datetime as _dt

MISSION_CONTROL_URL = "https://claude.ai/artifact/AYoY5uQBX52sd64eWjPbpp"

# Warn windows: flag TLS inside 14 days (a managed cert should have auto-renewed
# well before then) and the domain inside 45 days of expiry.
TLS_WARN_DAYS = 14
DOMAIN_WARN_DAYS = 45


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _days_until(date_str: str | None) -> int | None:
    """Days from today to an ISO ``YYYY-MM-DD`` date, or None if unparseable."""
    if not date_str:
        return None
    try:
        d = _dt.datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - _dt.date.today()).days


def severity_for(
    http_ok: bool,
    tls_days: int | None,
    domain_ok: bool,
    *,
    tls_warn: int = TLS_WARN_DAYS,
    domain_warn: int = DOMAIN_WARN_DAYS,
) -> str:
    """OK / ATTENTION / PROBLEM — PROBLEM if the site is down, ATTENTION if a
    cert or the domain is inside its warn window (or the domain check failed)."""
    if not http_ok:
        return "PROBLEM"
    if (tls_days is not None and tls_days <= tls_warn) or not domain_ok:
        return "ATTENTION"
    return "OK"


def build_report(watched: str, http: dict, tls: dict, domain: dict) -> str:
    """One human sentence summarising the three checks for the card body."""
    host = watched.replace("https://", "").replace("http://", "").rstrip("/")
    if http.get("ok"):
        lat = http.get("latency_ms")
        bit_http = f"HTTP healthy ({'~' + str(lat) + 'ms' if lat is not None else 'up'})"
    else:
        bit_http = "HTTP is DOWN"

    td, te = tls.get("days"), tls.get("expires")
    if te:
        bit_tls = f"TLS cert {'valid' if (td is None or td > TLS_WARN_DAYS) else 'EXPIRING'} (expires {te}{f', ~{td} days' if td is not None else ''})"
    else:
        bit_tls = "TLS not checked"

    dd, de = domain.get("domain_days"), domain.get("domain_expires")
    if domain.get("domain_ok") and de:
        bit_dom = f"domain valid to {de}{f' (~{dd} days)' if dd is not None else ''}"
    elif de:
        bit_dom = f"domain EXPIRING ({de}, ~{dd} days)"
    else:
        bit_dom = "domain expiry unverified (" + (domain.get("domain_note") or "no registrar data") + ")"

    return f"{host} is {'operational' if http.get('ok') else 'DOWN'}. {bit_http}. {bit_tls}. {bit_dom.capitalize()}."


def build_status_doc(
    http: dict,
    tls: dict,
    domain: dict,
    *,
    watched: str = "https://startuplan.ai",
    now: str | None = None,
    source: str = "ops-watcher",
    report: str | None = None,
) -> dict:
    """Assemble the status/site document the Live-status card renders.

    http:   {"ok": bool, "latency_ms": int|None}
    tls:    {"ok": bool, "expires": "YYYY-MM-DD"|None, "days": int|None}
            (days is recomputed from expires when omitted)
    domain: the dict from ``namecheap_expiry.check_domain_expiry`` (domain_ok /
            domain_days / domain_expires / domain_source / domain_note)
    """
    tls_days = tls.get("days")
    if tls_days is None:
        tls_days = _days_until(tls.get("expires"))

    http_ok = bool(http.get("ok"))
    domain_ok = bool(domain.get("domain_ok"))
    sev = severity_for(http_ok, tls_days, domain_ok)

    doc = {
        "watched": watched,
        "checked_at": now or _utcnow_iso(),
        "severity": sev,
        "report": report or build_report(watched, http, tls, domain),
        "http_ok": http_ok,
        "latency_ms": http.get("latency_ms"),
        "tls_ok": bool(tls.get("ok")),
        "tls_days": tls_days,
        "tls_expires": tls.get("expires"),
        "domain_ok": domain_ok,
        "domain_days": domain.get("domain_days"),
        "domain_expires": domain.get("domain_expires"),
        "domain_source": domain.get("domain_source"),
        "source": source,
    }
    return doc


if __name__ == "__main__":
    # Demo assembly (run with -I). In the watcher, replace these with real probe
    # results and the domain dict from check_domain_expiry().
    import json

    demo = build_status_doc(
        http={"ok": True, "latency_ms": 72},
        tls={"ok": True, "expires": "2026-11-17"},
        domain={
            "domain_ok": True,
            "domain_days": _days_until("2029-08-05"),
            "domain_expires": "2029-08-05",
            "domain_source": "namecheap",
        },
    )
    print(json.dumps(demo, indent=2))
