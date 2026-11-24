# AI Token Metering & Top-Up — Pro-Memoria (build spec)

**Status:** design, ready to build · **Author:** planning session, 2026-11-23
**Repos:** `startuplan-core` (engine, Python/FastAPI) · `StartUPlan_Web` (web, Next.js 16)
**Companion:** `tiers.catalog.json`, the Pricing Model artifact, `DEPLOY_STATE.md`.
**Rev 2 (2026-11-24):** Phase-2 wallet hardened after review — reservation model (refund to the *original* bucket so allowance can't leak into permanent tokens; atomic all-or-nothing reserve; crash-sweep of orphaned reservations), idempotent grants via the unique constraint, a per-feature reserve cap (the web can't estimate the engine's input), and **BYOK split out to its own Phase 3**. Phase 1 is unchanged.

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
| BYOK | **Yes — but a separate later milestone (Phase 3)**; the wallet ships without it. When added: Advisor/opt-in user key, usage logged (visibility) but **not deducted**. |

---

## 0b. Work by layer — the scheme (what gets built where)

```
   USER
    │  clicks "Describe project" / asks the Assistant / exports a PDF
    ▼
┌───────────────┐   call    ┌─────────────────────┐   measure   ┌──────────────────┐
│  FRONTEND     │──────────▶│  WEB ROUTES         │────────────▶│  ENGINE (Python) │
│  (React UI)   │           │  (Next.js /api/*)   │  usage ◀────│  reports tokens  │
│               │◀──────────│                     │             │  + our cost      │
│ balance • pie │  balance  │ log • reserve •     │             └──────────────────┘
│ history•topup │           │ settle • grant      │
└───────────────┘           └───────┬─────────────┘
                                     │ writes (service role only)
                      ┌──────────────┼───────────────┐
                      ▼                               ▼
             ┌─────────────────┐             ┌─────────────────┐
             │  SUPABASE (DB)  │             │  STRIPE         │
             │ usage log •     │             │ one-time token  │
             │ token buckets • │◀────webhook─│ pack purchase   │
             │ ledger • RPCs   │   grants    │ (+ VAT)         │
             └─────────────────┘             └─────────────────┘
```

| Layer | What gets added | **Plain words — what it actually does** | Phase |
|---|---|---|---|
| **Frontend** (web UI) | Balance readout by `TierBadge`; **allowance pie + "Top up"** in `AssistantDrawer`; pre-submit "~N tokens" in Describe/Export dialogs; **usage-history** view; **top-up modal**; `tokens` strings ×4 locales | What the user *sees*: how many tokens are left (a little pie on the AI box), their call history, and a button to buy more when low. | P2 |
| **Backend — Engine** (Python) | `pricing.py` (all model prices incl. cache); `llm.py` wrapper; every AI endpoint returns `usage` (export via a header) | Make the AI engine *report* how many tokens each call used and what it cost **us** — for both OpenAI and Anthropic. | P1 |
| **Backend — Web routes** (Next.js) | `aiUsage.ts` (log); `tokenWallet.ts`; reserve→settle in routes; webhook token-grant branch; checkout pack support; admin COGS page | The server *records* every call, *checks the balance before* spending, and hands out / charges tokens. Nothing happens in the browser. | P1 + P2 |
| **Supabase** (database) | `ai_usage_log` (P1); `token_grants` + `token_ledger` + `token_reservations` (P2; `byok_keys` → P3); RPCs grant/reserve/settle/refund/sweep/balance; RLS | Where the numbers *live*: a log of every call, each person's token buckets, an audit trail — with safe rules so only the server can change them. | P1 + P2 |
| **Stripe** | Token-pack products (one-time `payment`); webhook branch to credit tokens; Stripe Tax (VAT) | How people *pay* to top up — an ordinary one-time purchase, VAT handled automatically. | P2 |
| **Config / Ops** | `aiTokens` per tier + `tokenPacks` in the catalog; `AI_METERING_ENABLED` kill-switch; cost-spike email alert; price-verified date | The *dials you turn*: how many tokens each plan includes, pack prices, and an on/off switch for the whole thing. | P1 + P2 |

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
            │  tokenWallet.ts → reserve_tokens / settle_reservation / grant_tokens      │
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
  reason       text not null,                            -- 'grant'|'reserve'|'settle_refund'|'refund'|'expiry'
  grant_id     uuid references public.token_grants(id),
  source_ref   text,                                     -- links to usage_log.id or stripe event
  balance_after bigint,
  created_at   timestamptz not null default now()
);
create index token_ledger_user_idx on public.token_ledger (user_id, created_at);
alter table public.token_ledger enable row level security;
create policy "read own token ledger" on public.token_ledger for select using (auth.uid() = user_id);

-- Open reservations: holds the per-grant `draws` so settle/refund restore the ORIGINAL buckets, and a
-- sweep can reclaim a reservation orphaned by a crash between reserve and settle.
create table public.token_reservations (
  ref         text primary key,                 -- the route's idempotency ref (one per metered call)
  user_id     uuid not null references auth.users(id) on delete cascade,
  reserved    bigint not null,
  draws       jsonb not null,                    -- [{grant_id, amount}] — which buckets it drew from
  status      text not null default 'open' check (status in ('open','settled','refunded')),
  created_at  timestamptz not null default now(),
  settled_at  timestamptz
);
create index token_reservations_open_idx on public.token_reservations (created_at) where status = 'open';
alter table public.token_reservations enable row level security;  -- service-role only (no policy)
```
> Add `ai_usage_log`, `token_grants`, `token_ledger`, `token_reservations` to `rls-coverage.test.ts` `EXPECTED_TABLES`.
> `token_grants`/`token_ledger` are owner-scoped (policies above). `token_reservations` is server-only (no policy → service-role writes).

### BYOK key storage — Phase 3 (separate milestone, *not* in the Phase-2 wallet)
> Deferred: storing users' provider keys is its own custody liability (rotation, a decrypt path in the hot request, blast radius if the server key leaks). The wallet ships and works without it; add BYOK as its own milestone after Phase 2.
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
-- Idempotent grant. Relies on the UNIQUE index on source_ref (not a check-then-insert), so two
-- concurrent identical webhooks can't double-grant — the second hits the constraint and no-ops.
create or replace function public.grant_tokens(
  p_user uuid, p_amount bigint, p_kind text, p_expires_at timestamptz, p_source_ref text
) returns bigint language plpgsql security definer set search_path = public as $$
begin
  insert into token_grants(user_id,kind,total,remaining,expires_at,source_ref)
    values (p_user,p_kind,p_amount,p_amount,p_expires_at,p_source_ref);
  insert into token_ledger(user_id,delta,reason,source_ref) values (p_user,p_amount,'grant',p_source_ref);
  return public.token_balance(p_user);
exception when unique_violation then          -- same source_ref already granted → idempotent no-op
  return public.token_balance(p_user);
end; $$;

-- Live balance = sum of non-expired remaining.
create or replace function public.token_balance(p_user uuid)
returns bigint language sql security definer set search_path = public as $$
  select coalesce(sum(remaining),0) from token_grants
   where user_id = p_user and remaining > 0 and (expires_at is null or expires_at > now());
$$;

-- Reserve the pre-flight MAX up front, recording the per-grant draw in `draws` so a later settle/refund
-- restores the ORIGINAL buckets (allowance stays allowance, with its own expiry). ALL-OR-NOTHING: a
-- partial draw raises → rolls back every deduct → returns -1, so concurrent calls can't over/under-charge.
create or replace function public.reserve_tokens(p_user uuid, p_amount bigint, p_ref text)
returns bigint language plpgsql security definer set search_path = public as $$
declare r record; left bigint := p_amount; take bigint; draws jsonb := '[]'::jsonb;
begin
  if p_amount <= 0 then return public.token_balance(p_user); end if;
  if exists (select 1 from token_reservations where ref = p_ref) then           -- idempotent re-call
    return public.token_balance(p_user); end if;
  for r in select id, remaining from token_grants
            where user_id = p_user and remaining > 0 and (expires_at is null or expires_at > now())
            order by (kind not in ('allowance','trial')), expires_at nulls last  -- allowance/trial first, soonest expiry
            for update
  loop
    exit when left <= 0;
    take := least(left, r.remaining);
    update token_grants set remaining = remaining - take where id = r.id;
    draws := draws || jsonb_build_object('grant_id', r.id, 'amount', take);
    left := left - take;
  end loop;
  if left > 0 then raise exception 'insufficient'; end if;                       -- → caught below, rolls back
  insert into token_reservations(ref,user_id,reserved,draws) values (p_ref,p_user,p_amount,draws);
  insert into token_ledger(user_id,delta,reason,source_ref) values (p_user,-p_amount,'reserve',p_ref);
  return public.token_balance(p_user);
exception when others then
  return -1;                                                                     -- insufficient / any failure → nothing deducted (fail-closed)
end; $$;

-- Settle an open reservation to the ACTUAL usage: return (reserved - actual) to the SAME grants it was
-- drawn from (so allowance keeps its original expiry — this is the fix for the "refund leaks into
-- permanent tokens" bug). Idempotent: a no-op once settled. Expired grants are NOT resurrected.
create or replace function public.settle_reservation(p_ref text, p_actual bigint)
returns void language plpgsql security definer set search_path = public as $$
declare res record; d jsonb; back bigint; give bigint;
begin
  select * into res from token_reservations where ref = p_ref and status = 'open' for update;
  if not found then return; end if;                                             -- already settled/refunded
  back := greatest(res.reserved - greatest(p_actual,0), 0);                      -- unused reserve to return
  for d in select * from jsonb_array_elements(res.draws) loop                    -- restore across the drawn grants
    exit when back <= 0;
    give := least(back, (d->>'amount')::bigint);
    update token_grants set remaining = remaining + give
      where id = (d->>'grant_id')::uuid and (expires_at is null or expires_at > now());
    back := back - give;
  end loop;
  update token_reservations set status = 'settled', settled_at = now() where ref = p_ref;
  insert into token_ledger(user_id,delta,reason,source_ref)
    values (res.user_id, greatest(res.reserved - greatest(p_actual,0),0), 'settle_refund', p_ref);
end; $$;

-- Failed/refused call → refund the whole reservation (settle to 0 actual).
create or replace function public.refund_reservation(p_ref text)
returns void language sql security definer set search_path = public as $$
  select public.settle_reservation(p_ref, 0);
$$;

-- Crash safety: auto-refund reservations left 'open' past a TTL (web died between reserve and settle).
-- Run from a scheduled job (Cloud Run job / Supabase cron) every few minutes.
create or replace function public.sweep_stale_reservations(p_minutes int default 15)
returns int language plpgsql security definer set search_path = public as $$
declare n int := 0; res record;
begin
  for res in select ref from token_reservations
             where status = 'open' and created_at < now() - make_interval(mins => p_minutes) loop
    perform public.refund_reservation(res.ref); n := n + 1;
  end loop;
  return n;
end; $$;

revoke all on function public.grant_tokens(uuid,bigint,text,timestamptz,text) from public, anon, authenticated;
revoke all on function public.reserve_tokens(uuid,bigint,text)                from public, anon, authenticated;
revoke all on function public.settle_reservation(text,bigint)                from public, anon, authenticated;
revoke all on function public.refund_reservation(text)                       from public, anon, authenticated;
revoke all on function public.sweep_stale_reservations(int)                  from public, anon, authenticated;
-- token_balance may stay callable by the owner for the balance view, or be read via the service role.
```

**Reserve-then-settle** (the professional pattern, since output is capped):
1. **Reserve** before the call: `max = per-feature cap` (a conservative ceiling — see note) → `reserve_tokens(user, max, ref)`; `-1` → **402 insufficient** (nothing deducted).
2. **Call** the engine.
3. **Settle** after: `actual = usage.total_tokens` → `settle_reservation(ref, actual)` (returns the unused reserve to the original buckets). On engine **error/refusal**: `refund_reservation(ref)` — **no charge**.
4. **Crash safety:** a scheduled `sweep_stale_reservations()` auto-refunds any reservation left open past its TTL, so a web/engine crash between reserve and settle never costs the user.

> **Why a per-feature cap, not an input estimate:** the *engine* assembles the real prompt (system prompt + facts + editable catalog + conversation), which the web route never sees — so the web can't compute `input_tokens` accurately. Reserve a **conservative fixed ceiling per feature** (e.g. assistant = input-cap + `max_output`; extract = its own cap) and let `settle_reservation` refund down to the true `actual`. Alternatively, have the engine return a cheap pre-estimate; the cap is simpler and safe.

---

## 5. Engine changes (per file)

1. **`core/ai/pricing.py` (new, single source of truth).** Move + complete `_MODEL_PRICES`:
   both providers, input/output **and** cache rates (Anthropic cache-write ≈1.25× input, cache-read ≈0.1× input; OpenAI cached-input discount). Include the real models in use (`claude-haiku-4-5`, `gpt-4o-mini`, any Sonnet/Opus/4o used by the assistant tiers). Add a `PRICES_VERIFIED = "YYYY-MM-DD"` stamp and a helper `cost_usd(model, in, out, cache_read, cache_write)`. *(Numbers: verify against the Anthropic/OpenAI pricing pages at build time.)*
2. **`core/ai/llm.py` (new wrapper).** `complete(provider, model, messages, max_output_tokens, api_key, …) -> (text, Usage)` where `Usage = {provider, model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd}`. It owns the `OpenAI`/`Anthropic` client call and the provider-specific usage extraction (OpenAI `prompt_tokens/completion_tokens`; Anthropic `input_tokens/output_tokens` + `cache_creation_input_tokens/cache_read_input_tokens`). `cost_usd` from `pricing.py`.
3. **Route every call site through it:** `plan_extractor`, `plan_writer.polish_narrative`, `reviewer`, `guided_interpreter`, and refactor `assistant.py` to use it (dropping its private price table). Each returns `usage` alongside its result.
4. **Endpoints return `usage`:** add `usage` to the JSON of `/extract`, `/guided/build`, `/guided/next`. `/plan/refine` is no-LLM → unchanged. `/plan/assistant` already returns it. **`/plan/export`** body is the binary file → return usage in a **`X-AI-Usage` response header** (JSON) for `pdf/pptx/guide`; `xlsx` sets it to zero/omits it.
5. **BYOK (Phase 3, later):** the wrapper will accept an optional `byok_key` (web forwards it only for BYOK users) and mark `usage.byok=true`. **Not part of Phase 1 or the Phase-2 wallet.**

> The engine stays **stateless** about billing — it only *measures*. All persistence + deduction is the web's job (it holds the service-role key + the user identity). Keep it that way.

---

## 6. Web changes (per file)

### Phase 1 — observability (ships first, no gating)
- **`src/lib/aiUsage.ts` (new):** `logAiUsage(admin, { userId, feature, usage, projectId?, byok? })` → insert one `ai_usage_log` row via the service-role client. **Fail-open** (a logging error must never break the user's request).
- **In each AI route**, after a successful engine call, read `usage` (JSON body; for `export`, parse the `X-AI-Usage` header) and call `logAiUsage(auth.admin, { userId: auth.userId, feature, usage })`. Routes: `extract`, `assistant`, `guided`, `guided-next`, `export`. (`refine` = no LLM → skip.)
- **Migration** `..._ai_usage_log.sql` (DDL §3) + add to `rls-coverage.test.ts`.
- **A minimal cost view**: start with SQL rollups (run in the Supabase SQL editor, like the RLS audit) — cost/day, avg cost per feature, per model, per user. Promote to the admin page in Phase 2.

### Phase 2 — enforcement + top-up (behind a kill-switch)
- **`src/lib/tokenWallet.ts` (new):** `getBalance(admin,userId)`, `reserveTokens(admin,userId,max,ref)`, `settle(admin,userId,ref,actual)`, `refund(admin,userId,ref)`, `grantTokens(admin,userId,amount,kind,expiresAt,ref)` — thin wrappers over the RPCs. All service-role. A scheduled job calls `sweep_stale_reservations`.
- **Per metered route:** `const ref = crypto.randomUUID()`. If `AI_METERING_ENABLED`: `reserveTokens(per-feature cap, ref)` → `-1` ⇒ `402 {error:"insufficient_tokens", balance}` (nothing deducted). Call engine. `settle(ref, actual)` from the returned `usage.total_tokens`; on engine error/refusal `refund(ref)` (no charge). Then `logAiUsage(..., billed_tokens: actual)`. *(Phase 3: BYOK users skip reserve/settle and just `logAiUsage(byok:true)`.)*
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
| **Atomic deduction / no negative / multi-tab** | `reserve_tokens` draws under `FOR UPDATE` in one transaction and raises→rolls back if it can't fully cover (returns `-1`, deducts nothing); DB atomicity covers concurrent tabs/replicas. |
| **No charge on failed/refused call** | engine error or `type:"refusal"` ⇒ `refund_reservation(ref)` (restores the original buckets). Log with `billed_tokens=0`. |
| **Refund goes to the right bucket** | `settle_reservation` returns unused tokens to the **same grants** they were drawn from (via `draws`), so allowance keeps its original expiry and can't leak into never-expiring balance. |
| **Orphaned reservation (crash)** | A reservation left `open` past its TTL is auto-refunded by the scheduled **`sweep_stale_reservations()`** — a crash between reserve and settle never costs the user. |
| **Estimate / variable cost** | The web can't see the engine's assembled prompt, so reserve a **conservative per-feature cap** (not a web-side input estimate); `settle_reservation` refunds down to the true `actual`. Output is server-capped, bounding the cap. |
| **Partial-consume race** | `reserve_tokens` draws under `FOR UPDATE` and **raises→rolls back** if it can't fully cover, so concurrent calls are all-or-nothing (never a partial charge). |
| **Pre-flight estimate** | Estimate input tokens (tokenizer or ~chars/4 heuristic) + `max_output`; show "~N tokens" before submit and use it as the reserve. |
| **Low / empty balance UX** | Warn under a configurable threshold; at 0 the route returns `402` and the UI shows a **Top up** CTA (never a dead end). |
| **Anthropic prompt-cache tokens** | The wrapper captures `cache_creation`/`cache_read`; `pricing.py` prices them; `cost_usd` and `ai_usage_log` reflect them so COGS is accurate when caching is on. |
| **Price-table drift** | One source (`pricing.py`) + `PRICES_VERIFIED` date; unknown model ⇒ cost 0 **and a logged warning** (so a new model can't silently cost nothing). A test asserts every model used in code is priced. |
| **Expiry display** | Balance view shows allowance expiry (= window) and purchased expiry (12mo). A daily job (or lazy-at-read filter — the RPCs already exclude `expires_at<=now()`) writes `expiry` ledger rows for reporting. |
| **Admin COGS + spike alert** | Rollup page + scheduled threshold check → email. |
| **Privacy** | `ai_usage_log` stores **token counts + model only — never prompt/response text**. Add a line to the Privacy Policy; OpenAI/Anthropic already listed as sub-processors. |
| **VAT on packs** | Packs go through the same Stripe Checkout with **Stripe Tax** already wired — VAT handled, no new work. |
| **BYOK (Phase 3)** | Deferred to its own milestone. When built: encrypted-at-rest key, decrypt only server-side, usage **logged (byok=true) but not deducted**, never returned to the browser or logged. |
| **Kill-switch** | `AI_METERING_ENABLED` gates all reserve/deduct; off = measure-only. |
| **Start measuring now** | Phase 1 ships before testers so real COGS accrues for pricing. |

---

## 8. Tests (Vitest, next to source)
- `core/ai` (engine, pytest): `pricing` returns rates for every in-use model incl. cache; `llm.complete` parses usage for **both** providers; cost math incl. cache.
- `src/lib/aiUsage.test.ts`: logs a row; fail-open on admin error.
- `src/lib/tokenWallet.test.ts` + DB: `reserve_tokens` all-or-nothing (insufficient = no-op, `-1`), draw **order** (allowance/trial before purchased, earliest expiry), `settle_reservation` refunds to the **original** grants (expired allowance not resurrected), `refund_reservation` + `sweep_stale_reservations`, `grant_tokens` idempotency on repeated `source_ref`, expiry excluded from balance.
- Route tests: metered route returns **402** when balance 0; **no deduction** on engine error/refusal (reservation refunded); export reads `X-AI-Usage`.
- `stripe-webhook/route.test.ts`: pack `checkout.session.completed` → `grant_tokens(purchased,12mo)`, idempotent on duplicate event.
- `supabase/migrations/rls-coverage.test.ts`: add the three new tables; assert read-own + service-role-write-only.

---

## 9. Rollout

**Phase 1 — Measure (the next days, no gating):**
engine `pricing.py` + `llm.py` wrapper; `usage` on all AI endpoints (+ `X-AI-Usage` on export); `ai_usage_log` migration; `logAiUsage` in every AI route; verify prices; SQL COGS rollups. Flip nothing for users. ➜ **real €/action accrues.**

**Phase 1.5 — Price (you, from data):** set `aiTokens` allowance per tier, pack sizes/prices, markup, low-balance threshold → into config.

**Phase 2 — Enforce (behind `AI_METERING_ENABLED`):** `token_grants`/`token_ledger`/`token_reservations` + RPCs (grant/reserve/settle/refund/sweep); `tokenWallet.ts`; reserve→settle in routes; allowance grant on tier purchase; top-up packs (checkout + webhook); balance/pie/history/top-up UI; admin COGS + spike alert; the reservation **sweep job**; tests. Validate in staging, then flip the flag.

**Phase 3 — BYOK (separate, later):** `byok_keys` + app-side encryption; the engine accepts a forwarded key; BYOK users' usage is logged but not deducted. Its own milestone because key custody is a real liability (rotation, decrypt path, blast radius).

---

## 10. Open pricing inputs (fill after Phase 1)
`aiTokens` per tier (draft trial · plan · bankable · advisor monthly) · token→€ in packs (markup over measured COGS per 1k tokens) · pack sizes · low-balance warning threshold · BYOK eligibility (Advisor only vs opt-in for all).

---

## 11. Best task sequence (do them in this order)

### Phase 1 — Measure (ship first; no user-visible change)
1. **Engine · `pricing.py`** — one price table, all models in use, incl. Anthropic + cache rates. *Verify numbers against the provider pricing pages.*
2. **Engine · `llm.py` wrapper** — one function every AI call goes through; returns `(text, usage)` for both OpenAI and Anthropic.
3. **Engine · route all call sites** through the wrapper (`plan_extractor`, `assistant`, `plan_writer`, `reviewer`, `guided_interpreter`) and **return `usage`** on every AI endpoint (export via the `X-AI-Usage` header).
4. **Engine · tests** (pricing coverage, usage parsing for both providers).
5. **Supabase · `ai_usage_log`** migration + RLS (read-own, service-role write) + add to `rls-coverage.test.ts`.
6. **Web · `aiUsage.ts`** logger (fail-open).
7. **Web · call `logAiUsage`** in each AI route after a successful engine call.
8. **Web · route tests** (logs on success; fail-open; export reads the header).
9. **Measure** — COGS rollup SQL; run real calls; read actual €/action.
10. **⛔ STOP — review + set the pricing numbers** (allowances, pack sizes/prices, markup) into config.

### Phase 2 — Enforce + top-up (behind `AI_METERING_ENABLED`, default off)
11. **Supabase · wallet** — `token_grants` + `token_ledger` + `token_reservations` migrations; RPCs `grant_tokens` / `token_balance` / `reserve_tokens` / `settle_reservation` / `refund_reservation` / `sweep_stale_reservations` (atomic, idempotent); RLS + rls-coverage.
12. **Web · `tokenWallet.ts`** — `getBalance` / `reserveTokens` / `settle` / `refund` / `grantTokens`; schedule the `sweep_stale_reservations` job (every few min).
13. **Web · reserve→settle** in metered routes (402 on empty; refund on failure) — gated by the kill-switch.
14. **Web · allowance grant** on tier purchase (extend `writeGrant`).
15. **Stripe + Web · top-up packs** — one-time products; checkout accepts pack ids; **webhook** credits tokens (idempotent; Stripe Tax for VAT).
16. **Config · numbers** — `aiTokens` per tier + `tokenPacks` filled in.
17. **Frontend · views** — `useTokenBalance` hook; balance by `TierBadge`; **allowance pie + "Top up"** in `AssistantDrawer`; pre-submit estimate; **usage-history** view; **top-up modal**; `tokens` i18n ×4.
18. **Owner · admin COGS** page (allowlist-gated) + **cost-spike alert**.
19. *(moved to **Phase 3**)* — **BYOK** is its own later milestone (encrypted key storage; metering bypass; never expose the key), **not** part of this Phase 2.
20. **Tests → validate on staging → flip `AI_METERING_ENABLED` on.**

> **Golden rule:** steps **1–10 are safe to ship any time** (they only *measure*). Nothing touches a user's wallet until step 13, and even then only when the kill-switch is on. So you can deploy Phase 1 today, let real usage teach you the costs, and turn on billing when the numbers are right.
