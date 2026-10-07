# 3-Day Sprint — finalise Excel output + UI

**Focus:** finalise the **Excel output** and the **UI**.
**Deferred:** the PDF (layout already ~80% built; quicker to finish later).
**Window:** 6–8 Oct 2026 (adjust as you go).
**Optional parallel this week:** provision the Google Cloud runway — see `INFRA.md` (~20 min, no app code, de-risks deploy).

Item numbers (#) map to the original task list.

---

## Day 1 — Excel model (engine)
- [ ] **#6** Finalise the Excel **Input page**
- [ ] **#6** Finalise the **Growth-rates worksheet**
- [ ] **#7** **NPV of the options** — modelled into the Excel file

## Day 2 — Excel finish (engine)
- [ ] **#8** **Comparison of options** — comparison sheet in the Excel file
- [ ] **#9/#10** **Single-scenario Excel** export + **dashboard when one scenario only**
- [ ] **#1** Embed the **company logo** in the Excel export (upper tier, gated)

## Day 3 — UI (web)
- [ ] **#2** Separate the **left-menu sections** (add **Risk assessment**)
- [ ] **#3** Bring the **subsection buttons**
- [ ] **#4** Subdivide the **Monte Carlo** section into subsections
- [ ] **#1** **Logo upload** UI (upper tier, gated)
- [ ] **#5** **UI review** pass

---

## Deferred / backlog
- [ ] **#11** Explore other options for a project
- [ ] **#12** PDF — formal business plan (finalise the existing layout)
- [ ] **#13** PDF — explanatory business plan (variant)
- [ ] Logo in the PDF (rolls in with #12/#13)
- [ ] Italian (IT) translation pass for the exports (currently falls back to EN)

> Reminders:
> - **#7 NPV of options** and **#8 comparison of options** are **modelled into the
>   Excel file** (engine), not the web UI.
> - **No financial calculations on the client side** — the UI reads numbers from
>   the engine DTO only.
