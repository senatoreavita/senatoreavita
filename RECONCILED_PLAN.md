# Reconciled build plan — bankable plan × assistant × multilingual (pro-memoria)

**Status:** reconciliation (2026-11-25) **+ code-audit verification (2026-11-26).**
Reconciles the **target** `bankable_business_plan_prompt.md` (14-section bank/DFI standard)
against the project specs (`BANKABLE_PLAN_SPEC.md`, `BUSINESS_PLAN_PDF.md`), the **currently
shipped** state, and the day's roadmap (consistency, assistant, multilingual). On 2026-11-26
every "pending" item below was **verified against the live code** (four parallel audits of both
repos); the results are in §0b and folded through §2–§4. Engine `startuplan-core@main`
(`d171f59`, deployed); web `StartUPlan_Web@main` (`0dc928f`, deployed).

---

## 0. Summary

The bankable plan's **engine-driven core is built and consistency-hardened**: sections 1, 8, 9,
10, 11 + annexes A–G, a verifier, scenarios/tornado/Monte-Carlo, one-resolver scenario
consistency + a named view contract so no value diverges across PDF / Excel / dashboard. The
code audit (2026-11-26) shows the remaining work is **smaller than earlier cuts of this plan
claimed**: the **Project Assistant is fully built** (not pending), **FCFF/FCFE + Equity IRR are
already done in Excel** (only the PDF lags), and **multilingual is partly wired** (needs turning
on, not building from scratch). The genuine remaining work is **founder intake (web UI)**, a set
of **bankable financial-depth/chart** items, **billing Phase 2**, **Phase-3 cited research**, and
the **schema-migration path**. Several target items are **deferred by prior decision** (§1).

---

## 0a. Corrections (2026-11-25, re-verified against live code)

An earlier cut of this plan mis-stated two items; corrected here and below:

- **AI token billing was omitted entirely.** **Phase 1 (Measure) is DONE** — `pricing.py`
  (OpenAI + Anthropic + cache), the `llm.py` wrapper, call sites routed, `ai_usage_log` +
  `ai_cogs_rollups` migrations, `aiUsage.ts` + `logAiUsage` in the AI routes, tests. **Phase 2
  (wallet/enforcement/top-up) is pending.** Added as **G10** below.
- **Founder intake is not a flat gap.** The **engine scaffolding is DONE** (`core/report/founder.py`,
  `founder_sections.py`, FounderInputs + stub-aware sections + the section layout); only the
  **web bankable-intake UI** is pending. G1 reworded accordingly.
- The assistant's "metering" = billing **Phase 1 (done)**; its **caps/enforcement = billing
  Phase 2 (pending)** — the *same* work as G10 P2.13, not a separate build.

## 0b. Code-audit corrections (2026-11-26, four parallel audits of both repos)

Four read-only audits verified every "pending" claim against the live code. Four findings
**change the remaining-work picture** and are folded through §2–§4:

1. **G7 — the Project Assistant is DONE, not pending.** Earlier cuts list edit-proposals as
   "scaffolded", multilingual as "verify", caps as to-do. All four sub-features are **wired
   end-to-end**: whitelist-validated edit proposals (by field *name*) → **Apply** → recompute
   (`plan_catalog.py` → `assistant.py` → `AssistantDrawer.tsx` → `applyAssistantPatch.ts`);
   answers in the user's language; per-user cost log + 20/min + 100/day caps (durable in
   Supabase) + fail-closed auth/tier gates. **Removed from the pending list.** Cleanups only:
   a stale `/plan/assistant` docstring that still says "Phase 1 read-only / no edits" while the
   code returns edit proposals; language passed as an ISO code (`"it"`) not an endonym; the
   assistant reuses the `export` entitlement rather than a dedicated one.
2. **Founder sections are currently DROPPED from the exported PDF.** The engine scaffolding is
   complete, but the export path calls `build_bankable_pdf(founder=None → empty,
   omit_empty_founder=True)` (`core/services/export_service.py`), so **today's bankable PDF ships
   with none of the 8 narrative sections**. G1 (the web intake) is therefore the gate on the PDF
   being a real lender document, not just a nicety.
3. **FCFF/FCFE + Equity IRR are already done in Excel** — only the **PDF** lags. The engine
   computes `fcff`/`fcfe`/`equity_irr` and the Excel KPI sheet labels FCFF/FCFE and shows Project
   + Equity IRR side by side; the **PDF** still prints plain "Free cash flow" and omits equity
   IRR. This is a PDF-labelling task, not modelling.
4. **Multilingual: changing the language does NOT translate the plan body.** Section titles
   translate for FR/UK only; the sentence body is always English because the AI polish
   (`polish_narrative`, which *exists*) is **never switched on** by the export endpoint
   (`use_ai=False`), and an **Italian user gets an entirely English document** (`it → lng0 =
   English` mapping bug). So G6 is mostly *wire-on*, not build-from-scratch.

Two smaller audit findings: billing Phase 1 has **one unmetered AI call** (`core/ai/reviewer.py`
builds its own OpenAI client, bypassing `llm.py`) — fold into Phase-1 cleanup; and **LTV / DSRA
are not computed at all** (worse than "not surfaced").

---

## 1. Decisions already recorded (do not re-open)

- **Equity / Investor plan (plan Phase 2) — deferred by decision** (`BANKABLE_PLAN_SPEC §0b`).
- **Investor skin (Direction A) — reverted** (`1a1e1c4`); single **Lender** skin (Direction B) for now.
- **LLCR / PLCR — optional** (project-finance only; not SME term loans; stubbed `const(None)`).
- **CFADS-vs-debt-service chart — optional** for SME term loans.

These trim the ambitious target prompt to what StartUPlan ships for its SME-lender use case.

---

## 2. Status against the target prompt (verified 2026-11-26)

Legend: ✅ done · ◑ partial · ❌ gap. "Verified" = the 2026-11-26 code audit; "Plain language"
is the non-engineer explanation.

| Requirement | Plan status | Verified (code audit) | Plain language |
|---|---|---|---|
| Per-section generation, grounded, metered, fail-closed | ✅ | ✅ `report/generate.py`, `sections.py` | Each section is written from the model's own numbers and refuses rather than invent. |
| FactsContract (numbers reconciled) | ✅ | ✅ `report/facts.py` | One vetted set of figures feeds every section. |
| Quality gate as code (§10) | ✅ | ✅ `report/verify.py` | An automated check flags gaps before the file prints. |
| Engine sections 1, 8, 9, 10, 11 | ✅ | ✅ `exports/pdf/bankable.py` | The financial sections are built. |
| §11 scenarios + tornado + Monte Carlo | ✅ | ✅ (10k MC, all-lever tornado) `report/risk.py` | Up/down cases, driver ranking and a 10,000-run simulation all render. |
| Annexes A–G | ✅ | ✅ `exports/pdf/annexes.py` | The back-of-report detail tables are built. |
| KPI consistency across surfaces | ✅ | ✅ one resolver + view contract | Dashboard, Excel and PDF now show identical numbers. |
| Charts: DSCR-vs-covenant, tornado, Rev/EBITDA, MC, cash line | ✅ | ✅ 6 charts in `exports/pdf/charts.py` | The core lender charts are built. |
| Founder sections 2, 3, 6, 7, 13, 14 | ◑ engine scaffolded | ◑ **engine done but DROPPED from export** (`export_service.py` passes `founder=None`) | The engine can render these, but the PDF currently omits them because nothing fills them in. |
| AI token metering (per-call cost, logging) | ✅ (Phase 1) | ◑ done **except one unmetered call** in `reviewer.py` | Almost every AI call's cost is logged; one path isn't. |
| AI token **wallet / enforcement / top-up** | ❌ (Phase 2) | ❌ entirely absent (no wallet/reserve/top-up/UI/admin) | No token balance, no spending limit, no way to buy more. |
| Market §4 / Competitive §5 | ❌ | ❌ (needs founder or Phase-3 research) | No market/competitor section yet. |
| §12 Risk register (table) | ◑ narrative only | ❌ **no table** — only a prose paragraph | No proper "risk → likelihood → impact → mitigation" table. |
| 4th scenario "Severe stress" | ❌ | ❌ only base/upside/downside | The harsher stress case isn't built. |
| CFADS waterfall table (§5.2) | ❌ (CFADS computed) | ◑ CFADS computed; **no waterfall table in PDF** | Cash-to-lenders is calculated but not shown as a step-down table. |
| FCFF/FCFE + Project vs Equity IRR | ◑ unlabelled | ✅ **in Excel**; ❌ in PDF | The spreadsheet already labels/splits these; the PDF doesn't. |
| Two-way DSCR matrix (price × volume) | ❌ | ❌ absent | No grid of debt coverage across price and volume. |
| Break-even sentences per driver vs covenant | ◑ one sentence | ◑ one sentence | Only a single break-even line, not one per driver. |
| KPIs: Equity IRR, LTV, DSRA | ◑ not surfaced | ❌ **LTV/DSRA not computed at all**; equity IRR Excel-only | Two lender metrics don't exist yet; shareholder return reaches only Excel. |
| Assumptions Book (value·unit·source·date) / Glossary | ◑ partial | ❌ no assumptions book, no glossary | No single table of every assumption, and no glossary. |
| Multilingual ({{LANGUAGE}}) | ❌ English prose | ◑ **titles FR/UK only; body always English; polish exists but off; `it→English` bug** | Switching language changes some headings, never the sentences; Italian gets all-English. |
| Charts: EBITDA bridge, spider, debt profile, 2-way heatmap, cash-trough | ❌ | ❌ none of the 5 built (6 others exist) | The five fancier charts aren't built. |
| Inline "in plain words" callouts / explainer PDF | ◑ guide exists | ◑ guide PDF exists; callouts pending | The how-to-read guide exists; inline boxes beside charts don't. |
| **Project Assistant (Q&A + edits, any language, metered)** | ◑ "scaffolded / verify" | ✅ **DONE, wired end-to-end** | Ask questions, propose + apply edits, in any language, with cost caps — all working. |
| Deploy-safety guards (SHA stamp + cloudbuild assert) | ◑ started | ✅ **done + deployed** (build `0dc928f` live) | You can see which build is live; no image ships without that stamp. |

---

## 3. Reconciled gap list (grouped, verified)

- **G1 — Founder intake WEB UI (keystone).** Engine **DONE**; the **web collection UI** remains —
  collect §2/3/6/7/13/14 inputs with *value·unit·source·date*, absent → stub + Open Item. **Also
  flip the export** to pass the populated `FounderInputs` (today it passes `None`, so the sections
  are dropped). Largest remaining user-facing surface; gates how "complete" the PDF is. **[M–L]**
- **G2 — §12 Risk register** (table grounded on engine sensitivities; only a narrative paragraph
  exists today — **no table**). **[M]**
- **G3 — §9/§11 financial depth:** 4th "Severe stress" scenario · CFADS waterfall table ·
  **surface FCFF/FCFE + equity IRR in the PDF** (already in Excel — *small*) · per-driver
  break-even sentences · two-way DSCR matrix · Assumptions Book + Glossary · **compute + surface
  LTV / DSRA** (don't exist yet) · Excel payback off-by-one. **[M–L]** *(engine already computes
  CFADS/DSCR/ICR/leverage/liquidity — much of this is rendering.)*
- **G4 — Remaining charts:** EBITDA bridge · spider/break-even · cumulative-cash trough · debt
  profile · two-way heatmap. **[M]**
- **G5 — Phase-3 cited market research** (§4/§5): opt-in, grounded web search, sources verified,
  metered, fail-open to stub. **[L]**
- **G6 — Multilingual: mostly WIRE-ON, not build.** The AI polish (`polish_narrative`) and FR/UK
  chrome translation already exist. Turn on `use_ai` on the export path · fix the locale→language
  mapping (incl. the `it → English` bug) · translate the few hardcoded labels (e.g. "Annexes") ·
  locale number/date formatting. **[M]** *(down from [M–L])*
- **G7 — Project assistant — ✅ DONE (removed from pending).** C1 facts, C2 edit proposals, C3
  multilingual answers, C4 caps/entitlement/audit all wired end-to-end. Cleanups only: stale
  `/plan/assistant` docstring · ISO-code vs endonym language · dedicated assistant entitlement.
- **G8 — Inline "in plain words" callouts** beside charts (explainer guide PDF already ships). **[S–M]**
- **G9 — Deploy-safety guards — ✅ DONE + deployed** (SHA stamp live in Settings; cloudbuild
  requires `_GIT_SHA`). *(removed from pending.)*
- **G10 — AI token billing.** **Phase 1 (Measure) DONE** — plus **fix the one unmetered call**
  (`reviewer.py` bypasses `llm.py`). **Phase 2 (Enforce) pending:** wallet tables + RPCs
  (`token_grants`/`token_ledger`/`token_reservations`, grant/balance/reserve/settle/refund/sweep)
  · `tokenWallet.ts` + sweep job · reserve→settle in metered routes behind `AI_METERING_ENABLED`
  (= the assistant's caps) · allowance-grant on purchase · Stripe top-up packs · config numbers ·
  balance/pie/history/top-up UI + `tokens` i18n ×4 · admin COGS + spike alert · staging → flip
  the kill-switch. Two Phase-1 decision steps remain: **measure real COGS** and **set the pricing
  numbers**. **BYOK = Phase 3, deferred.** **[L]**
- **G11 — Plan schema-version migration path** (pre-public). `project_inputs.schema_version` is
  stamped `=1` but **never read back** — no `CURRENT_SCHEMA_VERSION`, no migrator registry.
  Build: a version read on load → run `v(n→n+1)` migrators → deserialize. **Required before real
  users store plans.** **[S–M]** *(was internal task #11.)*

**Engine-readiness note:** the engine already computes almost everything the prompt's KPI/chart
sections need (CFADS, DSCR series, ICR, leverage, liquidity, cap table), so **G3/G4 are mostly
rendering**, not new modelling — runnable in parallel with the intake work.

---

## 4. Reconciled sequence (verified)

| # | Work | Why here | Effort |
|---|---|---|---|
| — | **G7 assistant** | ✅ already done — not scheduled | — |
| — | **G9 deploy guards** | ✅ already done + deployed — not scheduled | — |
| 1 | **G1** founder intake web UI (+ flip export to include founder) | keystone — unlocks + un-drops 8 sections | L |
| 2 | **G2 + G3** risk register + financial depth (incl. PDF FCFF/FCFE/equity-IRR labelling — *small*; LTV/DSRA compute; Excel payback) | engine data ready; makes it bank-grade | M–L |
| 3 | **G4** remaining charts | pairs with G3 | M |
| 4 | **G6** multilingual — *turn on* AI polish + fix locale mapping (`it→English`) + labels | infra already exists | M |
| 5 | **G11** schema-version migration path | before real users store plans | S–M |
| 6 | **G10** billing Phase 2 (wallet/enforce/top-up) + fix the unmetered call | monetisation; kill-switched; after core features + real COGS | L |
| 7 | **G8** inline callouts | polish once content settles | S–M |
| 8 | **G5** Phase-3 market research | opt-in upper tier; last | L |

*Near-term decision (not a build): **set the billing pricing numbers** (allowance/packs/markup)
from the Phase-1 COGS data — once real usage has accrued, before turning Phase 2 on.*

**Dependencies:** G1 gates sections 2–7/13/14 and Phase-3 (G5). G3/G4 are engine-data-ready now
(no intake needed) → parallelisable with G1. G6 is now independent (its infra exists).

---

## 5. Shipped this session

- **G7-C1 ✅** `build_facts()` enriched with per-year series (cash flow, cumulative, revenue,
  EBITDA, net income, DSCR) + money-formatting instruction + test. `startuplan-core@d171f59`.
- **G9 ✅** `NEXT_PUBLIC_BUILD_SHA` stamp → shown in Settings; cloudbuild requires `_GIT_SHA`.
  `StartUPlan_Web@0dc928f` + deploy doc.
- **Redeploy ✅ (2026-11-26)** engine (`d171f59`) + web (`0dc928f`) deployed to Cloud Run from
  `main` — the assistant facts enrichment and the build stamp are live.
- **Code-audit verification ✅ (2026-11-26)** four parallel audits of both repos re-checked every
  pending claim; results in §0b and folded through §2–§4 (headline: G7 and G9 done; FCFF/FCFE +
  equity IRR Excel-done; multilingual wire-on; founder sections dropped from export; one unmetered
  AI call; LTV/DSRA uncomputed).
