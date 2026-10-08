# WEB — things to do (StartUPlan_Web)

Next.js front end. See `../SPRINT.md` for the 3-day plan.
Item numbers (#) map to the original task list.

> Repo: `senatoreavita/StartUPlan_Web`

---

## UI structure  ← THIS SPRINT
- [x] **#2** Separate the left-menu sections; add **Risk assessment** as its own section
- [x] **#3** Bring the **subsection buttons** (sub-navigation)
- [x] **#4** Subdivide the **Monte Carlo** section into subsections
- [ ] **#1** Company **logo upload** (upper tier, gated)
- [ ] **#5** **UI review** pass

---

## Notes
- **No financial calculations on the client side** — all numbers come from the
  engine DTO (`/plan/compute`).
- **#7 NPV of options** and **#8 comparison of options** are **Excel** deliverables
  (modelled into the workbook), not UI — see `engine/TODO.md`.

## In progress
_(nothing active)_

## Done
- [x] **#2** Left-menu split — Scenarios modelling + Risk assessment groups
- [x] **#3** Sub-section buttons — single `SECTION_SUBVIEWS` source for the
      sidebar accordion + in-section nav
- [x] **#4** Monte Carlo subdivided — run bar + charts + separate MC Cases inspector
- [x] FS Projections subdivided (Income / Balance / Cash flow / Ratios)
- [x] Floating bottom nav reworked (toggle + hover-to-scroll edge arrows)
- [x] Pricing board — feature list derived from the entitlement contract;
      upgrade pricing generalised (skip-tier upgrades credit what you paid)
- [x] Working Capital + Tax & Dividends gated behind the FS entitlement
- [x] Fix `/api/scenario-defaults` 401 (auth token) + one shared `authHeaders` helper
- [x] Scenario levers = single source of truth (UI persists to project, sends to
      engine for compute **and** export)
- [x] Monte Carlo config persisted with the project (fresh each run)
- [x] Latin Hypercube — second "Run" button
- [x] Download a selected Monte Carlo case (single-scenario Excel)
- [x] Prudent default MC distribution shapes (revenue down, costs up)
