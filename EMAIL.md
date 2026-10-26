# Email setup — startuplan.ai

How StartUPlan sends and receives email, the locked address list, and the
setup checklist. Three independent jobs, three systems:

| Job | Handled by | DNS it uses |
| --- | --- | --- |
| **Receive** mail at `@startuplan.ai` | **Cloudflare Email Routing** (free) — *→ Google Workspace, planned (see below)* | MX (apex) |
| **Send** automated mail (auth, notifications, **invoices**) | **Resend** | SPF + DKIM on `send.` subdomain |
| **Auth** emails from the app (verify / reset) | **Supabase → Custom SMTP → Resend** | (uses Resend's sending) |

DNS for the domain is managed in **Cloudflare** (registrar stays **Namecheap**).
Sending (SPF/DKIM) and receiving (MX) use different records, so Resend and
Cloudflare Email Routing coexist with no conflict.

## Mailboxes — Google Workspace (DECIDED · the professional solution)

**Decision (26 Oct):** adopt **Google Workspace Business Starter (~$7/user·mo)**
as the professional email solution — real `@startuplan.ai` **mailboxes** instead
of forward-only aliases. Planned; **not a launch blocker** — the free Cloudflare
forwarding + Resend send-as (below) stays until the switch.

**Why:**
- real per-service **inboxes**; role addresses (`support@ billing@ hello@ privacy@`)
  as **Google Groups** — free *within* Workspace, so **one paid seat + free groups**;
- `@startuplan.ai` **everywhere**, incl. the **Google OAuth consent support email**
  (no `gmail.com` showing anywhere);
- **org-owned Shared Drives** (company docs survive people leaving);
- admin console + **enforced 2FA**, better security/credibility for a SaaS.

**Migration (≈1 h, when adopted):** verify the domain in the Workspace admin
console → create the user + groups → **repoint the apex `MX` from Cloudflare Email
Routing to Google** (MX is exclusive — Workspace *replaces* Cloudflare for
**receiving**). **Resend sending is unaffected** (SPF/DKIM live on `send.`); keep
**one SPF record per name**. After the switch, retire Cloudflare Email Routing +
the Gmail "Send mail as" aliases.

**Until then / interim:** current setup stands — Cloudflare forwarding → one Gmail
(`startuplan.ai@gmail.com`) + Resend send-as. For the **Google OAuth project set up
now**, own it under the **`startuplan.ai@gmail.com`** brand account (not the personal
`senatoriavita@gmail.com`), so no personal address appears on the consent screen.

## Locked address list

Receiving addresses forward to the owner's Gmail. Catch-all is **on** (safety
net for typos; revisit if spam grows).

| Address | Purpose | Routing |
| --- | --- | --- |
| `hello@startuplan.ai` | General / contact (on the site footer) | → Gmail |
| `support@startuplan.ai` | Customer support | → Gmail |
| `billing@startuplan.ai` | Invoices + payment replies | → Gmail |
| `privacy@startuplan.ai` | GDPR / privacy requests (privacy page) | → Gmail |
| `ceo@startuplan.ai` | Partners / investors — the "face" address | → Gmail (own label/filter) |
| `postmaster@startuplan.ai` | Deliverability / convention | → Gmail |
| `*@startuplan.ai` (catch-all) | Anything else / typos | → Gmail |
| `no-reply@startuplan.ai` | **Send-only** — Supabase auth + automated mail | not a mailbox |
| `billing@startuplan.ai` (send) | **Send-only** — automated invoices via Resend | not a mailbox |

To reply *as* an address (e.g. `hello@`) from Gmail: Gmail → Settings →
Accounts → "Send mail as", SMTP `smtp.resend.com:587`, user `resend`, password =
a Resend API key.

## Setup checklist

- [x] Cloudflare account; `startuplan.ai` added (Free plan)
- [x] Existing zone imported (4 A + `www` CNAME = Google-hosted site; Resend
      records; DMARC; Google site-verification)
- [x] Website records set to **DNS only** (grey cloud) — Google hosting breaks
      behind Cloudflare's proxy
- [x] Nameservers switched at Namecheap to `nick.ns.cloudflare.com` /
      `tina.ns.cloudflare.com` (Custom DNS)
- [x] **Cloudflare domain Active** (2026-10-25; propagated in <1 h)
- [x] **Email Routing** enabled → `hello@ support@ billing@ privacy@ ceo@
      postmaster@` + catch-all → `startuplan.ai@gmail.com` (destination verified;
      apex MX `route1/2/3.mx.cloudflare.net` added)
- [x] **Resend** domain **Verified** after the move (org `financefrollini`,
      region Ireland eu-west-1)
- [x] **Supabase → Authentication → Custom SMTP** already configured (project
      `startuplan-prod`): `smtp.resend.com:587`, user `resend`, sender name
      `StartUPlan`, key `startuplan-supabase`
- [ ] **Auto-invoice email** built into the Stripe webhook (send from
      `billing@startuplan.ai` via Resend, attach Stripe's invoice PDF) — use a
      SEPARATE backend key, not `startuplan-supabase`

## Records already in place (from the import)

- `MX send` → `feedback-smtp.*.amazonses.com` (Resend bounce handling)
- `TXT send` → `v=spf1 include:amazonses.com …` (Resend SPF, on the subdomain)
- `TXT resend._domainkey` → DKIM public key
- `TXT _dmarc` → `v=DMARC1; p=quarantine; …`
- `TXT @` → `google-site-verification=…`
- 4× `A @` → Google IPs, `CNAME www` → `ghs.googlehosted.com` (the site)

## Caveats

- **One SPF record per name.** The apex gets Cloudflare Routing's SPF; Resend's
  SPF lives on `send.` — don't create a second apex SPF.
- **DMARC is `p=quarantine`** (strict). After go-live, confirm Resend is fully
  aligned so legitimate mail isn't quarantined; relax to `p=none` temporarily
  if needed while validating.
- **Google-hosted site** → keep the A/CNAME records **DNS only**, not proxied.

## Invoices — build spec (Option A: Stripe-generated, chosen 2026-10-25)

Build on branch **`dashboard_2026_10_26`** in StartUPlan_Web.

**Decision:** let Stripe create the invoices (numbered, hosted PDF, VAT-ready
later); we just email the PDF from `billing@startuplan.ai` via Resend. No
custom PDF/numbering.

**Current state (verified):** one-time SKUs (`plan`, `bankable`) use
`mode:"payment"` and do NOT create a Stripe invoice today; the subscription
(`advisor`) does. Webhook handles `checkout.session.completed` +
`customer.subscription.updated/deleted`; it does NOT handle `invoice.paid`.

**Steps**
1. `src/app/api/checkout/route.ts` — for one-time sessions add
   `invoice_creation: { enabled: true }` so `payment`-mode checkouts produce an
   invoice + PDF. (Subscriptions already invoice.)
2. `src/app/api/stripe-webhook/route.ts` — add `case "invoice.paid":` (and treat
   `invoice.payment_succeeded` the same). Retrieve the invoice; read
   `invoice.invoice_pdf` (PDF URL) + `hosted_invoice_url` + `number` +
   `customer_email` + amount/currency.
3. New `src/lib/invoiceEmail.server.ts` — Resend send helper: fetch the PDF
   bytes from `invoice_pdf`, send via Resend with the PDF as an attachment,
   from `billing@startuplan.ai`, reply-to `hello@startuplan.ai`.
4. **Idempotency:** Stripe retries webhooks — dedupe so one invoice is emailed
   once (guard on `invoice.id`, e.g. a `sent_invoices` row or a Stripe metadata
   flag). Ack 200 even when skipping.
5. **Env/secrets:** create a SEPARATE Resend key `startuplan-backend` (Sending
   access) → set as the web deployment's `RESEND_API_KEY`. Optional
   `INVOICE_FROM=billing@startuplan.ai`. Do NOT reuse `startuplan-supabase`.

**Email content:** subject `Your StartUPlan invoice {number}`; body: thanks +
plan name + amount + link to `hosted_invoice_url`; PDF attached.

**Testing:** Stripe test mode — complete a test checkout (one-time + sub), or
`stripe trigger invoice.paid`; confirm the mail arrives from
`billing@startuplan.ai` with the PDF.

**VAT (later, not a blocker):** checkout charges net, no VAT today. Proper EU
VAT invoices need Stripe Tax + the company's VAT registration — separate task.
