# Cloud Run deploy — StartUPlan private beta

A step-by-step runbook to put the **engine** (`startuplan-core`, FastAPI) and the
**web** (`StartUPlan_Web`, Next.js standalone) on Cloud Run for the **private,
invite-only beta** (test-mode payments, one small invited group).

- **Scope:** beta only. Public-launch extras (live Stripe, durable rate limiting,
  monitoring, custom domain) are in the Launch Readiness go/no-go, not here.
- **Companions:** `INFRA.md` (GCP provisioning — do that first) · `StartUPlan_Web/docs/deploy.md`
  (prod/Stripe wiring) · `StartUPlan_Web/docs/SETUP_payments_auth_security.md`.
- **Project / region:** `startuplan-prod` / `europe-west1`. **Registry:** `startuplan`.
- Code is on **`session_2026_11_20`** (engine) and **`dashboard_2026_11_20`** (web).

---

## ⚠️ Read first — two fixes the current code/Dockerfile need

These were found while drafting this runbook. Decide/fix them **before** you build.

### A. Pass every client `NEXT_PUBLIC_*` as a build arg  ✅ applied (Dockerfile + client guard)
Next.js inlines `process.env.NEXT_PUBLIC_*` into the **client bundle at build time**, so each
one the browser needs must be present at `npm run build`, not just at runtime. The
`StartUPlan_Web/Dockerfile` now declares build ARGs for all of them (`NEXT_PUBLIC_SUPABASE_URL`,
`_ANON_KEY`, `NEXT_PUBLIC_SITE_URL`, the two OAuth flags, `NEXT_PUBLIC_API_URL`,
`NEXT_PUBLIC_TRIAL_UPGRADES`, plus the existing Turnstile key) — **you just pass values with
`--build-arg`** (step 4). They are all PUBLIC values, safe to bake into the image.

If you forget one (e.g. `NEXT_PUBLIC_SUPABASE_URL`), the browser's Supabase client is
unconfigured: **sign-in breaks and the UI can't read the real tier** (it even shows the
local-preview demo unlocked). The *server* still gates real feature access — `verifyAuth`
fails closed with **503** in production when its service-role key is missing — so this is a
broken-login / misleading-UI problem, **not** a server-side tier bypass. A client-side
safety-catch was also added (`useUserTier`): a production build never defaults to the demo
tier, so a misbuilt image can't show everything unlocked.

### B. Web→engine auth is the bearer **service token**, not a Google ID token
The web calls the engine with `Authorization: Bearer ${EXTRACT_SERVICE_TOKEN}` (every
`src/app/api/*` route). There is **no `google-auth` dependency**, so it does **not** mint a
Cloud Run ID token. Therefore you **cannot** deploy the engine `--no-allow-unauthenticated`
(Cloud Run's IAM layer would reject the web's token-only calls before they reach the app).

**For the beta, pick one:**
- **B1 (recommended, simplest):** engine `--ingress internal --allow-unauthenticated`. Internal
  ingress blocks the public internet; the app's `EXTRACT_SERVICE_TOKEN` is the auth. Requires the
  web to reach the engine over internal routing — add a **Serverless VPC connector** on the web
  service (`--vpc-connector` + `--vpc-egress all-traffic`) so its egress to the engine stays internal.
- **B2 (no VPC connector):** engine `--ingress all --allow-unauthenticated`. The engine URL is
  publicly reachable but **token-gated** (fail-closed: unset token ⇒ 503; a 32-byte token is
  infeasible to brute, compare is constant-time). Acceptable for a short invite beta; tighten to
  B1 or ID-tokens before public launch.

Either way **`EXTRACT_SERVICE_TOKEN` must be set** — after the Phase-0 auth fix the engine fails
closed (503) in any non-`development` environment without it. Before public launch, the proper
end state is `--ingress internal --no-allow-unauthenticated` + the web minting an ID token
(needs `google-auth-library` added to the web).

---

## 0. Provisioning (from INFRA.md — verify done)
```bash
gcloud config set project startuplan-prod
gcloud config set run/region europe-west1
# APIs: run, cloudbuild, artifactregistry, secretmanager  (INFRA.md §2)
# Artifact Registry repo "startuplan" exists                (INFRA.md §3)
```

## 1. Create + fill the secrets (Secret Manager)
Generate the shared engine token **once** and give it to BOTH services:
```bash
openssl rand -hex 32            # copy this value; it is EXTRACT_SERVICE_TOKEN
```
Create each secret, then add its value (paste, Ctrl-D). Never put values in chat/history.
```bash
for S in EXTRACT_SERVICE_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY RESEND_API_KEY \
         SUPABASE_SERVICE_ROLE_KEY STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET TURNSTILE_SECRET_KEY ; do
  gcloud secrets create "$S" --replication-policy=automatic 2>/dev/null || true
done
gcloud secrets versions add EXTRACT_SERVICE_TOKEN --data-file=-   # paste, Ctrl-D ; repeat per secret
```
- **Engine secrets:** `EXTRACT_SERVICE_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `RESEND_API_KEY`.
- **Web secrets:** `EXTRACT_SERVICE_TOKEN` (same value), `SUPABASE_SERVICE_ROLE_KEY`,
  `STRIPE_SECRET_KEY` (test `sk_test_…`), `STRIPE_WEBHOOK_SECRET` (test), `TURNSTILE_SECRET_KEY`.
- Stripe test-mode go-live note: the webhook secret is the **prod endpoint's** `whsec_…`,
  created in step 6 of `docs/deploy.md` — for the beta you can register a test-mode endpoint.

## 2. Build + push the ENGINE image
`.dockerignore` already trims tests/Demos/etc. (Phase-0 cleanup).
```bash
cd startuplan-core
TAG=$(git rev-parse --short HEAD)
IMG=europe-west1-docker.pkg.dev/startuplan-prod/startuplan/engine:$TAG
gcloud builds submit --tag "$IMG" .
```

## 3. Deploy the ENGINE (internal, token-gated)
The engine config is `extra="forbid"` — pass **only** the variables it knows
(`AI_PROVIDER`, `ENVIRONMENT`, `STARTUPLAN_DEBUG`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`APP_URL`, `LANDING_PAGE_URL`) + its 4 secrets. Any unknown var stops it booting.
```bash
gcloud run deploy startuplan-engine \
  --image "$IMG" \
  --region europe-west1 \
  --ingress internal \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 1 \
  --cpu 1 --memory 1Gi --concurrency 8 --timeout 120 \
  --set-env-vars ENVIRONMENT=staging,AI_PROVIDER=openai,STARTUPLAN_DEBUG=false,SUPABASE_URL=https://XXXX.supabase.co,SUPABASE_ANON_KEY=eyJ...,APP_URL=https://<web-url>,LANDING_PAGE_URL=https://<web-url> \
  --set-secrets EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest
```
- `ENVIRONMENT=staging` + the token set ⇒ fail-closed auth is active (good).
- `--max-instances 1` for the beta (the 10k Monte-Carlo path is CPU-heavy; bump `--cpu`/`--memory`
  if exports/MC feel slow). Note the **internal URL** it prints → that's `ENGINE_EXTRACT_URL`.
- `SUPABASE_ANON_KEY` is a public value; fine as an env var (or move to a secret if you prefer).

## 4. Build + push the WEB image  (after fix A)
Pass every client `NEXT_PUBLIC_*` as a build arg (they bake into the bundle):
```bash
cd ../startuplan_web
TAG=$(git rev-parse --short HEAD)
IMG=europe-west1-docker.pkg.dev/startuplan-prod/startuplan/web:$TAG
gcloud builds submit --tag "$IMG" \
  --substitutions _NEXT_PUBLIC_SUPABASE_URL=...,_NEXT_PUBLIC_SUPABASE_ANON_KEY=...    # see note
```
> `gcloud builds submit --tag` can't pass `--build-arg` directly. Use **one of**:
> (a) a small `cloudbuild.yaml` with a `docker build --build-arg …` step, or
> (b) build locally and push:
> ```bash
> docker build -t "$IMG" \
>   --build-arg NEXT_PUBLIC_TURNSTILE_SITE_KEY=0x... \
>   --build-arg NEXT_PUBLIC_SUPABASE_URL=https://XXXX.supabase.co \
>   --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ... \
>   --build-arg NEXT_PUBLIC_SITE_URL=https://<web-url> \
>   --build-arg NEXT_PUBLIC_OAUTH_GOOGLE=true \
>   --build-arg NEXT_PUBLIC_OAUTH_APPLE=false \
>   --build-arg NEXT_PUBLIC_API_URL=https://<web-url> \
>   --build-arg NEXT_PUBLIC_TRIAL_UPGRADES=false .
> gcloud auth configure-docker europe-west1-docker.pkg.dev -q && docker push "$IMG"
> ```
> `<web-url>` is chicken-and-egg: deploy once to learn the URL, then rebuild with the real
> `NEXT_PUBLIC_SITE_URL`/`APP_URL`, or map a custom domain up front and use that.

## 5. Deploy the WEB (public)
Runtime server env (secrets + the internal engine URL). `NEXT_PUBLIC_*` are already baked.
Add the VPC connector here only if you chose **B1**.
```bash
gcloud run deploy startuplan-web \
  --image "$IMG" \
  --region europe-west1 \
  --ingress all --allow-unauthenticated \
  --min-instances 0 --max-instances 2 \
  --cpu 1 --memory 512Mi \
  --set-env-vars ENGINE_EXTRACT_URL=<engine-internal-url>,STRIPE_TAX_ENABLED=false,ALLOW_TRIAL_UPGRADES=false,STRIPE_PRICE_PLAN=price_...,STRIPE_PRICE_BANKABLE=price_...,STRIPE_PRICE_ADVISOR=price_... \
  --set-secrets SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,TURNSTILE_SECRET_KEY=TURNSTILE_SECRET_KEY:latest,EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest
  # B1 only: --vpc-connector <connector> --vpc-egress all-traffic
```
- **`ALLOW_TRIAL_UPGRADES`**: leave **off** (default). Turn on **only** if the beta needs the
  no-payment self-upgrade for testers; purge trial grants before public.
- The engine needs **no** Stripe secrets (and rejects them) — all Stripe lives on the web.

## 6. Wire the two services together
- Set the engine's `APP_URL`/`LANDING_PAGE_URL` and the web's `NEXT_PUBLIC_SITE_URL`/`ENGINE_EXTRACT_URL`
  to the real URLs (redeploy the step whose URL you didn't know yet).
- **Supabase:** add the web's URL to Auth → URL Configuration (redirect allowlist) and finish the
  **Google OAuth** provider config (client id/secret). Confirm `NEXT_PUBLIC_OAUTH_GOOGLE=true`.

## 7. Pre-open gates (don't skip — these protect the beta)
- [ ] **Invite-only** — confirm the allowlist / beta flag is enforced (open signup OFF). *(Verify this exists in code; it's a Timeline item.)*
- [ ] **Spend caps** — hard monthly caps + budget alerts on the OpenAI (and Anthropic) accounts.
- [ ] **Backups** — Supabase PITR ON, and run one restore drill into a throwaway DB.
- [ ] **Pre-beta RLS re-audit on the live DB** — every table RLS-on + owner-scoped; the drift-guard
      test (now covers the canonical tables) is the static check; confirm it on prod too.

## 8. Smoke test
```bash
# Engine is internal; curl it from within (Cloud Run shell / the web container), token required:
curl -sS -H "Authorization: Bearer $TOKEN" <engine-internal-url>/health      # {"ok":true,...}
curl -sS <engine-internal-url>/suggestions                                   # 401 (no token) — good
```
Then in the browser: sign in with Google → create a project → **compute** (exercises web→engine)
→ **export** a PDF + Excel → ask the **Assistant** a question (needs `OPENAI_API_KEY`). Confirm a
logged-out visitor can't reach a gated feature.

## 9. Rollback
```bash
gcloud run revisions list --service startuplan-web --region europe-west1
gcloud run services update-traffic startuplan-web --region europe-west1 --to-revisions <PREV>=100
```
Each deploy is an immutable revision; traffic can snap back instantly.

---

## Beta → public — what changes (plain words)

Going from the private beta to the open public is **mostly flipping settings and
opening accounts, not rebuilding the app**. Only **two** items below are real code
changes (marked 🛠); the rest are configuration, paperwork, or safety add-ons. This
is the same content as the Launch Readiness "Public launch — go/no-go gate", in plain
language, kept next to the beta steps so the delta is obvious.

1. **Money becomes real.** Beta runs payments in test mode (fake cards, no bank).
   Public: business **bank account** open → Stripe **test keys → live keys** + a live
   webhook secret → **VAT/tax on** + real invoices → verify **one real transaction**
   end-to-end → turn **off** `ALLOW_TRIAL_UPGRADES` and purge test/trial grants.
2. **The address changes.** Beta uses the long `…run.app` link you send invitees.
   Public: map **`startuplan.ai`** onto the web service, with managed TLS (https).
3. **The doors open.** Beta is invite-only (allowlist on). Public: turn **open
   signup on**.
4. **The engine's lock gets stronger.** 🛠 Beta uses the shared-password lock
   (`--allow-unauthenticated` + `EXTRACT_SERVICE_TOKEN`). Public moves to the Google
   **ID-token** setup — engine `--ingress internal --no-allow-unauthenticated`, and the
   web mints an ID token for each call (needs `google-auth-library` added to the web) —
   so a leaked password alone can't get in.
5. **It has to handle a crowd.** Beta runs a single instance. Public:
   - raise `--max-instances`, and make the per-minute rate limit **durable / shared
     across instances** (Memorystore or Upstash) — today it's counted per-instance, so
     several instances let a user slip past the cap;
   - **hard spend caps + budget alerts** on the AI accounts (volume/abuse can't run up an
     unbounded bill);
   - move the two slow jobs (**10k-run Monte-Carlo** and **AI extraction**) to run in the
     **background/async** so they don't jam the app under load.
6. **Eyes on it.** Beta you watch by hand. Public: **error tracking, uptime checks, and
   alerts** to your phone, so a breakage or spend spike surfaces in minutes.
7. **Legal paperwork** (required once there are real users + money): Terms of Service
   (with refund policy), Privacy Policy + sub-processor list, GDPR lawful basis + data
   agreements (DPAs), a working **data export/erasure** path, cookie consent, and your
   real **company + VAT number** shown in the terms.
8. **Lock scope + pricing.** Only sell features that actually render, finalize prices,
   and switch off any dev/test flags (`environment=production`).
9. **Protect real users' saved data.** 🛠 In the beta tester data is disposable; for the
   public, real users' saved plans must survive future engine changes — build the
   **plan schema-version migration path** (read `schema_version` → run migrators →
   deserialize) so changing the engine never orphans a saved plan.
10. **Final checks before flipping the switch.** Re-run the security/RLS check on the
    **live** DB, a security review + load test, write a short incident + rollback plan,
    confirm Streamlit is retired (done ✓), and a final **go/no-go sign-off**.

**In one line:** the app stays the same; going public is turning on real payments, your
own domain, open signup, crowd-safety (shared rate limits, spend caps, monitoring), the
legal paperwork, and the two code jobs (stronger engine lock + saved-plan protection).
