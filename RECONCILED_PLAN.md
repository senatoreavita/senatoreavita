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
| Founder sections 2, 3, 6, 7, 13, 14 | ❌ Gap (omitted) | needs founder intake |
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

- **G1 — Founder intake (keystone).** Unlocks 8 sections (2,3,4,5,6,7,13,14). Collects inputs with
  *value·unit·source·date*; absent → stub + Open Item. Largest new user-facing surface; gates how
  "complete" a plan can be. **[L]**
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
| 5 | **G7-C2/C3/C4** assistant edits + multilingual + caps | builds on C1 | M |
| 6 | **G6** multilingual plan (shared locale layer) | shares infra with G7-C3 | M–L |
| 7 | **G8** inline callouts | polish once content settles | S–M |
| 8 | **G5** Phase-3 market research | opt-in upper tier; last | L |

**Dependencies:** G1 gates sections 2–7/13/14 and Phase-3 (G5). G6 and G7-C3 share one locale layer
— build once. G3/G4 are engine-data-ready now (no intake needed) → parallelisable with G1.

---

## 5. In progress (this session)

- **Item 0 (G9):** cloudbuild `tag==HEAD` guard; `NEXT_PUBLIC_BUILD_SHA` stamp; payback wording
  alignment (PDF "Year 8" vs Excel "7").
- **Item 1 (G7-C1):** enrich `core/ai/assistant.py build_facts()` with per-year series + formatted
  figures + bounded arrays; test that the assistant can answer a year-level question.

Each lands on its repo's session branch with tests; the deploy guards ship with the next web build.
