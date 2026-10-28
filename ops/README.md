# ops — watcher helpers

Small, dependency-free helpers for the **ops-watcher** (the read-only Cloud Run
job in project `startuplan-ops` that pings `startuplan.ai` daily at 07:00 Dublin
and has Claude summarise the health → feeds Mission Control's **Live status**).

## `namecheap_expiry.py` — turn the `.ai` domain check green

**Problem it solves.** The watcher confirms the domain registration isn't about
to lapse via RDAP. The `.ai` registry has **no public RDAP endpoint**, so that
lookup returns HTTP 403 and Mission Control shows the domain line amber
("check (.ai RDAP)"). This helper asks **Namecheap** (the registrar) directly
for the real expiry date, so the check resolves and goes green.

Stdlib only (no `pip install`), reads credentials from the environment, and
**never raises** — on any error it returns `domain_ok=False` with a note, so the
watcher degrades to today's amber state instead of crashing.

### 1. Get a Namecheap API key
Namecheap dashboard → **Profile → Tools → Business & Dev Tools → API Access** →
toggle **ON**. (API access requires the account to meet Namecheap's criteria —
e.g. ≥ 20 domains, ≥ $50 balance, or ≥ $50 spent in the last 2 years. If it
won't enable, see "If the API isn't available" below.)
Note the **API key**, your **API username**, and add the watcher's egress IP to
the **Whitelisted IPs** list (next step).

### 2. Give the Cloud Run job a stable egress IP (for the IP whitelist)
Namecheap only answers API calls from whitelisted IPs. A Cloud Run job's egress
IP is not stable by default, so route it through a static IP:
```bash
# one-time, in project startuplan-ops, region europe-west1
gcloud compute addresses create ops-watcher-egress --region=europe-west1
gcloud compute routers create ops-watcher-router --region=europe-west1 --network=default
gcloud compute routers nats create ops-watcher-nat \
  --router=ops-watcher-router --region=europe-west1 \
  --nat-external-ip-pool=ops-watcher-egress \
  --nat-all-subnet-ip-ranges
# then run the job with a Serverless VPC connector + --vpc-egress=all-traffic
```
Whitelist the reserved IP (`gcloud compute addresses describe ops-watcher-egress
--region=europe-west1 --format='value(address)'`) in Namecheap, and pass it as
`NAMECHEAP_CLIENT_IP`.

### 3. Store the secrets (never in code or chat)
```bash
printf '%s' 'YOUR_API_KEY'  | gcloud secrets create NAMECHEAP_API_KEY  --data-file=- --project=startuplan-ops
printf '%s' 'YOUR_API_USER' | gcloud secrets create NAMECHEAP_API_USER --data-file=- --project=startuplan-ops
# USERNAME is usually the same as API_USER; CLIENT_IP is the reserved egress IP
printf '%s' 'YOUR_API_USER' | gcloud secrets create NAMECHEAP_USERNAME  --data-file=- --project=startuplan-ops
printf '%s' 'THE_EGRESS_IP'  | gcloud secrets create NAMECHEAP_CLIENT_IP --data-file=- --project=startuplan-ops
```
Then mount them on the job (`gcloud run jobs update ops-watcher
--set-secrets=NAMECHEAP_API_KEY=NAMECHEAP_API_KEY:latest,...`).

### 4. Wire it into the watcher
Ship `namecheap_expiry.py` alongside the watcher's source and replace the `.ai`
RDAP branch with one call. The returned dict's keys match the status document
the watcher already writes:
```python
from namecheap_expiry import check_domain_expiry

dom = check_domain_expiry()          # {"domain_ok", "domain_days", "domain_expires", ...}
status["domain_ok"]      = dom["domain_ok"]
status["domain_days"]    = dom["domain_days"]      # optional, for the report line
status["domain_expires"] = dom["domain_expires"]
if dom["domain_note"]:
    status.setdefault("report", "")               # surface warnings in the summary
```
Mission Control reads `domain_ok` → the line shows **ok** (green) once the check
resolves. `domain_days` / `domain_expires` are available if you later want the
Live-status panel to show the actual date (a one-line change in the artifact).

### Test locally
```bash
python -I ops/namecheap_expiry.py          # prints the result as JSON
python -I ops/test_namecheap_expiry.py     # offline tests (no network/creds)
```
With real creds exported, the first command prints the live expiry (should be
**2029-08-05**, matching the renewed domain). Use `NAMECHEAP_SANDBOX=1` to hit
the sandbox API.

### Config (env)
| Variable | Required | Default | Notes |
|---|---|---|---|
| `NAMECHEAP_API_USER` | yes | — | API username |
| `NAMECHEAP_API_KEY` | yes | — | from Profile → Tools → API Access |
| `NAMECHEAP_USERNAME` | yes | API_USER | usually the same |
| `NAMECHEAP_CLIENT_IP` | yes | — | the whitelisted egress IP |
| `NAMECHEAP_DOMAIN` | no | `startuplan.ai` | domain to check |
| `NAMECHEAP_WARN_DAYS` | no | `45` | green only if more days remain |
| `NAMECHEAP_SANDBOX` | no | — | `1` → sandbox API host |

## `mission_control_status.py` — keep the Live-status card fresh

**Problem it solves.** The watcher's **Live status** card reads one shared-db doc
(`status/site`). If the watcher stops writing it, the card silently freezes at
the last write — it sat on the 5 Oct run for 23 days before this was noticed.

`build_status_doc(http, tls, domain)` assembles that document in exactly the
shape the page renders — including a fresh `checked_at` every run and a computed
`severity` (OK / ATTENTION / PROBLEM) and `report` — so the watcher has one
source of truth for the payload and the card can't go quietly stale.

### Wire it into the watcher
At the end of each check-in, after probing the site, call the builder and write
the result to `status/site`:
```python
from namecheap_expiry import check_domain_expiry
from mission_control_status import build_status_doc, MISSION_CONTROL_URL

doc = build_status_doc(
    http={"ok": http_up, "latency_ms": latency_ms},     # from the HTTP probe
    tls={"ok": tls_ok, "expires": tls_expires_iso},      # from the TLS probe (days auto-computed)
    domain=check_domain_expiry(),                         # the Namecheap check
)
# Write it back. In the Claude check-in this is the ArtifactData tool:
#   ArtifactData(action="update", url=MISSION_CONTROL_URL,
#                collection="status", doc_id="site",
#                if_version=<version last read>, data=doc)
```
`checked_at` is stamped to "now" by the builder, so **the card's "updated …" line
tracks each run automatically.** Read `status/site` first and pass its `version`
as `if_version` so a concurrent edit isn't clobbered.

### Test locally
```bash
python -I ops/mission_control_status.py          # prints a demo status doc
python -I ops/test_mission_control_status.py     # offline tests
```

### Note on probing from a sandbox
The TLS probe must run from somewhere that reaches the **origin** directly. An
intercepting proxy (and some CI sandboxes) terminates TLS, so an `openssl`/`curl`
check there sees the *proxy's* cert, not `startuplan.ai`'s — the real Cloud Run
watcher has direct egress and gets the true cert. (This is why a one-off refresh
from a restricted session can only honestly update the domain + timestamp and
must carry HTTP/TLS from the last real run.)

---

### If the Namecheap API isn't available
If your account can't enable API access, two alternatives keep the line green
without the registrar API:
- **Static reminder:** hard-code the known expiry (`2029-08-05`) and compute
  `domain_days` locally — correct until the next renewal, zero dependencies.
- **Paid RDAP/WHOIS provider** (e.g. WhoisXML, RDAP.org passthrough) that *does*
  cover `.ai`, called the same way as this module.
Either drops into the same `check_domain_expiry()` shape.
