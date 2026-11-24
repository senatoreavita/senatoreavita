# Deploy state — STAGING (Cloud Run)

Live record of the staging deployment on Google Cloud Run. Captured so the
facts survive the ephemeral Cloud Shell / session. **No secret values live
here** — the real secrets are in Secret Manager (`gcloud secrets list`); this
file only names them. The Supabase URL + *publishable* (anon) key and the
Turnstile *site* key are public by design (baked into the browser bundle), so
they are safe to record.

_Last updated: 2026-11-23 (B3 deploy — validated end-to-end: login + compute incl. Monte Carlo)._

## Project / registry
| Key | Value |
|---|---|
| Project ID | `startuplan-prod` |
| Project number | `861173221940` |
| Region | `europe-west1` |
| Artifact Registry | `europe-west1-docker.pkg.dev/startuplan-prod/startuplan` |
| GCP owners | `startuplan.ai@gmail.com`, `senatoriavita@gmail.com` |

## Services (both deployed from the branches below)
### Engine — `startuplan-engine`
| Key | Value |
|---|---|
| URL | `https://startuplan-engine-861173221940.europe-west1.run.app` |
| Image | `…/startuplan/engine:36bef50` |
| Source | `startuplan-core` @ commit `36bef50` |
| Access | `--ingress all --no-allow-unauthenticated` (IAM-locked) |
| Scaling | min 0 / max 1, cpu 1, mem 1Gi, concurrency 8, timeout 120 |
| Env vars | `ENVIRONMENT=staging`, `AI_PROVIDER=openai`, `STARTUPLAN_DEBUG=false`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` (publishable), `APP_URL`=web URL, `LANDING_PAGE_URL`=web URL |
| Secrets | `EXTRACT_SERVICE_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `RESEND_API_KEY` |

> Engine is `pydantic extra="forbid"` — pass **only** those 7 env fields or it won't boot.

### Web — `startuplan-web`
| Key | Value |
|---|---|
| URL (canonical) | `https://startuplan-web-861173221940.europe-west1.run.app` |
| URL (legacy alias) | `https://startuplan-web-fibbvtlv6a-ew.a.run.app` |
| Image | `…/startuplan/web:4aed4d2` |
| Source | `StartUPlan_Web` branch `dashboard_2026_11_23` @ commit `4aed4d2` |
| Access | `--ingress all --allow-unauthenticated` (public) |
| Scaling | min 0 / max 2, cpu 1, mem 512Mi |
| Build config | `cloudbuild.yaml` (bakes `NEXT_PUBLIC_*` at build time) |
| Baked `NEXT_PUBLIC_*` | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (publishable), `SITE_URL`=web URL, `TURNSTILE_SITE_KEY`=`0x4AAAAAAEL9xyuSP3Vlm2h5` (Cloudflare widget "StartUPlan Dev"), `API_URL`=engine URL, `OAUTH_GOOGLE=true`, `OAUTH_APPLE=false`, `TRIAL_UPGRADES=false` |
| Env vars | `ENGINE_EXTRACT_URL`=engine URL, `STRIPE_TAX_ENABLED=false`, `ALLOW_TRIAL_UPGRADES=false`, `STRIPE_PRICE_PLAN`/`STRIPE_PRICE_BANKABLE`/`STRIPE_PRICE_ADVISOR` (**placeholders** — see TODO) |
| Secrets | `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `TURNSTILE_SECRET_KEY`, `EXTRACT_SERVICE_TOKEN` |

## Supabase (public identifiers)
| Key | Value |
|---|---|
| Project URL | `https://amcdnkzhpotillagcqop.supabase.co` |
| Publishable (anon) key | `sb_publishable_QGd-tGZZ0N6ChzS_0TFnGA_raZrmt1G` |
| Service-role key | in Secret Manager as `SUPABASE_SERVICE_ROLE_KEY` (never in chat/repo) |

## IAM grants made during deploy
- Project `startuplan-prod`: compute SA `861173221940-compute@developer.gserviceaccount.com` → `roles/secretmanager.secretAccessor` (lets revisions read secrets).
- Service `startuplan-engine`: compute SA `861173221940-compute@…` → `roles/run.invoker` (lets the web SA call the IAM-locked engine; the ID-token audience = engine URL).

## Engine-door auth (ID-token path)
Web mints a Google ID token (audience = engine URL) → `Authorization: Bearer`.
Shared `EXTRACT_SERVICE_TOKEN` moved to `X-Extract-Token` as an app backstop.
Engine `_require_token` prefers `X-Extract-Token`, falls back to legacy Bearer.
**Verified ✅ (2026-11-23):** engine returns **403** to anonymous callers, and a
live compute in the app — including a full Monte Carlo run — succeeded, which
proves the web→engine ID-token accept-leg end-to-end. (A human Cloud Shell
login cannot mint an audience-scoped token, so this leg can only be tested
through the running app, not curl.)

## Turnstile / captcha (login) — resolved
- Login captcha token is verified by **Supabase** (`signInWithPassword({ options: { captchaToken }})`), not by app code. So the **site key** baked into the web and the **secret key** set in Supabase's captcha settings must both belong to the **same** Cloudflare widget ("StartUPlan Dev").
- Correct site key: `0x4AAAAAAEL9xyuSP3Vlm2h5`. (An earlier build baked a *different* widget's key — that was the cause of the `400020` / "100% bot" failures.)
- The app CSP (`next.config.ts`) needed **`data:` in `connect-src`** — Turnstile's challenge fetches a `data:` URI; without it the challenge 401'd ("Refused to connect to data:"). Fixed in commit `4aed4d2`.
- Cloudflare "StartUPlan Dev" widget has `startuplan-web-861173221940.europe-west1.run.app` in its allowed hostnames.
- Note: the GCP `TURNSTILE_SECRET_KEY` secret is used only by the **contact form** (`custom-inquiry`), not login — make sure it's the StartUPlan Dev widget's secret too before relying on that form.

## TODO before / during beta
- [ ] Replace web `STRIPE_PRICE_*` placeholders with real Stripe `price_…` IDs (`gcloud run services update startuplan-web --update-env-vars …`).
- [ ] Replace `STRIPE_WEBHOOK_SECRET` (currently `whsec_pending`) with the real live webhook secret after registering the Stripe webhook.
- [x] Sign-in allowlists (web hostname `startuplan-web-861173221940.europe-west1.run.app`):
  - [x] Cloudflare Turnstile → "StartUPlan Dev" widget → allowed hostnames.
  - [x] Supabase → Auth → URL Configuration → Site URL + `/**` redirect.
  - [ ] **Google OAuth is NOT enabled** in Supabase ("provider is not enabled") — enable the Google provider + set the Google client's redirect URI to `https://amcdnkzhpotillagcqop.supabase.co/auth/v1/callback` if Google sign-in is wanted for the beta. Email/password works today.
- [x] End-to-end: sign in ✅ + compute (Monte Carlo) ✅. Still to try: **export** (Excel/PDF) and **assistant** (second/third engine paths).
- [ ] Post-launch: custom domain (startuplan.ai), then rebuild web + update engine `APP_URL`/`LANDING_PAGE_URL` with the domain; revisit account consolidation.

## B4 pre-open gates
- [x] **RLS re-audit on prod — PASSED (2026-11-23).** Verified live against the prod DB (not just the static drift-guard):
  - Every `public` table RLS-on, owner-scoped (`auth.uid()`), no `using(true)` policy.
  - Live tables: `profiles, projects, project_inputs, project_outputs, export_files, payments, entitlements→(dropped), subscriptions, tier_grants, custom_inquiries, api_daily_usage`. `entitlements` + `plans` were **intentionally dropped** by `20260825140000_consolidate_persistence.sql` (superseded by `tier_grants` + shared `project_inputs`); their absence is correct, the drift-guard's expected-list is just stale on those two.
  - **Money/entitlement tables** (`tier_grants`, `payments`, `subscriptions`): users have **SELECT-only** owner-scoped policies → writes are **service-role only** (Stripe webhook). No tier self-grant possible.
  - **Storage** `exports` bucket = private; SELECT + INSERT policies both folder-scoped to `auth.uid()`.
  - SECURITY DEFINER fns: `handle_new_user` (signup→profiles, standard) and `increment_api_usage` (revoked from public/anon/authenticated) — both legit.
  - **Fix applied during the audit:** the `api_daily_usage` migration (durable global daily LLM cap, COST-01) was missing on prod — applied via SQL editor. Without it the app degraded to the weaker per-instance in-memory cap.
- [ ] Provider monetary spend caps — Anthropic Console → Limits + OpenAI → Limits (hard monthly cap + alerts).
- [ ] Backups (PITR) on + one restore drill — Supabase is on **FREE** (no backups/PITR). **Deferred to 1 Dec** (owner is aligning all paid subscriptions to that date), then upgrade to **Pro**. Interim risk: no recovery if data is lost before then — take at least one manual `pg_dump` snapshot before real testers store plans (see `BACKUPS.md`).
- [ ] Invite-only enforcement (Auth signup settings + app-side beta gate).

## AI token metering — Phase 1 (measurement layer)
Spec: `AI_TOKEN_BILLING.md`. **Measurement only — no wallet, no balance, no blocking.** Phase 2 (reservations/top-ups/Stripe packs) is a separate build behind the `AI_METERING_ENABLED` kill-switch.
- **Engine** (`startuplan-core` branch `session_2026_11_24`, commit `4e7d516`): single price table `core/ai/pricing.py` (`PRICES_VERIFIED=2026-11-24`) + one `core/ai/llm.py` seam; all AI call sites route through it; every AI endpoint returns `usage` (`/extract`, `/guided/next`, `/plan/assistant`) or an `X-AI-Usage` response header (`/plan/export`, binary). Full suite **1433 passed / 4 skipped**.
- **Web** (`StartUPlan_Web` branch `dashboard_2026_11_24`, commit `5d46d5c`): `src/lib/aiUsage.ts` fail-open logger wired into all four AI routes; **56 web tests** + typecheck + lint green.
- **Supabase migrations applied to prod via SQL editor (2026-11-24, both success):**
  - `20261124120000_ai_usage_log.sql` — COGS ledger. RLS-on, single read-own SELECT policy → **service-role-write-only**. Stores token counts + model + `cost_usd` only — **never prompt/response text** (privacy).
  - `20261124121000_ai_cogs_rollups.sql` — read-only views `ai_cogs_daily` / `ai_cogs_by_feature` / `ai_cogs_by_model` / `ai_cogs_by_user`, all `security_invoker = true` (honour the table's RLS: service role sees all, a user sees only their own).
- **Not yet deployed:** the two branches are pushed but **not merged/redeployed to Cloud Run**. Rows start accruing in `ai_usage_log` only once the engine + web are redeployed from these commits and a real AI action runs. After redeploy, watch COGS with `select * from public.ai_cogs_by_feature;`.

## Redeploy cheatsheet
Full walkthrough: `DEPLOY_QUICKSTART.md`. Reference: `DEPLOY_CLOUD_RUN.md`.
