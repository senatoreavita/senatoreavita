# INFRA — provision-early checklist (Google Cloud)

Optional, ~20 min. Clears the Google Cloud runway **before** deploy, without
touching app code — so finish-first is unbroken. Doing it early de-risks the
boring account-plumbing surprises (billing links, IAM, quotas) that otherwise
bite during the week-5–6 deploy window.

> **Two different "billings" — do not confuse:**
> - **Google Cloud billing account** = *you* paying *Google* for cloud usage. ← this file
> - **Stripe / Paddle** = your *customers* paying *you*. ← separate payments workstream.
>
> Google Cloud billing account already in use: **`01E0C6-9B81CE-C0FBB3`**.

Scope: project **`startuplan-prod`**, region **`europe-west1`**.
The project already exists with billing linked (startuplan.ai / Streamlit runs
there), so steps 0–1 are **verify**, not create. Steps 3–4 are the real value.

---

## 0. Point gcloud at the right project
```bash
gcloud config set project startuplan-prod
gcloud config set run/region europe-west1
```

## 1. Verify project + billing (should already be linked)
```bash
gcloud billing projects describe startuplan-prod
# Only if billingEnabled: false —
# gcloud billing projects link startuplan-prod --billing-account=01E0C6-9B81CE-C0FBB3
```

## 2. Enable the APIs the deploy will need
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## 3. Create the image registry (where container images live)
```bash
gcloud artifacts repositories create startuplan \
  --repository-format=docker \
  --location=europe-west1 \
  --description="StartUPlan web + engine images"
```

## 4. Create the secrets vault entries (empty shells now; fill values later)

🔑 **Never paste real keys into chat or into shell history.** Create the secret,
then add its value by pasting at the prompt and ending with Ctrl-D:
```bash
gcloud secrets create ANTHROPIC_API_KEY --replication-policy=automatic
gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-   # paste value, then Ctrl-D
```
Secrets to `create` (names only — no values here):

- **Engine (startuplan-core):** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `EXTRACT_SERVICE_TOKEN`, `RESEND_API_KEY`
- **Web (StartUPlan_Web):** `SUPABASE_SERVICE_ROLE_KEY`, `TURNSTILE_SECRET_KEY`,
  `EXTRACT_SERVICE_TOKEN` (same value as the engine)

> Public `NEXT_PUBLIC_*` values are **not** secrets — they go in the build config,
> not Secret Manager.

## 5. (Optional) A dedicated deploy service account
```bash
gcloud iam service-accounts create startuplan-deployer \
  --display-name="StartUPlan deploy"
```
Roles (deploy / registry-write / secret-access) get granted when we wire the
actual deploy — not needed now.

---

## After this
The runway is clear. When the apps are finished (weeks 5–6), deploy is just:
build image → push to the `startuplan` registry → `gcloud run deploy`, with
secrets mounted from Secret Manager (keys never in code).
