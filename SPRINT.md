# Sprint — Excel finalised ✓ · now the UI

**Updated:** 9 Oct 2026
**Focus now:** the **web UI** — the left-menu restructure (#2/#3/#4) is **done**;
remaining UI is **logo upload** (#1) + the **review pass** (#5).
**Excel output:** the single-scenario export and the whole scenario model are
**done**; the 9 Oct code-review bugs (loan-name sanitize, localized jump-links)
and the income-statement green-triangle are **fixed** on `session_2026_10_09`
(see the 9 Oct section). Only a finalise-pass on #6, the #7/#8 "options" scope
question, and the remaining quality-hardening items remain on the engine.
**Deferred:** the PDFs (#12/#13) and the Italian export pass.
**Optional parallel:** provision the Google Cloud runway — see `INFRA.md`.

Item numbers (#) map to the original task list.

---

## ✅ Done (merged to main)

### Excel / engine
- [x] **#9 / #10** Single-scenario Excel export — one chosen case, full model
      (incl. depreciation + financial statements), **no up/down**, titled by the
      case number
- [x] Scenario **single source of truth** — levers flow UI → engine → Excel
      (no client-side calc; the Excel matches the screen)
- [x] IA scenario sheets (IA_B / IA_D / IA_U) + per-scenario depreciation +
      residual-value fix

### Monte Carlo (beyond the original list)
- [x] MC **config persisted** with the project (fresh each run; trials never stored)
- [x] **Latin Hypercube** sampling — second "Run" button
- [x] **Download a selected MC case** as a single-scenario Excel
- [x] **Prudent default shapes** — revenue skews to decrease, costs skew to increase

### Web UI (8 Oct — this session)
- [x] **#2** Left-menu split into **Scenarios modelling** + **Risk assessment**
      groups (Risk assessment is its own section; one source of truth)
- [x] **#3** **Sub-section buttons** / sub-navigation — one `SECTION_SUBVIEWS`
      config drives both the sidebar accordion and each section's in-section nav
- [x] **#4** **Monte Carlo** subdivided — slim run bar, charts on top, a separate
      **MC Cases** inspector; a built run persists for the session
- [x] **FS Projections** subdivided (Income / Balance / Cash flow / Ratios)
- [x] **Floating bottom nav** reworked (predictable toggle + hover-to-scroll arrows)
- [x] **Pricing board**: feature list now **derived from the entitlement contract**;
      upgrade pricing generalised (skip-tier upgrades credit what you paid)
- [x] **Working Capital** + **Tax & Dividends** gated behind the FS entitlement
      (reuse `financial_statements`; not added to the pricing board)
- [x] Fixes: `/api/scenario-defaults` 401 (missing auth token); one shared
      `authHeaders` helper (DRY)

---

## ← THIS SPRINT — the UI (web)
- [ ] **#1** Company **logo upload** (upper tier, gated) — UI
- [ ] **#5** **UI review** pass

## Excel — remaining (engine)
- [ ] **#6** Finalise-pass on the **Input page** + **Growth-rates** worksheet
      (verify vs checklist — both heavily reworked in the scenario work)
- [ ] **#14** Excel **charts** — native embedded charts across the model (e.g.
      revenue & EBITDA trend, cashflow, NPV / scenario cone, funding & debt),
      engine-generated from the sheet data (no client-side calc)
- [ ] **#15** Excel **design pass** — visual polish & consistency across every
      sheet (typography, colour/theme, spacing, borders, print layout)
- [ ] **#16** Excel **navigation dashboard** — a landing sheet with headline
      KPIs + jump-links to every sheet (one entry point into the model)
- [ ] **#7 / #8** **NPV of options** + **comparison of options** — ⚠️ *confirm scope:*
      the three scenarios (already compared in the IA sheets), or **alternative
      project plans** compared side-by-side?
- [ ] **#1** Embed company **logo** in the Excel export (upper tier, gated) — engine
- [x] **#9** Verify the **dashboard** view when only one scenario is active —
      done (web `dashboard_2026_10_09`, `995dd89`): the comparison table now
      degrades to a single column when only Base is computed; fan chart / switch
      / MC already handled it. No real path mis-rendered; this hardened the one
      latent gap.

---

## 9 Oct — Excel builder review follow-ups (engine)
From the code-quality review of `core/exports/excel` (verdict **B+**; see the PDF
`StartUPlan_Excel_Builder_Review.pdf`). Work landed on `session_2026_10_09`.

### Done ✓ (9 Oct · `session_2026_10_09`)
- [x] **(bug)** Sanitize loan names written raw in `loans_sheet.py` — formula-injection
      parity with every other writer — `e95dda8`
- [x] **(bug)** Localized per-loan "→ View" jump-links — use `ws.title`, not a hardcoded
      `#Loans!` (dangled in FR/UK builds) — `e95dda8`
- [x] **(SSOT)** Collapse the duplicate frequency map into the engine's single
      `PERIODS_PER_YEAR` — `e95dda8`
- [x] Blank the fixed-rate **"Variable Rate / Ref"** placeholder (was a stray `-`,
      the only leading-`-` text cell in the workbook) — `4df6c1a`
- [x] **Income-statement finance-cost green triangle** — root-caused and cleared:
      single consolidated **Driving Factors** row (`b94df72`) + `<ignoredErrors>`
      suppression for the residual "inconsistent formula" flag (`9c2c739`).
      Verified in a fresh export — links preserved, values unchanged, 155 tests green.
- [x] **Stable "Loan ID" cell** — show the positional label (`L1`, `L2`, …) instead
      of the engine's internal uuid, which regenerated each export because the web
      client sends no loan id (it was the *only* diff between two identical exports) —
      `4ef7b24`. Display-only; results unchanged. Two exports of one plan are now
      byte-identical.

### Remaining (quality hardening — not launch blockers)
- [x] **(DRY)** Shared `write_scenario_label` helper (replaced the copy-pasted
      label block in 7 writers) + `ExcelBuilderSME.series_scenario_total_row`
      single source (driving-factors / working-capital / cashflow delegate) —
      `b646bf3`; proven byte-identical output
- [x] **(SSOT/theme)** `declarative_builder` scenario banner now derives its
      columns + labels from `scenario_layout`; `size=12` hoisted into
      `ExcelStyleConfig.scenario_label_font_size` — `b646bf3`
  - [ ] *follow-up (optional):* hoist the remaining scattered per-sheet hex fills
        into the theme, and the leftover hardcoded `(2,10,18)` lever columns in
        `declarative_builder` — larger, lower value, higher churn
- [x] **(cleanup)** Decompose the ~450-line `create_loans_sheet` → `_write_loan_summary_block`
      + `_write_loan_blocks` (orchestrator now ~249 lines); drop dead
      `LayoutRegistry.create_parameter_named_ranges` — `92d9e9b`; byte-identical output.
      *Kept* `strict_declarative`: not dead (8+ tests + a dedicated contract test rely on
      it as a backward-compat shim).

---

## Later / backlog
- [ ] Excel **Risk Assessment page** — static MC/sensitivity charts, fed by the
      UI's already-computed result (ties into #2)
- [ ] **"Save this case"** — persist a chosen MC case's levers as a scenario
- [ ] **"Pin this run"** — optional fixed seed for a frozen report copy
- [ ] **#11** Explore other options for a project
- [ ] **#12** PDF — formal business plan (layout ~80% built)
- [ ] **#13** PDF — explanatory business plan (variant)
- [ ] Logo in the PDF (rolls in with #12/#13)
- [ ] Italian (IT) export translation (currently falls back to EN)

> Reminders:
> - **No financial calculations on the client side** — the UI reads numbers from
>   the engine DTO only.
> - **#7 / #8** are **Excel** deliverables (engine), not the web UI.
