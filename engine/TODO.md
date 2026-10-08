# engine — things to do (startuplan-core)

Python / FastAPI engine. See `../SPRINT.md` for the 3-day plan.
Item numbers (#) map to the original task list.

> Repo: `senatoreavita/startuplan-core`

---

## Excel output — finalise  ← THIS SPRINT
- [ ] **#6** Input page finalised — verify-pass (reworked in the scenario work)
- [ ] **#6** Growth-rates worksheet finalised — verify-pass
- [ ] **#7** NPV of the options — **modelled into the Excel file** ⚠️ confirm scope
- [ ] **#8** Comparison of options — **comparison sheet** ⚠️ scenarios vs alt. plans?
- [x] **#9/#10** Single-scenario Excel export — done (single-case export; the
      `scenarios_enabled` override builds one scenario, no up/down)
- [ ] **#9** Dashboard when exporting a single scenario — verify-pass
- [ ] **#1** Embed company logo in the Excel export (upper tier, gated by access_tier)

## PDF export  (later — layout ~80% built in core/exports/pdf/)
- [ ] **#12** Formal business-plan PDF — finalise sections
- [ ] **#13** Explanatory business-plan PDF — variant
- [ ] **#1** Embed logo in PDF (upper tier)
- [ ] Italian (IT) translation (currently falls back to EN)

## Explore
- [ ] **#11** Other options for a project

---

## In progress
_(nothing active)_

## Done
- [x] **#9/#10** Single-scenario Excel export (one chosen case, full model, no up/down)
- [x] Scenario single source of truth (compute + export read the project's levers)
- [x] IA scenario sheets (IA_B/IA_D/IA_U) + per-scenario depreciation + residual fix
- [x] Monte Carlo: config-only persistence contract, Latin Hypercube sampling,
      single-case export endpoint (`/plan/export` case_levers)
- [x] AI extraction defaulted to the cheap tier (Haiku / gpt-4o-mini)

