# BACKUPS — database backups & restore drill (Supabase)

What this protects against: **data loss** — a bad migration, a wrong `DELETE`,
a bug, or a platform problem that damages the database. It is **not** about
privacy/isolation (users seeing each other's data — that is covered by RLS and
already audited). Different risk, different fix.

The point of this file is the **restore drill**: proving — calmly, once, before
launch — that a backup actually restores and that you know the steps. A backup
you have never restored is a guess, not a safety net.

> Scope: the **production Supabase project** (EU region, to match
> `startuplan-prod` / `europe-west1`). The critical data is the Postgres tables
> below; everything else is either managed by Supabase or regenerable.

---

## What is already automatic (and what to turn on)

| Plan | Daily backups | Point-in-Time Recovery (PITR) |
|------|---------------|-------------------------------|
| Free | none — **not safe for prod** | no |
| **Pro** | **yes, daily, 7-day retention** (automatic) | **add-on — turn this on** |

Two actions, both in the dashboard (*Project → Database → Backups*):

1. **Be on Pro before launch.** Free-tier projects have no scheduled backups —
   a launch DB must be at least Pro.
2. **Enable PITR.** Daily snapshots can lose up to ~24 h of data (everything
   since the last nightly). PITR lets you restore to *any second*, so a 2 p.m.
   mistake can be undone to 1:59 p.m. For a product taking real customer data,
   this is worth the add-on.

That is the entire "turn on backups" task. The rest of this file is the drill.

---

## The restore drill (do once before launch, then quarterly)

The safe way to drill is **never on prod**. Do not use the dashboard's in-place
"Restore" button as a test — on a scheduled backup it **overwrites** the current
database. Instead, restore a *copy* into a throwaway database and inspect it.

### Step 1 — Download a backup
Dashboard → *Database → Backups* → pick the latest daily backup → **Download**.
You get a `.backup` / `.sql` dump file. (If only PITR is enabled with no
downloadable daily, use `pg_dump` against prod from your own machine instead —
see the box at the bottom.)

### Step 2 — Spin up a throwaway target
Either is fine — pick one:
- **Local (fastest):** `docker run --rm -d --name drill -e POSTGRES_PASSWORD=drill -p 5433:5432 postgres:16`
- **Scratch Supabase project:** create a new free project, use its connection string.

### Step 3 — Restore the copy into it
```bash
# plain SQL dump:
psql "postgresql://postgres:drill@localhost:5433/postgres" -f ./backup.sql
# custom-format dump (.backup):
pg_restore -d "postgresql://postgres:drill@localhost:5433/postgres" --no-owner ./backup.backup
```

### Step 4 — Verify it actually came back (the real test)
Connect to the restored copy and run:
```sql
-- (a) the critical tables exist and hold rows
select 'profiles' t, count(*) from profiles
union all select 'projects',       count(*) from projects
union all select 'project_inputs', count(*) from project_inputs
union all select 'project_outputs',count(*) from project_outputs
union all select 'export_files',   count(*) from export_files
union all select 'payments',       count(*) from payments
union all select 'subscriptions',  count(*) from subscriptions
union all select 'entitlements',   count(*) from entitlements
union all select 'tier_grants',    count(*) from tier_grants
union all select 'custom_inquiries',count(*) from custom_inquiries;

-- (b) a known project you recognise is present and whole
select id, owner_id, created_at from projects order by created_at desc limit 5;

-- (c) auth users came across (sign-ins depend on this)
select count(*) from auth.users;
```
**Pass =** the counts look right (not zero, roughly matching prod), your known
project is there, and `auth.users` is non-empty. Then **tear the copy down**
(`docker rm -f drill`, or delete the scratch project).

### Step 5 — Record it
Fill one row in the log at the bottom. That row *is* the deliverable — it is how
"restore drill" gets ticked off in the timeline / Mission Control.

---

## Two things the DB backup does NOT cover

- **Storage files** (`exports` bucket — the generated Excel / PDF files). Daily
  DB backups do **not** include Storage objects. Low impact: exports are
  **regenerable** — re-running the engine on a project's `project_inputs`
  reproduces them — so they are not critical to back up. Worth knowing, not
  worth a separate backup system.
- **Secrets** (API keys, service-role key). Those live in Google Secret Manager
  (see `INFRA.md`), not in the database, and are not in these backups.

---

> **Alternative: your own off-platform copy.** If you ever want a backup that
> does not depend on Supabase at all, run this from your machine (the password
> is a prod secret — never paste it into chat or commit it):
> ```bash
> pg_dump "$SUPABASE_DB_URL" -Fc -f "startuplan_$(date +%F).backup"
> ```
> Store it somewhere durable (e.g. a GCS bucket). This is optional — Supabase's
> managed daily + PITR is enough for launch. Automating it is a later task, not
> part of this drill.

---

## Drill log

| Date | Who | Backup used | Result | Notes |
|------|-----|-------------|--------|-------|
| _tbd_ | — | — | — | first pre-launch drill — fill this in |
