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

### B. Web→engine auth — Google ID token (OIDC), shared token as backstop
The web mints a **Google-signed ID token** for the engine URL (as audience) on every
`src/app/api/*` call — `src/lib/engineAuth.ts`, using `google-auth-library` — and sends it in
`Authorization`. It **also** sends the shared `EXTRACT_SERVICE_TOKEN` in a separate
`X-Extract-Token` header. Two independent gates, so one mis-deploy can't open the engine.

**Decision: ID-token auth selected — best practice, $0 extra infra.** ✅
- **Primary (platform):** engine `--ingress all --no-allow-unauthenticated`; the web's runtime
  service account is granted **`roles/run.invoker`** on the engine. Cloud Run validates the ID
  token *at the edge*, so an unauthenticated request never reaches the app. Scales to zero — **no
  VPC, no NAT, no monthly cost**.
- **Backstop (app):** the engine still checks `EXTRACT_SERVICE_TOKEN`, now read from
  `X-Extract-Token` (falling back to `Authorization: Bearer` for pre-ID-token clients). So even a
  mis-deploy to `--allow-unauthenticated` can't expose it, and local dev (no Cloud Run in front)
  runs on this token alone. The ID-token mint auto-disables off Cloud Run (no metadata server).

**Alternatives (not chosen — kept for reference):**
- **B1 — also hide the engine at the network layer:** add `--ingress internal` + a Serverless VPC
  connector (`--vpc-egress all-traffic`) + Cloud NAT. This layers network hiding *on top of* the ID
  token, at **~$40–55/mo** (connector + NAT, always-on). Optional hardening for later; commands in
  **step 4b**. The engine holds only the RLS-gated anon key, not the service-role key, so this buys
  little for the beta — it's abuse-surface reduction, not user-data protection.
- **B2 — shared token only, no ID token:** engine `--ingress all --allow-unauthenticated`,
  token-gated (fail-closed: unset token ⇒ 503; 32-byte token, constant-time compare). The simplest
  fallback if the invoker grant proves fiddly on the day — just drop `--no-allow-unauthenticated`
  and skip the grant; the `X-Extract-Token` backstop still gates every call.

`EXTRACT_SERVICE_TOKEN` **must be set** in all of the above — after the Phase-0 auth fix the engine
fails closed (503) in any non-`development` environment without it.

> **Technical terms** (what to search for; also on the Timeline):
> - **ID-token / OIDC service-to-service auth (chosen)** = engine **`--no-allow-unauthenticated`**,
>   the web's service account granted **`roles/run.invoker`** on the engine, and the web attaching a
>   **Google-signed ID token** per call (via **`google-auth-library`**, engine URL as the
>   **audience**). This is the "Google ID badge."
> - **Hiding the engine (B1, optional add-on)** = Cloud Run **"internal" ingress** + a **Serverless
>   VPC Access connector** (`--vpc-connector` + `--vpc-egress`) + **Cloud NAT**. Network-layer
>   hiding; stacks on top of the ID token if you ever want it.

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

## 3. Deploy the ENGINE (public URL, IAM-locked + token-gated)
The engine config is `extra="forbid"` — pass **only** the variables it knows
(`AI_PROVIDER`, `ENVIRONMENT`, `STARTUPLAN_DEBUG`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`APP_URL`, `LANDING_PAGE_URL`) + its 4 secrets. Any unknown var stops it booting.
```bash
gcloud run deploy startuplan-engine \
  --image "$IMG" \
  --region europe-west1 \
  --ingress all \
  --no-allow-unauthenticated \
  --min-instances 0 --max-instances 1 \
  --cpu 1 --memory 1Gi --concurrency 8 --timeout 120 \
  --set-env-vars ENVIRONMENT=staging,AI_PROVIDER=openai,STARTUPLAN_DEBUG=false,SUPABASE_URL=https://XXXX.supabase.co,SUPABASE_ANON_KEY=eyJ...,APP_URL=https://<web-url>,LANDING_PAGE_URL=https://<web-url> \
  --set-secrets EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest
```
- `--no-allow-unauthenticated` ⇒ Cloud Run IAM gates the engine: only callers bearing a valid
  Google ID token *and* holding `roles/run.invoker` get in (grant is in **step 6**). `--ingress all`
  is fine because IAM is the lock — the public URL answers only to authenticated callers.
- `ENVIRONMENT=staging` + the token set ⇒ the app-level fail-closed backstop is active too (good).
- `--max-instances 1` for the beta (the 10k Monte-Carlo path is CPU-heavy; bump `--cpu`/`--memory`
  if exports/MC feel slow). Note the **service URL** it prints → that's `ENGINE_EXTRACT_URL` *and*
  the ID-token **audience** (they must be the same string).
- `SUPABASE_ANON_KEY` is a public value; fine as an env var (or move to a secret if you prefer).

## 4. Build + push the WEB image  (uses `cloudbuild.yaml`)
The web repo ships a `cloudbuild.yaml` that builds on Cloud Build (no local Docker) and
passes every client `NEXT_PUBLIC_*` value — they're inlined into the browser bundle at
build time, so they must be set now, not at runtime. It validates the required ones are
non-empty first (a blank value would ship a broken-login / demo-mode image), then pushes
to Artifact Registry. One command:
```bash
cd ../startuplan_web
TAG=$(git rev-parse --short HEAD)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=\
_IMAGE=europe-west1-docker.pkg.dev/startuplan-prod/startuplan/web:$TAG,\
_GIT_SHA=$TAG,\
_SUPABASE_URL=https://XXXX.supabase.co,\
_SUPABASE_ANON_KEY=eyJ...,\
_SITE_URL=https://<web-url>,\
_TURNSTILE_SITE_KEY=0x...,\
_API_URL=https://<web-url>
# optional (defaults shown): _OAUTH_GOOGLE=true _OAUTH_APPLE=false _TRIAL_UPGRADES=false
# _GIT_SHA is REQUIRED (the build fails without it). It stamps the deployed commit
# into the app — check it in Settings ("build <sha>") after deploy to confirm the
# live code matches `git rev-parse --short HEAD`.
```
> All of these are **PUBLIC** values — safe as substitutions. The real secrets (service-role
> key, Stripe, Turnstile *secret*) go in at deploy (step 5) via `--set-secrets`, never baked
> into the image.
> `<web-url>` is chicken-and-egg: deploy once to learn the URL, then rebuild with the real
> `_SITE_URL` / `_API_URL`, or map a custom domain up front and use that.

## 4b. (OPTIONAL — B1 only) Network hiding — VPC connector + Cloud NAT  (~15 min, ~$40–55/mo)
**Skip this for the beta.** The chosen ID-token path does not need it. Do this *only* if you later
want to also hide the engine behind internal ingress (B1): the web then reaches it *through the
VPC*, and the web's other egress (Supabase, Stripe) needs a NAT to reach the internet. If you do,
also change the engine back to `--ingress internal` in step 3 and add the `--vpc-connector` line to
the web deploy in step 5.
```bash
gcloud services enable vpcaccess.googleapis.com compute.googleapis.com

# Serverless VPC Access connector (same region; a free /28 in the default VPC)
gcloud compute networks vpc-access connectors create startuplan-conn \
  --region europe-west1 --range 10.8.0.0/28

# Cloud NAT so the web's all-traffic egress still reaches the public internet
gcloud compute routers create startuplan-router \
  --region europe-west1 --network default
gcloud compute routers nats create startuplan-nat \
  --router startuplan-router --region europe-west1 \
  --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges
```
> Uses the `default` VPC. The connector's `/28` must not overlap an existing subnet.

## 5. Deploy the WEB (public)
Runtime server env (secrets + the engine URL). `NEXT_PUBLIC_*` are already baked. On Cloud Run the
web auto-mints the engine ID token (it detects `K_SERVICE`; no extra env needed). The VPC line is
**B1-only** — left commented out for the chosen ID-token path.
```bash
gcloud run deploy startuplan-web \
  --image "$IMG" \
  --region europe-west1 \
  --ingress all --allow-unauthenticated \
  --min-instances 0 --max-instances 2 \
  --cpu 1 --memory 512Mi \
  --set-env-vars ENGINE_EXTRACT_URL=<engine-internal-url>,STRIPE_TAX_ENABLED=false,ALLOW_TRIAL_UPGRADES=false,STRIPE_PRICE_PLAN=price_...,STRIPE_PRICE_BANKABLE=price_...,STRIPE_PRICE_ADVISOR=price_... \
  --set-secrets SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,TURNSTILE_SECRET_KEY=TURNSTILE_SECRET_KEY:latest,EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest
  # B1 ONLY (optional network hiding, step 4b) — append to the line above:
  #   --vpc-connector startuplan-conn --vpc-egress all-traffic
```
- `ENGINE_EXTRACT_URL` is the engine's **service URL** from step 3 — the same string the web uses
  as the ID-token audience. Keep them identical or Cloud Run IAM rejects the token.
- `EXTRACT_SERVICE_TOKEN` stays set here too: it's the `X-Extract-Token` app backstop.
- **`ALLOW_TRIAL_UPGRADES`**: leave **off** (default). Turn on **only** if the beta needs the
  no-payment self-upgrade for testers; purge trial grants before public.
- The engine needs **no** Stripe secrets (and rejects them) — all Stripe lives on the web.

## 6. Wire the two services together
- **Grant the web permission to call the engine (the ID-token lock).** The web's runtime service
  account needs `roles/run.invoker` on the engine, or every call comes back **403** from Cloud Run.
  If you didn't set `--service-account` on the web, it runs as the default compute SA:
  ```bash
  PROJECT_NUMBER=$(gcloud projects describe startuplan-prod --format='value(projectNumber)')
  WEB_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com   # or your dedicated web SA
  gcloud run services add-iam-policy-binding startuplan-engine \
    --region europe-west1 \
    --member="serviceAccount:${WEB_SA}" \
    --role=roles/run.invoker
  ```
  Quick check: `curl https://<engine-url>/health` from your laptop should return **403** (no token),
  while the web app's engine calls succeed. 403 from the browser path = the grant is missing or the
  audience ≠ `ENGINE_EXTRACT_URL`.
- Set the engine's `APP_URL`/`LANDING_PAGE_URL` and the web's `NEXT_PUBLIC_SITE_URL`/`ENGINE_EXTRACT_URL`
  to the real URLs (redeploy the step whose URL you didn't know yet).
- **Supabase:** add the web's URL to Auth → URL Configuration (redirect allowlist) and finish the
  **Google OAuth** provider config (client id/secret). Confirm `NEXT_PUBLIC_OAUTH_GOOGLE=true`.

## 7. Pre-open gates (don't skip — these protect the beta)
- [ ] **Invite-only** — confirm the allowlist / beta flag is enforced (open signup OFF). *(Verify this exists in code; it's a Timeline item.)*
- [ ] **Spend caps** — hard monthly caps + budget alerts on the OpenAI (and Anthropic) accounts.
- [ ] **Backups** — Supabase PITR ON, and run one restore drill into a throwaway DB.
### Pre-beta RLS re-audit on the LIVE database
**This is the step that actually protects user data.** The drift-guard test checks the *repo*; this
confirms the *deployed* database. Run each in the Supabase SQL editor (as the admin), tick when green:

- [ ] **RLS on everywhere.**
      `select tablename, rowsecurity from pg_tables where schemaname='public' order by 1;`
      → every row must be `rowsecurity = true`. Any `false` is a hole — fix before opening.
- [ ] **Every policy is owner-scoped.**
      `select tablename, policyname, cmd, qual, with_check from pg_policies where schemaname='public' order by 1,2;`
      → every policy on a user table references `auth.uid()` — directly (`id = auth.uid()`,
      `user_id = auth.uid()`) or via a `projects … owner_id = auth.uid()` subquery. **No** policy is
      `using (true)` / `with check (true)`.
- [ ] **Entitlements are server-write-only.** `tier_grants` (also `payments`, `subscriptions`,
      `entitlements`) have **no insert/update policy for the `authenticated` role** — only the service
      role (the Stripe webhook) writes them. A signed-in user must not be able to grant themselves a tier.
- [ ] **The real test — cross-user isolation (empirical, stronger than reading policies).** Sign in as
      test user A, and with A's token (anon/authenticated key — NOT the service key) try to read and write
      user B's data: `select * from projects;` returns **only A's** rows, and an update to one of B's rows
      is **rejected**. Repeat for `profiles` / `payments`.
- [ ] **`profiles.plan` can't be self-escalated.** With A's token, `update profiles set plan='premium'
      where id = <A>` must either be rejected or be irrelevant (the server no longer trusts `profiles.plan`
      after the Phase-0 fix — confirm both: the code change is deployed AND the column isn't a backdoor).
- [ ] **Service-role key is server-only.** It must never reach the browser bundle:
      `grep -r "service_role" .next/static` (in the built web) finds nothing, and the key lives only in
      Secret Manager — never in `NEXT_PUBLIC_*`, never in git.
- [ ] **Storage is private.** The `exports` bucket is `public = false`; files are served via signed URLs,
      and the `storage.objects` read policy is scoped to the user's own folder (`{user_id}/…`).

> Re-run this whole block whenever a table or policy changes, and once more just before public launch.

### Engine door (the ID-token lock)
- [ ] **Unauthenticated calls are refused at the edge.** `curl https://<engine-url>/health` from
      your laptop (no token) returns **403** — Cloud Run IAM rejecting it before the app runs.
- [ ] **The web can reach the engine.** Loading the dashboard computes results (no `engine_unauthorized`
      / 403 in the web logs) — i.e. the `roles/run.invoker` grant and the audience are correct.

## 8. Smoke test
```bash
# Engine is IAM-locked (--no-allow-unauthenticated). From your laptop, no identity:
curl -sS -o /dev/null -w '%{http_code}\n' https://<engine-url>/health        # 403 — Cloud Run IAM, good

# With a Google ID token for the engine audience (what the web does automatically):
TOKEN=$(gcloud auth print-identity-token --audiences=https://<engine-url>)
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Extract-Token: $EXTRACT_TOKEN" \
  https://<engine-url>/health                                                # {"ok":true,...}
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
4. **The engine's lock is already strong.** ✅ The beta runs the Google **ID-token**
   setup — engine `--no-allow-unauthenticated` (Cloud Run IAM) with the web minting an ID
   token per call, plus the `X-Extract-Token` app backstop. A leaked password alone can't
   get in. Public needs **no change** here; the only optional extra is B1 network hiding
   (internal ingress + VPC/NAT, step 4b), and that's hardening, not a requirement.
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
