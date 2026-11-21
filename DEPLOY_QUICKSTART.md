# Deploy quickstart (B3) — condensed command walkthrough

The short, copy-paste version of **step B3** (deploy both services). The full
reference, with every flag explained and the B1/B2 alternatives, is in
`DEPLOY_CLOUD_RUN.md` — read that first if anything here is unclear. Run these in
**Google Cloud Shell**. The engine door is the chosen **ID-token** path:
engine `--no-allow-unauthenticated` (Cloud Run IAM) + a Google ID token from the
web + an `X-Extract-Token` app backstop.

> Fill the `XXXX` / `price_...` / `0x...` / `eyJ...` placeholders from Secret
> Manager and your Supabase / Stripe / Turnstile dashboards.

## 0. One-time setup
```bash
export PROJECT=startuplan-prod
export REGION=europe-west1
export AR=$REGION-docker.pkg.dev/$PROJECT/startuplan
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories create startuplan --repository-format=docker \
  --location=$REGION 2>/dev/null || true
```

## 1. Secrets → Secret Manager
```bash
for S in EXTRACT_SERVICE_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY RESEND_API_KEY \
         SUPABASE_SERVICE_ROLE_KEY STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET \
         TURNSTILE_SECRET_KEY; do
  gcloud secrets create $S --replication-policy=automatic 2>/dev/null || true
  echo "→ paste value for $S then Ctrl-D:"; gcloud secrets versions add $S --data-file=-
done
# EXTRACT_SERVICE_TOKEN: generate once → openssl rand -hex 32
```

## 2. Engine: build → deploy (IAM-locked, public URL)
```bash
cd startuplan-core
TAG=$(git rev-parse --short HEAD); IMG=$AR/engine:$TAG
gcloud builds submit --tag "$IMG" .
gcloud run deploy startuplan-engine --image "$IMG" --region $REGION \
  --ingress all --no-allow-unauthenticated \
  --min-instances 0 --max-instances 1 --cpu 1 --memory 1Gi --concurrency 8 --timeout 120 \
  --set-env-vars ENVIRONMENT=staging,AI_PROVIDER=openai,STARTUPLAN_DEBUG=false,SUPABASE_URL=https://XXXX.supabase.co,SUPABASE_ANON_KEY=eyJ...,APP_URL=https://PLACEHOLDER,LANDING_PAGE_URL=https://PLACEHOLDER \
  --set-secrets EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest

export ENGINE_URL=$(gcloud run services describe startuplan-engine --region $REGION --format='value(status.url)')
echo "ENGINE_URL = $ENGINE_URL"   # == ENGINE_EXTRACT_URL == the ID-token audience
```
> **Only** those 7 env vars — the engine is `extra="forbid"`; any stray var stops it booting.

## 3. ★ ID-token lock: let the web SA invoke the engine
```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
WEB_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com   # default compute SA (or a dedicated web SA)
gcloud run services add-iam-policy-binding startuplan-engine --region $REGION \
  --member="serviceAccount:${WEB_SA}" --role=roles/run.invoker
curl -s -o /dev/null -w 'engine unauth: %{http_code}\n' $ENGINE_URL/health   # expect 403
```

## 4. Web: build (bakes NEXT_PUBLIC_*) → deploy
```bash
cd ../startuplan_web
TAG=$(git rev-parse --short HEAD)
gcloud builds submit --config cloudbuild.yaml --substitutions=\
_IMAGE=$AR/web:$TAG,_SUPABASE_URL=https://XXXX.supabase.co,_SUPABASE_ANON_KEY=eyJ...,\
_SITE_URL=https://PLACEHOLDER,_TURNSTILE_SITE_KEY=0x...,_API_URL=$ENGINE_URL

gcloud run deploy startuplan-web --image $AR/web:$TAG --region $REGION \
  --ingress all --allow-unauthenticated --min-instances 0 --max-instances 2 --cpu 1 --memory 512Mi \
  --set-env-vars ENGINE_EXTRACT_URL=$ENGINE_URL,STRIPE_TAX_ENABLED=false,ALLOW_TRIAL_UPGRADES=false,STRIPE_PRICE_PLAN=price_...,STRIPE_PRICE_BANKABLE=price_...,STRIPE_PRICE_ADVISOR=price_... \
  --set-secrets SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,TURNSTILE_SECRET_KEY=TURNSTILE_SECRET_KEY:latest,EXTRACT_SERVICE_TOKEN=EXTRACT_SERVICE_TOKEN:latest

export WEB_URL=$(gcloud run services describe startuplan-web --region $REGION --format='value(status.url)')
echo "WEB_URL = $WEB_URL"
```
> `_API_URL` is required by the build validator but not read by app code — any URL satisfies it.

## 5. Close the chicken-and-egg (skip the web rebuild if you mapped a domain first)
```bash
cd ../startuplan_web
gcloud builds submit --config cloudbuild.yaml --substitutions=\
_IMAGE=$AR/web:$(git rev-parse --short HEAD),_SUPABASE_URL=https://XXXX.supabase.co,\
_SUPABASE_ANON_KEY=eyJ...,_SITE_URL=$WEB_URL,_TURNSTILE_SITE_KEY=0x...,_API_URL=$ENGINE_URL
gcloud run deploy startuplan-web --image $AR/web:$(git rev-parse --short HEAD) --region $REGION

gcloud run services update startuplan-engine --region $REGION \
  --update-env-vars APP_URL=$WEB_URL,LANDING_PAGE_URL=$WEB_URL
```

## 6. Smoke test
```bash
curl -s -o /dev/null -w 'engine unauth: %{http_code}\n' $ENGINE_URL/health   # 403 = IAM working
TOKEN=$(gcloud auth print-identity-token --audiences=$ENGINE_URL)
curl -s -H "Authorization: Bearer $TOKEN" $ENGINE_URL/health                  # {"ok":true,...}
# then in a browser at $WEB_URL: sign in → compute → export → assistant
```

## The three deploy-day failure modes
- **403 on every engine call from the app** → the invoker grant (step 3) is missing, or
  `ENGINE_EXTRACT_URL` ≠ the ID-token audience. Same root URL, no trailing path.
- **Engine won't boot** → a stray `--set-env-vars` that isn't one of the 7 known fields
  (`extra="forbid"`). Pass only what's in step 2.
- **Broken login / demo-mode UI** → a blank `NEXT_PUBLIC_*` at build time; the
  `cloudbuild.yaml` validator catches the required ones first.
