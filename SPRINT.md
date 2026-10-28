# Sprint — Excel finalised ✓ · now the UI

**Updated:** 28 Oct 2026 · 21:14 UTC
**Now (wk 4 · 26–30 Oct):** two big product builds landed — the **Export Center**
(export dialog: Excel + scenario scope · business-plan PDF · pitch-deck PPT ·
how-to-read guide) and the **Project Assistant** (floating, project-scoped chat:
grounded answers + model-change proposals you Apply → recompute). Plus the
growth-rows switchboard + workbench rebuild + Detailed ratios, and the dashboard
KPI band + status badge + live net-CF chart (see the **28/27 Oct** sections).
Sensitivity Excel sheet + entitlements v6 + email stack landed 26 Oct.
**Carried from wk 1–2:** UI review **#5** (wk 1), Excel design **#15** + nav
**#16** (wk 2), logo **#1**. _Historical narrative below._

**Focus (historical · wk 2 · 12–16 Oct):** the **Excel presentation workstream** —
**#14 charts done ✓** (14 Oct: 8-chart Summary dashboard + the KPI ratios board);
**#15 design pass** + **#16 nav dashboard** in progress. In parallel on the web:
**logo upload** (#1) + the **UI review pass** (#5).
**Excel output:** the single-scenario export and the whole scenario model are
**done**; the 9 Oct code-review bugs (loan-name sanitize, localized jump-links)
and the income-statement green-triangle are **fixed** on `session_2026_10_09`
(see the 9 Oct section). Only a finalise-pass on #6, the #7/#8 "options" scope
question, and the remaining quality-hardening items remain on the engine.
**Deferred:** the PDFs (#12/#13) and the Italian export pass.
**Optional parallel:** provision the Google Cloud runway — see `INFRA.md`.

Item numbers (#) map to the original task list.

---

## 28 Oct — Export Center + Project Assistant (core `session_2026_10_28` · web `dashboard_2026_10_28`)

Two feature builds, each phased like the Export Center was (modal → formats → polish).

- [x] **Export Center** — an **"Export model" dialog**: pick a format — **Excel**
      (with a **scenario scope**: base only, or all 3 cases) · **business-plan PDF**
      · **pitch-deck PPT** · **how-to-read guide**. Engine exporters
      (`build_sme_excel_export` / `_pdf_` / `_pptx_` / `_guide_export`), the web
      `ExportDialog`, `/api/export` routing (format + scope), and tests. The PPT path
      needs **`python-pptx`** installed on the engine (else 502); the business-plan
      narrative is a **template + optional OpenAI polish**. *This delivers the deferred
      business-plan PDF (#12/#13).*
- [x] **Project Assistant** — a **floating, draggable/resizable, project-scoped chat**
      in the dashboard: **grounded answers with citations** + **model-change proposals**
      you **Apply → recompute**, validated against an **editable-field whitelist**
      (addressed by **name, never index** — no off-catalog write lands). Small/large
      **model tiers**, a per-user **cost meter + rate/daily caps**, a **fail-closed scope
      guard**. Engine `/plan/assistant` (grounded facts + strict JSON answer|proposal|
      refusal) + web `/api/assistant` + `AssistantDrawer` + tests. **Needs
      `OPENAI_API_KEY` on the engine** to answer live (fails closed with "not available"
      otherwise). Later follow-ups: Light·Dark·Auto theme toggle + bottom-right resize
      grip on the card. *First build of the AI-copilot spec.*
- [x] **Tests** — engine export-endpoint (scope/pdf/pptx/guide) + assistant
      (facts/parse/catalog/validation/red-team/tiers) + pptx-deck; web assistant-patch +
      route + dialog. Both suites green (web **462**).
- [ ] **Deploy prerequisites (owner):** `pip install python-pptx openai` on the engine
      + set `OPENAI_API_KEY`, then restart — both features are code-complete but dormant
      until the engine has them.

---

## 27 Oct — Growth-rows + workbench rebuild + dashboard (core `session_2026_10_27_A` · web `dashboard_2026_10_27`)

- [x] **Detailed ratios / ratio catalog** — single-source ratio catalog module +
      per-family ratio sheets + a **Detailed ratios** tab (Ratios → Key ratios); D-nav +
      i18n (en/fr/uk/it). *(extends #14)*
- [x] **Growth-rows switchboard** — per-line **±pp** block with per-item appraisal
      **re-chaining from `gr`** (drag-safe), i18n across all languages, parametrized
      fidelity + structure tests.
- [x] **Workbench rebuild** — house grid (years from **D**), banner/TOC via
      `write_sheet_index`, **exact per-item growth** (`gr` rate + pp) **plus level**,
      detail tables in the TOC (collapsed by default), recalc-verified for
      tie/level/growth; snapshots/goldens regenerated, full sweep green, render-checked.
- [x] **Dashboard (web)** — compact switchboard with **level vectors moved to a hidden
      engine block**, a **KPI band + context-aware status badge**, and a **live net-CF
      chart** (house style) + a base net-CF row. Fidelity/gating/snapshot tests green.
- [x] **Unit Economics** (CAC/LTV/ARPU) — **removed from launch scope**: engine+web
      clean-delete, logic kept as a note.

---

## 26 Oct — Sensitivity + ratios + entitlements (core `session_2026_10_26`)

- [ ] **Sensitivity Excel sheet** ("Sens" / `sh_Sens`) — **under construction.** A
      one-way **NPV tornado** (diverging floating bars) + a **switching-values
      (break-even)** table + a live chart-data table, under a house banner/TOC index.
      Base NPV links live to IA_B; shock figures are a snapshot. Core built; iterating
      on presentation. *(advances #15/#16; new Risk/Excel deliverable)*
- [x] **Entitlements v6** — **sensitivity moved to Plan (tier_1)**; Monte Carlo stays
      Bankable (tier_2). Shared contract + engine gate + web UI gate flipped; sensitivity
      is now the 3rd Excel-gating key (tier-matrix regenerated).
- [x] **Per-family ratio sheets** + single-source **ratio catalog** module + a
      **Detailed ratios** tab (Ratios → Key ratios); D-nav buttons; i18n (en/fr/uk/it). *(extends #14)*
- [x] **Feature × tier** comparison table (generator + `docs/tier-matrix.md`).
- [x] **Email infrastructure** for startuplan.ai — receive + send + auth working
      (Cloudflare Email Routing + Resend + Supabase SMTP + Gmail send-as). See `EMAIL.md`.
- [x] **Dashboard nav** — sensitivity surfaced at Plan; contract-driven tier-lock cues
      from one source of truth; section reorder; redundant middle sub-view rows removed.
- [ ] **Next (queued for tomorrow):** build the **Sens Check** live what-if sheet —
      parallel pre-tax appraisal, pristine base, `v.Sens_*` multipliers; spec in the
      build-brief PDF (engine-fidelity clause §8).

---

## 15 Oct — session · launch infra (web `dashboard_2026_10_16` · pushed, pending merge)

The three launch-blockers from the timeline — **payments**, **security**,
**log-in-with-Google** — all landed in code this session. Stripe and Google
await only the owner's external account setup; see
`StartUPlan_Web/docs/SETUP_payments_auth_security.md`.

- [x] **Stripe test-mode checkout → entitlements** — `api/checkout` (hosted
      session, buyer id from the verified session) + `api/stripe-webhook` (the
      only writer of paid `tier_grants`: grant on paid checkout, renew/revoke on
      subscription events; signature-verified, idempotent). Catalog-derived
      price→tier map (one `STRIPE_PRICE_<PLAN>` env var each). The upgrade modal's
      Buy button now starts real checkout outside internal trial mode. Runs fully
      in **test mode** (`sk_test_…`, test cards) — no legal entity, no real money.
      *Owner to do:* create the Stripe account + 3 products/prices + webhook
      secret (steps in the setup doc).
- [x] **Security — RLS drift guard** — a static test
      (`supabase/migrations/rls-coverage.test.ts`) that fails the build if any
      `public` table ships without RLS, if a `user_id` table has a
      non-owner-scoped policy, or if any policy is unconditionally permissive.
      Passes on the current schema; guards every future migration.
- [x] **Google OAuth** — the easier provider; the code was already complete
      (buttons, `signInWithOAuth`, `/auth/callback`). No code change — documented
      the Supabase + Google-Cloud config. *Owner to do:* create the Google OAuth
      client and paste it into Supabase → Providers → Google.
- [ ] **Apple (iCloud) OAuth** — deferred: needs the paid Apple Developer
      account ($99/yr), a Service ID, a `.p8` key and domain verification. Hide
      the button with `NEXT_PUBLIC_OAUTH_APPLE=false` until then.
- [x] +22 tests (checkout 8, webhook 10, RLS 4); full web suite **389 green**;
      `tsc` clean.

---

## 15 Oct — session (merged to main · core `session_2026_10_15` → main, web `dashboard_2026_10_15` → main)

**Excel / engine**
- [x] **Equity IRR & MOIC** now computed (`ratios.py`) — shareholder cash flow
      (capital in, dividends out, book-equity exit); mirrored in the KPI sheet as
      live formulas. They were the last engine-`None` valuation ratios. *(extends #14)*
- [x] **Magnitude-adaptive number formats** — one SSOT rule (`adaptive_decimals`):
      a vector keeps 2 dp while small, drops to whole from 1000 up, decided per
      vector from the engine-projected peak. Applied to the Revenue / Opex / Staff /
      COGS / Capex driver matrices + grand totals. *(part of #15)*
- [x] **Decade-start layout rule** across every series sheet incl. IS / BS / CF —
      the first table opens on a clean decade row after the index (one SSOT). *(part of #15)*
- [x] KPI sheet: whole-plan scalars (NPV / IRR / CAGR / EV …) moved to the **first**
      (visible) column, not hidden in the last. *(part of #15)*

**Web UI**
- [x] **Unit Economics section** — CAC / churn / gross-margin-per-customer + a
      manual per-year active-customers grid … *(new; served #5)* — **⚠ later REMOVED
      (26 Oct): cut from launch scope; clean-delete across engine + web, logic kept as a note.**
- [x] **Magnitude-adaptive decimals** in the input/output grids + the output
      matrices (`ProjectionTable`, full scale); **section descriptions → a
      circled-i hover tooltip** (no longer a line under the title). *(part of #5)*
- [x] ~~*follow-up:* gate the Unit Economics section to subscription industries~~ —
      **moot: Unit Economics REMOVED from launch scope (26 Oct).**

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
- [ ] **#5** **UI review** pass *(wk 1)* — incl. **mobile-usable landing / auth /
      pricing** (not a rewrite) · **not done**

## Excel — remaining (engine)
*Schedule: **#6 this week (wk 1)**, then the **Excel presentation workstream
#14–#16 next week (wk 2 · 12–16 Oct)**.*
- [x] **#6** Finalise-pass on the **Input page** + **Growth-rates** worksheet
      (verify vs checklist — both heavily reworked in the scenario work) · *wk 1* —
      **done ✓**: 18/18 live-build checklist checks pass (reference integrity,
      clamp parity `=MAX(-0.95,MIN(5.0, base + Inputs!lever))`, completeness,
      free⊆premium subset, presentation) + 180 targeted tests green
      (inputs / gr / scenario / numeric + UI↔Excel parity). No defects found;
      aesthetic polish rolls into #15. Premium sample workbook shared for the
      visual check.
- [x] **#14** Excel **charts** — **done ✓** (14 Oct, `session_2026_10_14`):
      an 8-chart live **Summary dashboard**, all native + recalculating from a
      live chart-data block (no client-side calc) — revenue/EBITDA/net income,
      EBITDA & net margin, operating-cost composition, cash flow & break-even
      (live dynamic break-even marker), cash balance, capex, NPV & IRR by
      scenario. Also the **KPI sheet rebuilt as the full ratios board** (every
      engine ratio from `build_ratios` as a live Excel formula; CAPM / unit-
      economics inputs exposed). Parity + gating + golden fixtures; full suite
      green (1508). · *wk 2*
- [ ] **#15** Excel **design pass** — visual polish & consistency across every
      sheet (typography, colour/theme, spacing, borders, print layout) · *wk 2* —
      **in progress**: chart house-style + the per-sheet top nav band / autofit
      landed with #14/#16; the full cross-sheet polish pass remains.
- [ ] **#16** Excel **navigation dashboard** — a landing sheet with headline
      KPIs + jump-links to every sheet (one entry point into the model) · *wk 2* —
      **in progress**: the KPI/Summary landing + the per-sheet "⬅ Go to dashboard"
      nav band are in; the jump-links-to-every-sheet index is the remainder.
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
- [ ] **Export builder dialog** — "Export model" opens a form: tick which
      tables/sections to include/exclude (and extract a single table with its
      explanation), and choose the format — **Excel** (built), **PDF** (#12/#13),
      **PowerPoint (PPT)** (new). Web: the dialog UI. Engine: exporters take an
      include-manifest; add a PPTX exporter.
- [ ] **#11** Explore other options for a project
- [ ] **#12** PDF — formal business plan (layout ~80% built)
- [ ] **#13** PDF — explanatory business plan (variant)
- [ ] Logo in the PDF (rolls in with #12/#13)
- [ ] Italian (IT) export translation (currently falls back to EN)
- [ ] **Google Workspace migration** (Business Starter ~$7/user·mo) — real
      `@startuplan.ai` mailboxes + free Groups for role addresses; repoint apex
      **MX Cloudflare → Google** (Resend sending unaffected); then retire
      Cloudflare Email Routing + the Gmail "Send mail as" aliases. **Not a launch
      blocker.** Decided 26 Oct — see `EMAIL.md`.
- [ ] **At the Streamlit → Next.js cutover: wire the ops-watcher helpers.** The
      watcher is the Cloud Run job in `startuplan-ops`; do this while already in
      GCP for the deploy (needs Secret Manager + a static egress IP for the
      Namecheap whitelist). (1) Drop in `ops/namecheap_expiry.py` + replace the
      `.ai` RDAP branch with `check_domain_expiry()` → turns the domain line green
      with the real registrar expiry (2029-08-05). (2) Use
      `ops/mission_control_status.build_status_doc(http, tls, domain)` to write the
      full `status/site` doc each run (fresh `checked_at`) so the Live-status card
      self-refreshes instead of freezing. Then flip Mission Control's **"Live site
      — Streamlit"** card → Next.js and start the Streamlit retirement (closes
      SEC-2). Helpers + wiring steps are in `ops/README.md`. **Not a launch
      blocker.**

> Reminders:
> - **No financial calculations on the client side** — the UI reads numbers from
>   the engine DTO only.
> - **#7 / #8** are **Excel** deliverables (engine), not the web UI.
