# Sprint — Excel finalised ✓ · now the UI

**Updated:** 8 Oct 2026 (eve)
**Focus now:** the **web UI** — the left-menu restructure (#2/#3/#4) is **done**;
remaining UI is **logo upload** (#1) + the **review pass** (#5).
**Excel output:** the single-scenario export and the whole scenario model are
**done** (see below). Only a finalise-pass on #6 and the #7/#8 "options" scope
question remain on the engine.
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
- [ ] **#7 / #8** **NPV of options** + **comparison of options** — ⚠️ *confirm scope:*
      the three scenarios (already compared in the IA sheets), or **alternative
      project plans** compared side-by-side?
- [ ] **#1** Embed company **logo** in the Excel export (upper tier, gated) — engine
- [ ] **#9** Verify the **dashboard** view when only one scenario is active

---

## 9 Oct — Excel builder review follow-ups (engine)
From the code-quality review of `core/exports/excel` (verdict **B+**; see the PDF
`StartUPlan_Excel_Builder_Review.pdf`). Priority order:
- [ ] **(bug)** Sanitize loan names written raw in `loans_sheet.py` (lines 297 / 655 / 727)
      — formula-injection parity with every other writer (which already sanitize)
- [ ] **(bug)** `loans_sheet.py:526` hardcodes `#Loans!` in the per-loan jump links —
      breaks in FR/UK builds where the tab is localized; use `ws.title`
- [ ] **(SSOT)** Collapse the duplicate frequency map (`loans_sheet.py:703`) into the
      already-imported engine `PERIODS_PER_YEAR`
- [ ] **(DRY)** Extract one shared scenario-stacking + label helper (removes the
      copy-pasted idiom from 7 writers) and `_series_row` onto the builder
- [ ] **(SSOT/theme)** Derive `declarative_builder.py:289` from `scenario_layout`;
      promote scattered hex colors + `size=12` literals into the theme
- [ ] **(cleanup, later)** Decompose the ~450-line `create_loans_sheet`; drop dead
      `strict_declarative` param + `LayoutRegistry.create_parameter_named_ranges`

> Items 1–3 are small, surgical and covered by the existing snapshot tests.
> This is quality hardening, not a launch blocker — the two bugs are worth doing
> before 1 Dec.

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
