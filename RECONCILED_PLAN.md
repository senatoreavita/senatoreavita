# Reconciled build plan — bankable plan × assistant × multilingual (pro-memoria)

**Status:** reconciliation (2026-11-25). Reconciles the **target** `bankable_business_plan_prompt.md`
(14-section bank/DFI standard) against the project specs (`BANKABLE_PLAN_SPEC.md`, `BUSINESS_PLAN_PDF.md`),
the **currently shipped** state, and the day's roadmap (consistency, assistant, multilingual).
Engine `startuplan-core@session_2026_11_25`; web `StartUPlan_Web@dashboard_2026_11_24`.

---

## 0. Summary

The bankable plan's **engine-driven core is built and now consistency-hardened**: sections 1, 8, 9,
10, 11 + annexes A–G, a verifier, scenarios/tornado/Monte-Carlo, and (today) one-resolver scenario
consistency + a named view contract so no value diverges across PDF / Excel / dashboard. Against the
full target prompt the remaining work is **founder intake** (unlocks 8 narrative sections), a handful
of **financial-depth/chart** items (mostly rendering of data the engine already computes), **Phase-3
cited research**, **multilingual**, and a **working project assistant**. Several target items are
**deferred by prior decision** (below) and are intentionally out of scope for the SME-lender product.

---

## 0a. Corrections (2026-11-25, re-verified against live code)

An earlier cut of this plan mis-stated two items; corrected here and below:

- **AI token billing was omitted entirely.** **Phase 1 (Measure) is DONE** — `pricing.py`
  (OpenAI + Anthropic + cache), the `llm.py` wrapper, all call sites routed, `ai_usage_log` +
  `ai_cogs_rollups` migrations, `aiUsage.ts` + `logAiUsage` in the AI routes, tests. **Phase 2
  (wallet/enforcement/top-up) is pending.** Added as **G10** below. (The assistant's cost chip
  is Phase-1 metering.)
- **Founder intake is not a flat gap.** The **engine scaffolding is DONE** (`core/report/founder.py`,
  `founder_sections.py`, FounderInputs + stub-aware sections + the 14-section layout); only the
  **web bankable-intake UI** is pending. G1 reworded accordingly.
- The assistant's "metering" = billing **Phase 1 (done)**; its **caps/enforcement = billing
  Phase 2 (pending)** — the *same* work as G10 P2.13, not a separate build.

## 1. Decisions already recorded (do not re-open)

- **Equity / Investor plan (plan Phase 2) — deferred by decision** (`BANKABLE_PLAN_SPEC §0b`).
- **Investor skin (Direction A) — reverted** (`1a1e1c4`); single **Lender** skin (Direction B) for now.
- **LLCR / PLCR — optional** (project-finance only; not SME term loans; stubbed `const(None)`).
- **CFADS-vs-debt-service chart — optional** for SME term loans.

These trim the ambitious target prompt to what StartUPlan ships for its SME-lender use case.

---

## 2. Status against the target prompt

| Prompt requirement | Status | Where |
|---|---|---|
| Per-section generation, grounded, metered, fail-closed | ✅ Done | `core/report/generate.py`, `sections.py` |
| FactsContract (numbers from the model, reconciled) | ✅ Done | `core/report/facts.py` (41 facts) |
| Quality gate as code (§10) | ✅ Done (subset) | `core/report/verify.py` |
| Engine sections 1, 8, 9, 10, 11 | ✅ Done | `core/exports/pdf/bankable.py` |
| §11 scenarios + tornado + Monte Carlo | ✅ Done (+ today: 10k MC, all-11 tornado) | `core/report/risk.py` |
| Annexes A–G (loan, revenue, costs, assets, TV, cap table, WC) | ✅ Done | `core/exports/pdf/annexes.py` |
| KPI consistency across surfaces | ✅ Hardened today | one resolver + view contract |
| Charts: DSCR-vs-covenant, Tornado, Rev/EBITDA, MC, cash line | ✅ Done | `core/exports/pdf/charts.py` |
| Founder sections 2, 3, 6, 7, 13, 14 | ◑ Engine scaffolded; omitted pending **web intake** | `founder.py`, `founder_sections.py` |
| AI token metering (per-call cost, logging) | ✅ Done (billing Phase 1) | `pricing.py`, `llm.py`, `aiUsage.ts`, `ai_usage_log` |
| AI token **wallet / enforcement / top-up** | ❌ Gap (billing Phase 2) | — |
| Market §4 / Competitive §5 | ❌ Gap | founder or Phase-3 research |
| §12 Risk register (table) | ◑ Partial (narrative draft only) | `_risks` draft |
| 4th scenario "Severe stress" | ❌ Gap (Base/Up/Down only) | `scenario_spec.py` |
| CFADS waterfall table (§5.2) | ❌ Gap (DSCR shown, not waterfall) | engine has CFADS |
| FCFF/FCFE + Project vs Equity IRR split | ◑ Partial (unlevered FCF + levered CF, unlabelled) | engine has series |
| Two-way DSCR matrix (price × volume) | ❌ Gap | — |
| Break-even sentences per driver vs covenant | ◑ Partial (one sentence) | — |
| KPIs: Equity IRR, LTV, DSRA (LLCR/PLCR optional) | ◑ Not surfaced | `ratios.py` |
| Assumptions Book (value·unit·source·date) / Glossary | ◑ Partial | — |
| Multilingual ({{LANGUAGE}}) | ❌ Gap (English prose) | diagnosed 2026-11-25 |
| Charts: CFADS-vs-debt, EBITDA bridge, spider, debt profile, 2-way heatmap | ❌ Gap | `charts.py` |
| Inline "in plain words" callouts / explainer PDF | ◑ Guide PDF exists; callouts pending | `guide.py` |

---

## 3. Reconciled gap list (grouped)

- **G1 — Founder intake WEB UI (keystone).** Engine side **DONE** (FounderInputs + stub-aware
  sections + 14-section layout); the **web collection UI** is what remains — collect §2/3/6/7/13/14
  inputs with *value·unit·source·date*, absent → stub + Open Item. Largest remaining user-facing
  surface; gates how "complete" a plan can be. **[M–L]** (was [L]; engine half already built)
- **G2 — §12 Risk register** (table grounded on engine sensitivities; narrative draft exists). **[M]**
- **G3 — §9/§11 financial depth:** 4th "Severe stress" scenario · CFADS waterfall table · FCFF/FCFE
  labelling + Project-vs-Equity IRR · per-driver break-even sentences vs covenant · two-way DSCR
  matrix · Assumptions Book + Glossary · surface Equity IRR/LTV/DSRA (+ thresholds). **[M–L]**
- **G4 — Remaining charts:** EBITDA bridge · spider/break-even · cumulative-cash trough · debt
  profile · two-way heatmap (CFADS-vs-debt optional). **[M]**
- **G5 — Phase-3 cited market research** (§4/§5): opt-in, grounded web search, every source verified,
  metered, fail-open to stub. **[L]**
- **G6 — Multilingual:** shared locale layer → chrome translation (titles + labels, incl. IT) → AI
  prose polish (enable the existing `polish_narrative(language=…)`) → locale number/date formatting.
  **[M–L]**
- **G7 — Project assistant** (Q&A + edits, any language, metered):
  - **C1** enrich `build_facts` with per-year series (cash flow, cumulative CF, revenue, net income,
    DSCR, calendar years) + formatted figures + bounded payload. *(started — see §5)*
  - **C2** enable edit proposals (scaffolded: `plan_catalog` + `validate_patch` + drawer apply).
  - **C3** multilingual answers (already plumbed; verify).
  - **C4** caps / entitlement / audit. **[M]**
- **G8 — Inline "in plain words" callouts** beside charts (explainer guide PDF already ships). **[S–M]**
- **G9 — Deploy-safety guards** (SHA stamp + cloudbuild `tag==HEAD` assert) + payback wording.
  *(started — see §5)* **[S]**
- **G10 — AI token billing.** **Phase 1 (Measure) DONE** (pricing/wrapper/logging/`ai_usage_log`).
  **Phase 2 (Enforce) pending:** wallet tables + RPCs (`token_grants`/`token_ledger`/`token_reservations`,
  grant/balance/reserve/settle/refund/sweep) · `tokenWallet.ts` + sweep job · reserve→settle in metered
  routes behind `AI_METERING_ENABLED` (= the assistant's caps) · allowance-grant on purchase · Stripe
  top-up packs · config numbers · balance/pie/history/top-up UI + `tokens` i18n ×4 · admin COGS + spike
  alert · staging → flip the kill-switch. Two Phase-1 decision steps remain: **measure real COGS** and
  **set the pricing numbers** (allowance/packs/markup). **BYOK = Phase 3, deferred.** **[L]**

**Engine-readiness note:** the engine already computes almost everything the prompt's KPI/chart
sections need (CFADS, DSCR series, ICR, leverage, liquidity, cap table — `BANKABLE_PLAN_SPEC §3`),
so **G3/G4 are mostly rendering**, not new modelling — lower risk than they look, and runnable in
parallel with the intake work.

---

## 4. Reconciled sequence

| # | Work | Why here | Effort |
|---|---|---|---|
| 0 | **G9** deploy guards + payback wording | tiny; stops repeats of the stale-bundle hour | S |
| 1 | **G7-C1** assistant per-year facts | high value, independent, already diagnosed | S–M |
| 2 | **G1** founder intake | keystone — unlocks 8 sections | L |
| 3 | **G2 + G3** risk register + financial depth | engine data ready; makes it bank-grade | M–L |
| 4 | **G4** remaining charts | pairs with G3 | M |
| 5 | **G7-C2/C3** assistant edits + multilingual answers | builds on C1 | M |
| 6 | **G6** multilingual plan (shared locale layer) | shares infra with G7-C3 | M–L |
| 7 | **G10** billing Phase 2 (wallet/enforce/top-up) — incl. the assistant's caps (P2.13) | monetisation; kill-switched; do after core features | L |
| 8 | **G8** inline callouts | polish once content settles | S–M |
| 9 | **G5** Phase-3 market research | opt-in upper tier; last | L |

*Near-term decision (not a build): **set the billing pricing numbers** (allowance/packs/markup)
from the Phase-1 COGS data — do this once real usage has accrued, before turning Phase 2 on.*

**Dependencies:** G1 gates sections 2–7/13/14 and Phase-3 (G5). G6 and G7-C3 share one locale layer
— build once. G3/G4 are engine-data-ready now (no intake needed) → parallelisable with G1.

---

## 5. Shipped this session

- **Item 1 (G7-C1) ✅** `build_facts()` enriched with per-year series (cash flow, cumulative,
  revenue, EBITDA, net income, DSCR) + money-formatting instruction + test. `startuplan-core@d171f59`.
- **Item 0 (G9) ✅ (partial)** `NEXT_PUBLIC_BUILD_SHA` stamp → shown in Settings; cloudbuild requires
  `_GIT_SHA` (no build without provenance). `StartUPlan_Web@0dc928f` + deploy doc. **Remaining:**
  payback "Year 8 vs 7" is an **Excel-formula** off-by-one (engine/dashboard/PDF agree on 8), folded
  into the G3 financial-depth/parity pass.
- Both need a redeploy to go live (engine for the assistant; web rebuild — now with `_GIT_SHA` — for
  the Settings stamp).
