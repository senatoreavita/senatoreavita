# Email setup — startuplan.ai

How StartUPlan sends and receives email, the locked address list, and the
setup checklist. Three independent jobs, three systems:

| Job | Handled by | DNS it uses |
| --- | --- | --- |
| **Receive** mail at `@startuplan.ai` | **Cloudflare Email Routing** (free) | MX (apex) |
| **Send** automated mail (auth, notifications, **invoices**) | **Resend** | SPF + DKIM on `send.` subdomain |
| **Auth** emails from the app (verify / reset) | **Supabase → Custom SMTP → Resend** | (uses Resend's sending) |

DNS for the domain is managed in **Cloudflare** (registrar stays **Namecheap**).
Sending (SPF/DKIM) and receiving (MX) use different records, so Resend and
Cloudflare Email Routing coexist with no conflict.

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
- [ ] **Cloudflare domain Active** (propagating; 1–2 h typical)
- [ ] **Email Routing** enabled → the addresses above created → verify the Gmail
      destination (adds the apex MX)
- [ ] **Resend** still shows domain **Verified** after the move
- [ ] **Supabase → Authentication → Custom SMTP** = `smtp.resend.com:587`,
      user `resend`, pass = Resend API key, sender `no-reply@startuplan.ai`
- [ ] **Auto-invoice email** built into the Stripe webhook (send from
      `billing@startuplan.ai` via Resend, attach Stripe's invoice PDF)

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

## Invoices

Trigger = the existing Stripe webhook (`/api/stripe-webhook` in StartUPlan_Web)
on `checkout.session.completed` / `invoice.paid`. Email the customer from
`billing@startuplan.ai` via the Resend API, attaching Stripe's hosted invoice
PDF. Engine already scaffolds `RESEND_API_KEY` in `infra/settings.py`.
