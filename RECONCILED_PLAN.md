# Reconciled Build Plan — verified status

**StartUPlan · bankable plan × assistant × multilingual.** Reconciliation 2026-11-25, **verified against live code 2026-11-26** (four parallel read-only audits of both repos). Engine `startuplan-core@main` (`d171f59`, deployed) · web `StartUPlan_Web@main` (`0dc928f`, deployed). Legend: ✅ done · ◑ partial · ❌ gap.

## A. Headline corrections — plan vs. reality

The earlier plans were honest but **overstated** the remaining work. Six items moved after the code audit:

| # | Item | Plan said | Verified reality |
|---|---|---|---|
| 1 | **Project Assistant** | C2 scaffolded · C3 "verify" · C4 to-do | **DONE, wired end-to-end** — propose → Apply → recompute, answers in any language, per-user cost + 20/min + 100/day caps. **Remove from pending.** |
| 2 | **Founder sections** | engine scaffolded | Engine done **but export passes `founder=None`** → the 8 narrative sections are **dropped from today's PDF**. |
| 3 | **FCFF/FCFE + Equity IRR** | partial / unlabelled | **Already done in Excel** (labelled + Project-vs-Equity split); only the **PDF** lags. |
| 4 | **Multilingual** | English prose (gap) | Partly wired: FR/UK titles translate, `polish_narrative` exists **but is switched off**, and `it → English` bug. **Mostly wire-on, not build.** |
| 5 | **Billing Phase 1** | done | Done **except one unmetered call** — `reviewer.py` bypasses the `llm.py` wrapper. |
| 6 | **LTV / DSRA** | "not surfaced" | **Not computed at all** (worse than not-surfaced); Equity IRR exists but only in Excel. |

## B. Full status matrix (verified)

| Area / requirement | Plan | Verified (code) | Plain words | Pending? |
|---|:--:|---|---|:--:|
| Per-section generation · grounded · metered · fail-closed | ✅ | ✅ `report/generate.py`, `sections.py` | Each section is written from the model's own numbers and refuses rather than invent. | No |
| FactsContract (numbers reconciled) | ✅ | ✅ `report/facts.py` | One vetted set of figures feeds every section. | No |
| Quality gate as code (§10) | ✅ | ✅ `report/verify.py` | An automated check flags gaps before the file prints. | No |
| Engine sections 1 · 8 · 9 · 10 · 11 | ✅ | ✅ `exports/pdf/bankable.py` | The financial sections are built. | No |
| §11 scenarios + tornado + Monte Carlo | ✅ | ✅ `report/risk.py` (10k, all levers) | Up/down cases, driver ranking and a 10,000-run simulation all render. | No |
| Annexes A–G | ✅ | ✅ `exports/pdf/annexes.py` | The back-of-report detail tables are built. | No |
| KPI consistency across surfaces | ✅ | ✅ one resolver + view contract | Dashboard, Excel and PDF show identical numbers. | No |
| Core charts (DSCR-covenant · tornado · Rev/EBITDA · MC · cash) | ✅ | ✅ 6 in `exports/pdf/charts.py` | The core lender charts are built. | No |
| **Project Assistant** (Q&A + edits · any language · metered) | ◑ | ✅ **DONE, wired end-to-end** | Ask questions, propose + apply edits, any language, with cost caps — all working. | No¹ |
| Deploy-safety guards (SHA stamp + cloudbuild assert) | ◑ | ✅ **done + deployed** (`0dc928f` live) | You can see which build is live; no image ships without the stamp. | No |
| AI metering — Phase 1 (per-call cost + logging) | ✅ | ◑ done **except `reviewer.py`** unmetered | Almost every AI call's cost is logged; one path isn't. | Tiny fix |
| **Founder sections 2 · 3 · 6 · 7 · 13 · 14** | ◑ | ◑ engine done **but DROPPED from export** | The engine can render these; the PDF omits them because nothing fills them in. | **YES** |
| AI wallet / enforcement / top-up — Phase 2 | ❌ | ❌ entirely absent | No token balance, no spending limit, no way to buy more. | **YES** |
| Market §4 / Competitive §5 | ❌ | ❌ (founder or Phase-3) | No market / competitor section yet. | **YES** |
| §12 Risk register (table) | ◑ | ❌ **no table** (prose only) | No proper "risk → likelihood → impact → mitigation" table. | **YES** |
| 4th "Severe stress" scenario | ❌ | ❌ base/up/down only | The harsher stress case isn't built. | **YES** |
| CFADS waterfall table (§5.2) | ❌ | ◑ computed · **no PDF table** | Cash-to-lenders is calculated but not shown as a step-down table. | **YES** |
| FCFF/FCFE + Project vs Equity IRR | ◑ | ✅ **Excel** · ❌ **PDF** | The spreadsheet already labels/splits these; the PDF doesn't. | PDF only |
| Two-way DSCR matrix (price × volume) | ❌ | ❌ absent | No grid of debt coverage across price and volume. | **YES** |
| Break-even sentences per driver vs covenant | ◑ | ◑ one sentence | Only a single break-even line, not one per driver. | **YES** |
| KPIs: Equity IRR · LTV · DSRA | ◑ | ❌ **LTV/DSRA uncomputed** · eq-IRR Excel-only | Two lender metrics don't exist yet; shareholder return reaches only Excel. | **YES** |
| Assumptions Book (value·unit·source·date) / Glossary | ◑ | ❌ neither | No single table of every assumption, and no glossary. | **YES** |
| Multilingual ({{LANGUAGE}}) | ❌ | ◑ titles FR/UK · body EN · polish off · `it→EN` bug | Switching language changes some headings, never the sentences; Italian gets all-English. | **YES**² |
| Extra charts (EBITDA bridge · spider · debt profile · heatmap · cash-trough) | ❌ | ❌ 0 of 5 built | The five fancier charts aren't built. | **YES** |
| Inline "in plain words" callouts / explainer PDF | ◑ | ◑ guide exists · callouts no | The how-to-read guide exists; inline boxes beside charts don't. | **YES** |
| Plan schema-version migration path | pre-public | ❌ stamped, never read back | A future engine change could orphan saved plans. | **YES** |

¹ Cleanups only: a stale `/plan/assistant` docstring ("Phase 1 read-only"), language passed as `"it"` not `"Italian"`, and the assistant reusing the `export` entitlement.  ² Mostly *wire-on* — the AI polish and FR/UK chrome already exist.

## C. Best sequence to perform

Owner, in parallel (gates the beta, not in the build sequence): **provider spend caps** (OpenAI/Anthropic), **invite-only flip** (Supabase), **backups PITR** on the 1 Dec upgrade.

| # | Task | Why in this slot | Effort | Depends on |
|:--:|---|---|:--:|---|
| — | **G7 Assistant · G9 deploy guards** | ✅ already done + deployed — **not scheduled** | — | — |
| 1 | **G1 — Founder intake web UI** (+ flip the export to pass the populated inputs) | Keystone: un-drops the 8 narrative sections and makes the PDF a real lender document | L | engine ready |
| 2 | **G2 + G3 — Risk register + financial depth** (severe-stress scenario · CFADS waterfall · two-way DSCR matrix · assumptions book + glossary · **compute LTV/DSRA** · surface **FCFF/FCFE + equity-IRR in the PDF** — small · Excel payback fix) | Engine already computes the data — mostly rendering; makes it bank-grade; runs parallel to G1 | M–L | engine ready |
| 3 | **G4 — Remaining 5 charts** (EBITDA bridge · spider · cash-trough · debt profile · heatmap) | Pairs with G3's data | M | G3 |
| 4 | **G6 — Multilingual** (switch on AI polish · fix `it→English` + locale map · translate hardcoded labels · number/date formatting) | Infra already exists — turn it on; independent of intake | M | — |
| 5 | **G11 — Schema-version migration path** (read version → run migrators → deserialize) | Before real users store plans in the beta | S–M | — |
| 6 | **G10 — Billing Phase 2** (wallet · reserve→settle behind `AI_METERING_ENABLED` · Stripe top-up · token UI · admin COGS) + fix the unmetered `reviewer.py` call | Monetisation; kill-switched; after core features and once real COGS set the pricing numbers | L | pricing numbers |
| 7 | **G8 — Inline "plain words" callouts** beside charts | Polish once the content has settled | S–M | G3 · G4 |
| 8 | **G5 — Phase-3 cited market research** (§4/§5, opt-in, grounded, metered) | Opt-in upper tier; last; needs founder intake first | L | G1 |

**Critical path to a bank-grade PDF:** G1 → G2/G3 → G4.  **Deferred by decision (not pending):** equity/investor plan, investor skin, LLCR/PLCR, CFADS-vs-debt chart, BYOK (billing Phase 3).
