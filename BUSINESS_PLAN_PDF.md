# Business-plan PDF — design & build spec (pro-memoria)

**Status:** design locked (2026-11-24). Drives the refinement of the engine's
existing PDF export (`startuplan-core/core/exports/pdf/`). Most of the machinery
already exists — this spec is **two skins + variant wiring + an explainer**, not a
rewrite.

---

## 0. One-paragraph summary

The engine already generates a branded business-plan PDF (8 chapters, a ReportLab
style system, a charts module) and a plain-English "how-to-read" guide. This spec
turns that into **two audience variants** — an **Investor** plan (warm, serif,
brand-green) and a **Lender** plan (navy institutional) — that share the same
chapters and charts but differ in **skin** and in **which metrics lead**. Prose is
a deterministic factual skeleton **refined by AI** into professional wording
(metered, with a clean fallback). A plain-English companion PDF plus inline
"in plain words" notes make the numbers legible to a non-financial founder.

## 1. Locked decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Audience | **Two variants**, founder picks by funding purpose: **Investor** & **Lender** |
| 2 | Scope | Financial chapters + **optional founder-written** soft sections (AI polishes, never invents). Later **upper-tier** add-on: AI market research with **verified, cited** sources |
| 3 | Visual | **Investor → Direction A** (serif + brand green) · **Lender → Direction B** (navy institutional) |
| 4 | Narrative | Deterministic **skeleton** (structure + correct facts; never breaks/invents) → **AI polish** for professional wording (paid default, metered ~fractions of a ¢; deterministic = free/fallback) |
| 5 | Explainer | **Both**: a separate "Understanding your numbers" companion PDF **and** inline "in plain words" callouts beside each chart |

**Hard rules.** (1) AI never invents numbers, names, dates — it only rewrites
wording of a factual skeleton. (2) The deterministic path must always succeed, so a
missing key / API error degrades to the template, never a broken export. (3) The
later research feature cites only **genuinely fetched** sources — a verified link
per claim, or the claim is dropped. No model-recalled "references".

## 2. The two variants

Same 8 chapters, same charts, same data. Two things differ: the **design tokens**
and the **Executive-Summary lead metrics / tone**.

### 2a. Design tokens

| Token | **A — Investor** (serif + green) | **B — Lender** (navy institutional) |
|-------|----------------------------------|-------------------------------------|
| paper | `#FBFAF7` warm white | `#FFFFFF` |
| ink (body) | `#2A2F2B` | `#1A1A2E` |
| strong (titles) | `#16221B` | `#002060` navy |
| muted | `#6F756E` | `#6B7280` |
| accent | `#1C6B49` forest green | `#215967` teal |
| rule | `#D7D2C7` | `#558ED5` |
| hairline | `#ECE9E1` | `#E6ECF5` |
| card fill / border | `#F2F0EA` / `#E4E0D6` | `#F0F4FA` / `#D9E1F2` |
| positive / negative | `#1E7D46` / `#B42318` (shared) | `#1E7D46` / `#B42318` (shared) |
| chart accent | `#1C6B49` | `#2E5F9E` |
| heading font | **Source Serif 4** (serif) | Inter / Arial (sans) |
| body font | Inter | Inter / Arial |

Variant **B is the current `PdfTheme`** in `styles.py` (navy/teal/pale-blue) — it
stays as-is. Variant **A** is new: a warm-paper, green-accented, **serif-headed**
theme. Serif headings need a serif TTF in the container (DejaVu Serif if present,
else add one to the Dockerfile; fall back to the sans family, never crash).

### 2b. Lead metrics & tone

| | **Investor (A)** | **Lender (B)** |
|---|---|---|
| Exec-summary opens with | NPV, revenue CAGR, year-5 revenue, gross margin, equity ask, payback | **DSCR** (min debt-service coverage), break-even, peak cash need, loan quantum & tenor, interest cover |
| Tone | opportunity, scalability, upside | resilience, repayment capacity, prudence |
| Soft sections (opt.) | Company story, Market & customers, Team, Go-to-market | usually omitted; collateral/security note if relevant |

Everything else (chapters, statements, charts) is identical — the engine already
computes all of these metrics (`narrative.compute_metrics` has NPV, payback, DSCR,
break-even, peak/min cash, CAGR, margins).

## 3. Chapters (shared skeleton)

Current `SECTION_KEYS` in `narrative.py` — kept:

1. **Executive Summary** — AI synthesis; lead metrics per variant (§2b)
2. **Company Overview** *(+ optional founder "Company story")*
3. **Business Model** *(+ optional founder "Market & customers" — Investor)*
4. **Cost Structure**
5. **Investment** (capex)
6. **Funding** (equity / grants / loans, use of funds)
7. **Financial Analysis** — Income Statement, Balance Sheet, Cash-Flow Statement, break-even, **Monte Carlo scenarios**
8. **Risks** *(+ optional founder "Team" / "Go-to-market" — Investor)*
9. **Appendix** — assumptions register + detailed tables

Optional founder sections are **only** AI-polished from the founder's own text;
absent input → section omitted (never fabricated).

## 4. Charts (one predesigned language, both variants)

Consistent with the on-screen dashboard: variant accent as the series colour,
document font, `tabular-nums`, recessive grid, emphasised endpoint, selective
direct labels, 2px surface gaps. Map:

| Chapter | Chart |
|---------|-------|
| Executive Summary | KPI tile row + headline revenue line |
| Business Model | revenue by product, stacked over years |
| Cost Structure | cost stack → EBITDA |
| Investment | capex timeline |
| Funding | sources / use-of-funds + cash-runway line |
| Financial Analysis | P&L bars · cash-flow waterfall · break-even · **Monte Carlo fan chart** |
| Risks | scenario / tornado from the Monte Carlo spread |

Chart work lives in `core/exports/pdf/charts.py`; it must read the active variant's
accent + ink + grid tokens (not hard-coded navy).

## 5. Narrative / polish

- `narrative.py` builds the **factual skeleton** (facts + numbers) — unchanged, the
  safety net.
- `plan_writer.polish_narrative` refines wording into professional prose — this is
  the **normal paid output**. It already routes through `core.ai.llm.complete`, so
  every polish call is **metered** into `ai_usage_log` (feature `narrative`).
- Default: **AI-polished on paid tiers**; free tier / AI failure → deterministic
  skeleton. Exec-summary prompt takes the per-variant lead-metric order.
- Cost: a full-plan polish is a handful of calls, cents at most — visible in COGS.

## 6. The plain-English explainer (both)

- **Companion PDF** — expand the existing `guide.py` ("how-to-read guide") into
  "**Understanding your numbers**": EBITDA, cash-flow-vs-profit, break-even, DSCR,
  NPV, depreciation — each in simple words, **using the founder's own figures**
  ("You break even in month 16, which means…"). i18n via `guide.<key>` (en/fr/uk/it).
- **Inline notes** — a small "**In plain words**" callout component beside each
  financial chart in the main plan (one or two sentences). New style in `styles.py`
  + a render helper; off for the Lender variant's most formal pages if it clutters.

## 7. Later — cited market research (upper tier)

A separate, later feature. Grounded web-search → real sources → **verify each link**
→ cite inline. Gated to top tiers (cost). Never ships recalled/invented references.
Own project; not part of this build.

## 8. Build sequence (maps to files)

Already built: 8 chapters, `styles.py` theme, `charts.py`, `guide.py`, PPTX, i18n,
AI polish seam (metered). New work:

1. **`styles.py`** — refactor `PdfTheme` to a selectable pair: `THEME_LENDER`
   (current navy) + `THEME_INVESTOR` (new green/serif). Register a serif font
   family for the Investor headings (fallback-safe).
2. **Thread `variant`** (`"investor" | "lender"`) through `template.py` / `render.py`
   / `narrative` → `export_service.build_sme_pdf_export(..., variant=...)` →
   `/plan/export` request field; infer default from funding mix (loans-heavy →
   lender) when unspecified.
3. **`charts.py`** — read accent/ink/grid from the active theme (no hard-coded navy).
4. **Exec-summary lead metrics** — per-variant ordering in `narrative._executive_summary`.
5. **Inline "In plain words"** callout style + helper; wire beside each chart.
6. **Expand `guide.py`** into the "Understanding your numbers" companion.
7. **Optional founder sections** — accept founder text, AI-polish, omit when absent.
8. **Web** — `ExportDialog` variant toggle (Investor / Lender); forward `variant`.
9. *(Later)* cited-research tier.

**First slice to ship (this session's part b):** steps 1–3 — the two themes wired
so a real **Investor** PDF and **Lender** PDF can be exported and compared.

---

*Design reference: the three-direction mockup (artifact "Business Plan Directions").
A = Investor, B = Lender were chosen from it.*
