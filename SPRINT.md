# Sprint — Excel finalised ✓ · now the UI

**Updated:** 8 Oct 2026
**Focus now:** the **web UI** — Risk-assessment section, sub-navigation, Monte-Carlo
sub-sections, logo upload, review pass.
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

---

## ← THIS SPRINT — the UI (web)
- [ ] **#2** Separate the left-menu sections; add **Risk assessment** as its own section
- [ ] **#3** **Sub-section buttons** (sub-navigation)
- [ ] **#4** Subdivide the **Monte Carlo** section into sub-sections
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
