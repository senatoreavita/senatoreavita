# Build prompt — AI Token Metering (Phase 1) + Wallet/Top-Up (Phase 2)

> Paste this into a fresh build session that has **both** repos checked out:
> `startuplan-core` (engine) and `StartUPlan_Web` (web). Develop on the current
> dashboard/dev branches (engine: its working branch; web: `dashboard_2026_11_23`).
> The full design is in **`AI_TOKEN_BILLING.md`** (planning repo `senatoreavita`,
> root) — read it first; this prompt is the execution brief, that doc is the source of truth.

## Goal
Add **AI token metering + a token wallet with top-ups** to StartUPlan. Users see a **token
balance** (unit = tokens), a **remaining-allowance pie on the AI dialog**, and a **usage
history**; they **top up** by buying tokens (one-time Stripe `payment`). AI features gate on
balance; deterministic compute + the **Excel workbook stay free**. Owner gets a **COGS
dashboard** + cost-spike alert. (**BYOK** — bring-your-own-key — is a later **Phase 3**, *not* in this build.) Ship **Phase 1 first and STOP
for review** before Phase 2.

## Hard rules (do not violate)
1. **Naming:** call it **tokens / token wallet / `token_grants` / `token_ledger` / `ai_usage_log`**. Do **NOT** use "credit" — that name is already the Stripe upgrade-proration feature (`tiers.ts` `UpgradeOffer.mode:"credit"`, `creditWindowDays`, `tiers.price.credit`). Colliding there is a bug.
2. **Security:** every write is **server-side via the service-role client** (`getSupabaseAdmin()`). New user tables are **read-own RLS, no write policy**; all mutations go through **SECURITY DEFINER** RPCs. Mirror `tier_grants` + `api_daily_usage`/`increment_api_usage`. Add every new table to `supabase/migrations/rls-coverage.test.ts` `EXPECTED_TABLES`.
3. **Privacy:** log **token counts + model only — NEVER prompt/response content.**
4. **The engine stays billing-stateless** — it only *measures* (returns `usage`). All persistence + deduction lives in the web (it holds the service-role key + the user id). Keep user identity/PII out of engine calls (unchanged).
5. **Idempotent** on Stripe `event.id`; **atomic** deduction (no negative balance, multi-tab safe); **no charge** on a failed/refused LLM call.
6. **Do not invent pricing numbers.** Allowances, pack sizes/prices, markup live in **config** (`tiers.catalog.json` `aiTokens` + a `tokenPacks` list) as explicit `TODO`s for the owner to fill from Phase-1 data. Do not hard-code them.
7. **Phase 1 must not gate or block any user** — it only logs. Enforcement is Phase 2, behind an `AI_METERING_ENABLED` kill-switch (default off).

## PHASE 1 — Measurement (do this now, then stop for review)

### Engine (`startuplan-core`)
1. `core/ai/pricing.py` (new): single source of truth for model prices — **both** providers, input/output **and** cache rates, covering every model actually used (`claude-haiku-4-5`, `gpt-4o-mini`, plus any assistant-tier models). `cost_usd(model, in, out, cache_read=0, cache_write=0)`. Add `PRICES_VERIFIED="YYYY-MM-DD"`. Unknown model ⇒ cost 0 **+ a logged warning**. (Verify the rates against the Anthropic/OpenAI pricing pages.)
2. `core/ai/llm.py` (new): `complete(provider, model, messages, max_output_tokens, api_key, …) -> (text, Usage)`. `Usage = {provider, model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd}`. Owns the OpenAI/Anthropic call + provider-specific usage extraction (OpenAI `prompt/completion_tokens`; Anthropic `input/output_tokens` + `cache_creation_input_tokens`/`cache_read_input_tokens`).
3. Route **every** `core/ai/*` LLM call through `complete()` and return `usage`: `plan_extractor`, `assistant` (refactor to drop its private `_MODEL_PRICES`), `plan_writer.polish_narrative`, `reviewer`, `guided_interpreter`.
4. Endpoints return `usage`: add to JSON of `/extract`, `/guided/build`, `/guided/next`. `/plan/export` returns it in an **`X-AI-Usage`** response header (JSON) for `pdf/pptx/guide` (`xlsx`=none). `/plan/refine` is no-LLM — unchanged.
5. Tests (pytest): pricing covers every in-use model incl. cache; `complete` parses usage for both providers; cost math.

### Web (`StartUPlan_Web`)
6. Migration `..._ai_usage_log.sql` — table + indexes + RLS (read-own, service-role-write) exactly as in the spec §3. Add `ai_usage_log` to `rls-coverage.test.ts`.
7. `src/lib/aiUsage.ts` (new): `logAiUsage(admin, { userId, feature, usage, projectId?, byok? })` → one `ai_usage_log` insert via the service-role client. **Fail-open** (never break the user request on a log error).
8. In each AI route (`extract`, `assistant`, `guided`, `guided-next`, `export`), after a successful engine call, read `usage` (JSON body; for `export` parse the `X-AI-Usage` header) and call `logAiUsage(auth.admin, { userId: auth.userId, feature, usage })`. Skip `refine`.
9. Tests: a route logs usage on success; fail-open on admin error; export reads the header.
10. Provide a short `docs/` SQL snippet of COGS rollups (cost/day, per feature, per model, per user) to run in the Supabase SQL editor.

**Then STOP.** Report: files changed, both suites green (engine pytest + web `vitest run`), and the COGS rollup SQL. Do **not** start Phase 2 — the owner prices from Phase-1 data first.

## PHASE 2 — Wallet + enforcement + top-up (only after review + pricing)
Behind `AI_METERING_ENABLED` (default off). Implement per spec §3–§6:
- Migrations: `token_grants`, `token_ledger`, `token_reservations` (+ RLS + rls-coverage). *(BYOK's `byok_keys` is Phase 3, not here.)*
- RPCs (all SECURITY DEFINER, revoked from public/anon/authenticated): `grant_tokens` (idempotent via the unique `source_ref` constraint — rely on the constraint + `exception when unique_violation`, not a check-then-insert), `token_balance`, `reserve_tokens` (atomic **all-or-nothing**; draws allowance/trial first then earliest expiry; records per-grant `draws`; raises→rolls back if it can't fully cover), `settle_reservation` (refunds the unused reserve to the **original** grants so allowance can't leak into permanent tokens), `refund_reservation`, `sweep_stale_reservations`.
- `src/lib/tokenWallet.ts`: `getBalance / reserveTokens / settle / refund / grantTokens`; schedule the `sweep_stale_reservations` job (every few min — crash safety).
- Metered routes: `reserveTokens(per-feature cap, ref)` — **the web can't estimate the engine's input (the engine builds the prompt), so reserve a conservative per-feature cap**, not an input estimate → `402 insufficient_tokens` if `-1`; `settle(ref, actual)` from `usage.total_tokens`; `refund(ref)` on engine error/refusal; `logAiUsage(billed_tokens=actual)`.
- **Phase 3 (separate, later): BYOK** — `byok_keys` + app-side encryption; engine accepts a forwarded key; BYOK usage logged but not deducted. Do **not** build it into Phase 2.
- Grants: `writeGrant` also `grantTokens(allowance = plan.aiTokens, expiresAt = tier window, ref="tier:"+sku)`; top-up pack `checkout.session.completed` ⇒ `grantTokens(purchased, now+12mo, ref="stripe:"+event.id)`.
- Config: `aiTokens` per plan + `tokenPacks` (TODO numbers). Checkout accepts pack ids (one-time `payment`, Stripe Tax for VAT).
- UI: `useTokenBalance()` hook; balance by `TierBadge`; **allowance pie + "Top up"** in `AssistantDrawer` footer (it already shows `sessionCost`); pre-submit "~N tokens" in `DescribeProjectDialog`/`ExportDialog`; usage-history view (read-own `ai_usage_log`); top-up modal (pattern `UpgradeModal`); `tokens` i18n group in all four `messages/*.json`.
- Admin: `src/app/admin/cogs/` gated by an `ADMIN_USER_IDS` allowlist — COGS by day/feature/model, per-customer, margin; scheduled cost-spike email alert.
- Tests per spec §8.

## Definition of done (Phase 1)
Engine + web changes above, **both test suites green**, no behaviour change for users (logging only), the COGS rollup SQL delivered, and a short written summary of what each AI action currently costs once a few real calls have been logged.
