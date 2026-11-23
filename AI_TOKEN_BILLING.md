# AI Token Metering & Top-Up — Pro-Memoria (build spec)

**Status:** design, ready to build · **Author:** planning session, 2026-11-23
**Repos:** `startuplan-core` (engine, Python/FastAPI) · `StartUPlan_Web` (web, Next.js 16)
**Companion:** `tiers.catalog.json`, the Pricing Model artifact, `DEPLOY_STATE.md`.

> **Naming:** the feature is **"tokens" / "token wallet"**. Do **not** call it "credits" —
> `credit` is already the Stripe *upgrade-proration* concept (`tiers.ts` `UpgradeOffer.mode:"credit"`,
> `creditWindowDays`, `tiers.price.credit` i18n). A collision there would be a real bug.

---

## 0. What we're building (one paragraph)

Meter real AI **token usage (input/output)** per user on every LLM-powered action, show the
user a **token balance** (unit = tokens) with a **remaining-allowance pie on the AI dialog** and a
**usage history (+/-)**, and let them **top up** by buying more tokens (one-time Stripe purchase).
AI features are **gated by balance**; deterministic modelling and the Excel workbook stay **free**.
The owner gets a **COGS dashboard** (cost by day/feature/model, per customer, margin = revenue −
provider cost) and a cost-spike alert. Power users can **BYOK** (bring their own provider key) and
bypass metering. Ship in two phases: **Phase 1 = measure** (log usage, no gating), **Phase 2 =
enforce** (balance, deduct, top-up) priced from Phase-1 data.

### Decisions locked (from the brief)
| # | Decision |
|---|---|
| Unit | **Tokens** — balance + top-ups in tokens; history shows in/out; a pie of free-allowance-remaining on the AI dialog. |
| Metering | **Token-accurate** (real input/output + cache tokens), not flat-per-action. |
| What consumes | **Extract · Assistant · Guided (build/next) · PDF/PPT/guide narrative polish**. Deterministic compute + **Excel (xlsx) = free**. |
| Lifetime | Allowance tokens **expire with the access window** (90d/365d). Purchased tokens valid **12 months**, **preserved** across window lapses, usable in any active window. Consume **allowance first, earliest-expiry first**. |
| Free `draft` tier | Small **trial** token allowance; **no Excel/PDF/PPT export** (export stays paid — the conversion lever). |
| Numbers (allowance/pack sizes/prices/markup) | **Deferred to Phase-1 data; live in config, not code.** |
| Views | **User:** balance + usage history + top-up. **Owner/admin:** per-customer usage + COGS by day/feature/model + margin. |
| BYOK | **Yes** (Advisor + opt-in): user key, usage logged (visibility) but **not deducted**. |

---

## 1. Current state (grounded in the code)

### Engine (`startuplan-core`)
- LLM call sites, spread across `core/ai/`: `plan_extractor.py` (extract; default **Anthropic** `claude-haiku-4-5`, or OpenAI `gpt-4o-mini`), `assistant.py` (chat), `plan_writer.py` (`polish_narrative` — the **PDF/PPT/guide** prose), `reviewer.py`, `guided_interpreter.py` (guided build/next). Each constructs its own `OpenAI(...)` / `Anthropic(...)` client and calls `chat.completions.create` / `messages.create`.
- **Only `assistant.py` reports usage.** It has `estimate_cost(model, in, out)` + `_usage_zero()` and returns `usage {input_tokens, output_tokens, model, cost_usd}`.
- **Price table is incomplete & OpenAI-only:** `assistant._MODEL_PRICES = {gpt-4o-mini:(0.15,0.60), gpt-4o:(2.50,10.0)}`. The extractor's default **Anthropic Haiku is unpriced** → token-accurate cost is currently blind to the single most-used model. No cache-token pricing.
- `/plan/export` runs `plan_writer.polish_narrative` for `fmt in (pdf, pptx, guide)`; `xlsx` is deterministic (no LLM).

### Web (`StartUPlan_Web`)
- **AI proxy routes** (`src/app/api/*`, `runtime="nodejs"`), common shape: `readJsonCapped` → `verifyAuth(request)` → `rateLimited(...)` → `engineAuthHeaders(engineUrl)` → `fetch(ENGINE_EXTRACT_URL/<path>)` → return engine JSON. User id **only** from `verifyAuth` (service-role `admin.auth.getUser(token)`). No PII/user-id sent to the engine.
  - `extract` → `/extract` · `assistant` → `/plan/assistant` (resolves tier, forwards `access_tier`, uses `overDailyBudget`) · `export` → `/plan/export` (binary response) · `guided` → `/guided/build` · `guided-next` → `/guided/next` · `refine` → `/plan/refine` (**no LLM**).
- **Guard pattern to mirror** — `src/lib/apiGuard.ts`: `verifyAuth(request): AuthResult{ok,userId,admin}`, `rateLimited(key,max,windowMs)`, `rateKeyFrom`, `readJsonCapped`. `src/lib/rateBudget.ts`: `overDailyBudget(admin,key,max)` → `admin.rpc("increment_api_usage",...)` against `api_daily_usage` (per-day **request** count, **not tokens**; fail-open).
- **Stripe webhook** — `src/app/api/stripe-webhook/route.ts` is *the only writer of paid grants*. Verifies raw-body signature, `switch(event.type)`; on `checkout.session.completed` calls `writeGrant(admin, ctx)` from `src/lib/grants.server.ts` — a **delete-then-insert** into `public.tier_grants` keyed on `source_sku="stripe:<planId>"`, `expires_at = now + plan.windowDays*day`. **No RPC; direct service-role writes.** `contextFrom(metadata,…)` reconstructs `{user_id, plan_id, tier_id, terms_accepted_at}`.
- **Checkout** — `src/app/api/checkout/route.ts`: `priceIdForPlan(plan.id)` → `process.env["STRIPE_PRICE_<PLAN>"]`; `checkoutModeForPlan` → `"subscription"` iff `plan.kind==="subscription"` else `"payment"`. Catalog = tiers/windows; env = price ids.
- **Schema / access** — service-role client `src/lib/supabaseAdmin.ts getSupabaseAdmin()`; browser client `src/lib/supabase.ts getSupabase()`. `tier_grants(id,user_id,tier_id,granted_at,expires_at,source_sku,created_at)`, RLS on, **SELECT-only** policy `"read own grants" using (auth.uid()=user_id)` → service-role-write-only. `profiles.plan` is **deliberately not read** for entitlement (user-writable → self-grant hole). `api_daily_usage` + `increment_api_usage(p_key,p_day,p_max)` SECURITY DEFINER, RLS-on/no-policies.
- **Entitlement resolution** — pure: `src/config/grants.ts` `resolveEffectiveTier(grants,now)`, `effectiveExpiry(grants,now)`. Server: `src/lib/resolveUserTier.ts resolveUserTierServer(admin,userId)` (60s cache, fail-closed tier_0). Client (display): `src/lib/useUserTier.ts useUserTier() → {tier,plan,expiresAt,loading}`.
- **UI mounts** — all AI dialogs in `src/components/dashboard2/DashboardOverlays.tsx`. **`AssistantDrawer.tsx` already parses the engine `usage`** (`AssistantUsage{input_tokens,output_tokens,model,cost_usd}`), accumulates `sessionCost`, and renders a cost chip in the footer (~L480) next to the model-tier selector — the natural home for the **balance + pie + "top up"**. `DescribeProjectDialog.tsx` (extract) and `ExportDialog.tsx` (format/scope + Lock/upgrade UI) are the other mounts. Sidebar `TierBadge.tsx` (reads `useUserTier`) is the natural neighbour for a **balance readout**.
- **i18n** — `messages/{en,fr,it,uk}.json`, `next-intl`. Add a new `tokens` group across all four.
- **Tests** — Vitest 3, tests next to source: route tests `src/app/api/<r>/route.test.ts`, lib `src/lib/*.test.ts`, config `src/config/*.test.ts`, RLS guard `supabase/migrations/rls-coverage.test.ts` (**new tables must be added to its `EXPECTED_TABLES`**).

### Gaps to close
No `ai_usage` / token / wallet table exists. Nothing persists the engine's `usage`. Price table OpenAI-only + no cache rates. Only the assistant reports usage. No balance/deduct/top-up anywhere.

---

## 2. Architecture

```
            ┌──────────────────────── Engine (startuplan-core) ────────────────────────┐
            │  core/ai/llm.py   complete(prompt,…) -> (text, Usage)  ◄── ONE seam       │
 all AI  ───┤    • normalises usage: OpenAI prompt/completion + Anthropic input/output  │
 callsites  │      + cache_read/cache_write                                             │
            │  core/ai/pricing.py  price(model) -> rates (both providers + cache)       │
            │  every /endpoint returns `usage` (export: via X-AI-Usage header)          │
            └───────────────────────────────────────────────────────────────────────────┘
                              │  engine JSON incl. usage
            ┌─────────────────▼──────────────── Web (StartUPlan_Web) ───────────────────┐
 Phase 1    │  route → (call engine) → aiUsage.logAiUsage(admin,{userId,feature,usage}) │
            │                                        └─► public.ai_usage_log (COGS)     │
 Phase 2    │  route → wallet.reserve(max) → call engine → wallet.settle(actual)        │
            │           (insufficient → 402)         (error/refusal → release)          │
            │  tokenWallet.ts → RPCs consume_tokens / grant_tokens over token_grants    │
            │  stripe-webhook → grant branch: allowance (on tier buy) · pack (top-up)   │
            └───────────────────────────────────────────────────────────────────────────┘
```

Principles (inherited from the existing security model): **all writes server-side via the
service role**; user tables are **read-own RLS, no write policy**; mutations go through
**SECURITY DEFINER** RPCs; **idempotent** on Stripe event ids; **never log prompt/response
content** — only token counts + model.

---

## 3. Data model (DDL)

### Phase 1 — measurement
```sql
-- Every LLM call's provider usage + our COGS. Append-only. Service-role write.
create table public.ai_usage_log (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid references auth.users(id) on delete set null,
  feature            text not null,          -- 'extract'|'assistant'|'guided'|'narrative'
  provider           text not null,          -- 'openai'|'anthropic'
  model              text not null,
  input_tokens       integer not null default 0,
  output_tokens      integer not null default 0,
  cache_read_tokens  integer not null default 0,
  cache_write_tokens integer not null default 0,
  cost_usd           numeric(12,6) not null default 0,   -- provider COGS (our cost)
  billed_tokens      integer not null default 0,          -- what the user paid (Phase 2; 0 in P1/BYOK)
  byok               boolean not null default false,
  project_id         uuid,
  request_id         text,                                -- correlation / debugging
  created_at         timestamptz not null default now()
);
create index ai_usage_log_user_day_idx on public.ai_usage_log (user_id, created_at);
create index ai_usage_log_feat_idx     on public.ai_usage_log (feature, created_at);
alter table public.ai_usage_log enable row level security;
create policy "read own usage" on public.ai_usage_log for select using (auth.uid() = user_id);
-- no insert/update/delete policy → writes only via service role. Admin COGS reads via service role.
```

### Phase 2 — the wallet (buckets + audit)
```sql
-- Balance buckets. remaining is the live balance; expiry + kind drive consume order.
create table public.token_grants (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  kind        text not null check (kind in ('allowance','purchased','trial','adjustment')),
  total       bigint not null,
  remaining   bigint not null check (remaining >= 0),
  expires_at  timestamptz,                               -- null = no expiry
  source_ref  text,                                      -- 'stripe:<event_id>' | 'tier:<sku>' | 'trial'
  created_at  timestamptz not null default now()
);
create unique index token_grants_source_uniq on public.token_grants (source_ref) where source_ref is not null; -- idempotency
create index token_grants_user_live_idx on public.token_grants (user_id, expires_at) where remaining > 0;
alter table public.token_grants enable row level security;
create policy "read own token grants" on public.token_grants for select using (auth.uid() = user_id);

-- Append-only audit of every mutation (grant / consume / refund / expiry).
create table public.token_ledger (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  delta        bigint not null,                          -- + grant, - consume
  reason       text not null,                            -- 'grant'|'consume'|'refund'|'expiry'
  grant_id     uuid references public.token_grants(id),
  source_ref   text,                                     -- links to usage_log.id or stripe event
  balance_after bigint,
  created_at   timestamptz not null default now()
);
create index token_ledger_user_idx on public.token_ledger (user_id, created_at);
alter table public.token_ledger enable row level security;
create policy "read own token ledger" on public.token_ledger for select using (auth.uid() = user_id);
```
> Add `ai_usage_log`, `token_grants`, `token_ledger` to `rls-coverage.test.ts` `EXPECTED_TABLES`.
> `token_grants`/`token_ledger` have a `user_id` → the test requires owner-scoped policies (above satisfy it).

### BYOK key storage
```sql
create table public.byok_keys (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  provider     text not null check (provider in ('openai','anthropic')),
  key_ciphertext text not null,     -- app-encrypted (NEVER plaintext); decrypt only server-side
  created_at   timestamptz not null default now()
);
alter table public.byok_keys enable row level security;   -- RLS on, NO select policy: service-role only; user never reads the key back
```
> The key is **encrypted by the app** before storage (e.g. libsodium sealed box with a server key in Secret Manager) and only decrypted in the web server when forwarding a call. Never returned to the browser; never logged.

---

## 4. RPCs (SECURITY DEFINER, service-role only)

```sql
-- Idempotent grant. Re-running with the same source_ref is a no-op (returns current balance).
create or replace function public.grant_tokens(
  p_user uuid, p_amount bigint, p_kind text, p_expires_at timestamptz, p_source_ref text
) returns bigint language plpgsql security definer set search_path = public as $$
declare v_balance bigint;
begin
  if p_source_ref is not null and exists (select 1 from token_grants where source_ref = p_source_ref)
    then return public.token_balance(p_user); end if;                       -- idempotent
  insert into token_grants(user_id,kind,total,remaining,expires_at,source_ref)
    values (p_user,p_kind,p_amount,p_amount,p_expires_at,p_source_ref);
  insert into token_ledger(user_id,delta,reason,source_ref) values (p_user,p_amount,'grant',p_source_ref);
  return public.token_balance(p_user);
end; $$;

-- Live balance = sum of non-expired remaining.
create or replace function public.token_balance(p_user uuid)
returns bigint language sql security definer set search_path = public as $$
  select coalesce(sum(remaining),0) from token_grants
   where user_id = p_user and remaining > 0 and (expires_at is null or expires_at > now());
$$;

-- Atomic consume across buckets: allowance/trial first, then earliest expiry. Skips expired.
-- Returns remaining balance on success, or -1 if insufficient (deducts NOTHING).
create or replace function public.consume_tokens(p_user uuid, p_amount bigint, p_source_ref text)
returns bigint language plpgsql security definer set search_path = public as $$
declare r record; left bigint := p_amount; take bigint;
begin
  if p_amount <= 0 then return public.token_balance(p_user); end if;
  if public.token_balance(p_user) < p_amount then return -1; end if;        -- insufficient → no-op
  for r in select id, remaining from token_grants
            where user_id=p_user and remaining>0 and (expires_at is null or expires_at>now())
            order by (kind <> 'allowance' and kind <> 'trial'),              -- allowance/trial first
                     expires_at nulls last                                   -- then soonest expiry
            for update
  loop
    exit when left <= 0;
    take := least(left, r.remaining);
    update token_grants set remaining = remaining - take where id = r.id;
    insert into token_ledger(user_id,delta,reason,grant_id,source_ref) values (p_user,-take,'consume',r.id,p_source_ref);
    left := left - take;
  end loop;
  return public.token_balance(p_user);
end; $$;

-- Refund (release a reservation / refund a failed call). source_ref = the consume's ref.
create or replace function public.refund_tokens(p_user uuid, p_amount bigint, p_source_ref text)
returns bigint language plpgsql security definer set search_path = public as $$
begin
  -- simplest correct policy: add back as a short-lived 'adjustment' grant tied to the same ref.
  perform public.grant_tokens(p_user, p_amount, 'adjustment', now() + interval '365 days', p_source_ref || ':refund');
  return public.token_balance(p_user);
end; $$;

revoke all on function public.grant_tokens(uuid,bigint,text,timestamptz,text)   from public, anon, authenticated;
revoke all on function public.consume_tokens(uuid,bigint,text)                  from public, anon, authenticated;
revoke all on function public.refund_tokens(uuid,bigint,text)                   from public, anon, authenticated;
-- token_balance may stay callable by the owner for the balance view, or be read via the service role.
```

**Reserve-then-settle** (the professional pattern, since output is capped):
1. **Reserve** before the call: `max = estimate_input + max_output_tokens` → `consume_tokens(user, max, ref)`; `-1` → **402 insufficient**.
2. **Call** the engine.
3. **Settle** after: `actual = usage.total`; `refund_tokens(user, max - actual, ref)` (refund the unused reserve). On engine **error/refusal**: `refund_tokens(user, max, ref)` — **no charge**.
This guarantees the balance never goes negative and failed calls cost nothing.

---

## 5. Engine changes (per file)

1. **`core/ai/pricing.py` (new, single source of truth).** Move + complete `_MODEL_PRICES`:
   both providers, input/output **and** cache rates (Anthropic cache-write ≈1.25× input, cache-read ≈0.1× input; OpenAI cached-input discount). Include the real models in use (`claude-haiku-4-5`, `gpt-4o-mini`, any Sonnet/Opus/4o used by the assistant tiers). Add a `PRICES_VERIFIED = "YYYY-MM-DD"` stamp and a helper `cost_usd(model, in, out, cache_read, cache_write)`. *(Numbers: verify against the Anthropic/OpenAI pricing pages at build time.)*
2. **`core/ai/llm.py` (new wrapper).** `complete(provider, model, messages, max_output_tokens, api_key, …) -> (text, Usage)` where `Usage = {provider, model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd}`. It owns the `OpenAI`/`Anthropic` client call and the provider-specific usage extraction (OpenAI `prompt_tokens/completion_tokens`; Anthropic `input_tokens/output_tokens` + `cache_creation_input_tokens/cache_read_input_tokens`). `cost_usd` from `pricing.py`.
3. **Route every call site through it:** `plan_extractor`, `plan_writer.polish_narrative`, `reviewer`, `guided_interpreter`, and refactor `assistant.py` to use it (dropping its private price table). Each returns `usage` alongside its result.
4. **Endpoints return `usage`:** add `usage` to the JSON of `/extract`, `/guided/build`, `/guided/next`. `/plan/refine` is no-LLM → unchanged. `/plan/assistant` already returns it. **`/plan/export`** body is the binary file → return usage in a **`X-AI-Usage` response header** (JSON) for `pdf/pptx/guide`; `xlsx` sets it to zero/omits it.
5. **BYOK:** accept an optional `byok_key` in the request (web forwards it only for BYOK users); when present the wrapper uses it and marks `usage.byok=true`.

> The engine stays **stateless** about billing — it only *measures*. All persistence + deduction is the web's job (it holds the service-role key + the user identity). Keep it that way.

---

## 6. Web changes (per file)

### Phase 1 — observability (ships first, no gating)
- **`src/lib/aiUsage.ts` (new):** `logAiUsage(admin, { userId, feature, usage, projectId?, byok? })` → insert one `ai_usage_log` row via the service-role client. **Fail-open** (a logging error must never break the user's request).
- **In each AI route**, after a successful engine call, read `usage` (JSON body; for `export`, parse the `X-AI-Usage` header) and call `logAiUsage(auth.admin, { userId: auth.userId, feature, usage })`. Routes: `extract`, `assistant`, `guided`, `guided-next`, `export`. (`refine` = no LLM → skip.)
- **Migration** `..._ai_usage_log.sql` (DDL §3) + add to `rls-coverage.test.ts`.
- **A minimal cost view**: start with SQL rollups (run in the Supabase SQL editor, like the RLS audit) — cost/day, avg cost per feature, per model, per user. Promote to the admin page in Phase 2.

### Phase 2 — enforcement + top-up (behind a kill-switch)
- **`src/lib/tokenWallet.ts` (new):** `getBalance(admin,userId)`, `reserveTokens(admin,userId,max,ref)`, `settle(admin,userId,ref,reserved,actual)`, `grantTokens(admin,userId,amount,kind,expiresAt,ref)` — thin wrappers over the RPCs. All service-role.
- **Per metered route:** `const ref = crypto.randomUUID()`. If **not BYOK** and `AI_METERING_ENABLED`: `reserve` the pre-flight max → `-1` ⇒ `402 {error:"insufficient_tokens", balance}`. Call engine. `settle` to actual (refund the diff); on engine error/refusal `refund` the whole reserve. Then `logAiUsage(..., billed_tokens: actual)`. **BYOK users:** skip reserve/settle, still `logAiUsage(byok:true)`.
- **Grants on tier purchase:** in `grants.server.ts writeGrant` (or the webhook branch that calls it), after writing the tier grant, `grantTokens(allowance = plan.aiTokens, expiresAt = the tier window, ref = "tier:"+source_sku)`. Idempotent via `source_ref`.
- **Top-up packs:** add pack SKUs to a `tokenPacks` catalog (`{ id, tokens, priceEnv }`); the **checkout** route accepts a pack id and creates a one-time `payment` session (reuse `priceIdForPlan`-style env mapping + **Stripe Tax** for VAT); the **webhook** gains a branch: pack session → `grantTokens(purchased, expiresAt = now+12mo, ref = "stripe:"+event.id)`.
- **Kill-switch:** `AI_METERING_ENABLED` env (default off). Off ⇒ Phase-1 behaviour (log only). Lets Phase 2 ship dark and flip on after validation.
- **Config (`tiers.catalog.json`):** add `"aiTokens": <n>` per plan (allowance; draft = trial amount). Add a sibling `tokenPacks` list. **Numbers TODO — fill from Phase-1 COGS.**
- **Admin COGS page** `src/app/admin/cogs/` (gated by an `ADMIN_USER_IDS` allowlist checked server-side via `verifyAuth` + membership): service-role rollups over `ai_usage_log` — cost by day/feature/model, per-customer usage, **margin = token revenue − cost_usd**. Plus a **scheduled cost-spike alert** (a Cloud Run job or Supabase cron comparing today's COGS to a threshold → Resend email).

### UI (the four views + the dialog pie)
- **Balance readout:** next to `TierBadge.tsx` in the sidebar (reads a new `useTokenBalance()` hook → `token_balance` RPC / read-own `token_grants`).
- **AI-dialog pie:** in `AssistantDrawer.tsx` footer (it already shows `sessionCost`) — add a small **doughnut of allowance used/remaining** + a **"Top up"** button (it already has `onUpgrade`/`entitled`/`locked`). Mirror a compact balance line in `DescribeProjectDialog.tsx` (pre-submit "~N tokens") and `ExportDialog.tsx` (for pdf/pptx/guide).
- **Usage history:** a Settings tab or `/account/usage` listing `ai_usage_log` rows (read-own RLS): date · feature · in/out tokens · cost (or tokens billed). Paginated.
- **Top-up modal:** patterned on `UpgradeModal.tsx` — pack options → checkout. Opened from the balance readout and the `insufficient_tokens` state.
- **i18n:** new `tokens` group in `messages/{en,fr,it,uk}.json` (balance, remaining, lowBalance, topUp, usageHistory, insufficient, perCall estimate, byok…).

---

## 7. Edge cases — the required handling

| Concern | Handling |
|---|---|
| **Idempotent grants** | `token_grants.source_ref` unique; `grant_tokens` no-ops on a seen ref. Stripe events carry a stable `event.id`. |
| **Atomic deduction / no negative / multi-tab** | `consume_tokens` checks balance then `UPDATE … FOR UPDATE` row-locks per bucket in one transaction; insufficient ⇒ deduct nothing, return `-1`. DB atomicity covers concurrent tabs/replicas. |
| **No charge on failed/refused call** | Reserve-then-settle: engine error or `type:"refusal"` ⇒ `refund_tokens(full reserve)`. Log with `billed_tokens=0`. |
| **Variable cost** | Reserve `input_estimate + max_output_tokens`; settle to actual; refund the difference. Output is already server-capped (`max_output_tokens`), bounding the max reserve. |
| **Pre-flight estimate** | Estimate input tokens (tokenizer or ~chars/4 heuristic) + `max_output`; show "~N tokens" before submit and use it as the reserve. |
| **Low / empty balance UX** | Warn under a configurable threshold; at 0 the route returns `402` and the UI shows a **Top up** CTA (never a dead end). |
| **Anthropic prompt-cache tokens** | The wrapper captures `cache_creation`/`cache_read`; `pricing.py` prices them; `cost_usd` and `ai_usage_log` reflect them so COGS is accurate when caching is on. |
| **Price-table drift** | One source (`pricing.py`) + `PRICES_VERIFIED` date; unknown model ⇒ cost 0 **and a logged warning** (so a new model can't silently cost nothing). A test asserts every model used in code is priced. |
| **Expiry display** | Balance view shows allowance expiry (= window) and purchased expiry (12mo). A daily job (or lazy-at-read filter — the RPCs already exclude `expires_at<=now()`) writes `expiry` ledger rows for reporting. |
| **Admin COGS + spike alert** | Rollup page + scheduled threshold check → email. |
| **Privacy** | `ai_usage_log` stores **token counts + model only — never prompt/response text**. Add a line to the Privacy Policy; OpenAI/Anthropic already listed as sub-processors. |
| **VAT on packs** | Packs go through the same Stripe Checkout with **Stripe Tax** already wired — VAT handled, no new work. |
| **BYOK** | Encrypted-at-rest key; decrypt only server-side when forwarding; usage **logged (byok=true) but not deducted**; never returned to the browser or logged. |
| **Kill-switch** | `AI_METERING_ENABLED` gates all reserve/deduct; off = measure-only. |
| **Start measuring now** | Phase 1 ships before testers so real COGS accrues for pricing. |

---

## 8. Tests (Vitest, next to source)
- `core/ai` (engine, pytest): `pricing` returns rates for every in-use model incl. cache; `llm.complete` parses usage for **both** providers; cost math incl. cache.
- `src/lib/aiUsage.test.ts`: logs a row; fail-open on admin error.
- `src/lib/tokenWallet.test.ts` + DB: `consume_tokens` atomicity, insufficient = no-op, **order** (allowance before purchased, earliest expiry), refund path, `grant_tokens` idempotency on repeated `source_ref`, expiry excluded from balance.
- Route tests: metered route returns **402** when balance 0; **no deduction** on engine error/refusal; BYOK path skips deduction; export reads `X-AI-Usage`.
- `stripe-webhook/route.test.ts`: pack `checkout.session.completed` → `grant_tokens(purchased,12mo)`, idempotent on duplicate event.
- `supabase/migrations/rls-coverage.test.ts`: add the three new tables; assert read-own + service-role-write-only.

---

## 9. Rollout

**Phase 1 — Measure (the next days, no gating):**
engine `pricing.py` + `llm.py` wrapper; `usage` on all AI endpoints (+ `X-AI-Usage` on export); `ai_usage_log` migration; `logAiUsage` in every AI route; verify prices; SQL COGS rollups. Flip nothing for users. ➜ **real €/action accrues.**

**Phase 1.5 — Price (you, from data):** set `aiTokens` allowance per tier, pack sizes/prices, markup, low-balance threshold → into config.

**Phase 2 — Enforce (behind `AI_METERING_ENABLED`):** `token_grants`/`token_ledger`/`byok_keys` + RPCs; `tokenWallet.ts`; reserve/settle in routes; allowance grant on tier purchase; top-up packs (checkout + webhook); balance/pie/history/top-up UI; admin COGS + spike alert; BYOK; tests. Validate in staging, then flip the flag.

---

## 10. Open pricing inputs (fill after Phase 1)
`aiTokens` per tier (draft trial · plan · bankable · advisor monthly) · token→€ in packs (markup over measured COGS per 1k tokens) · pack sizes · low-balance warning threshold · BYOK eligibility (Advisor only vs opt-in for all).
