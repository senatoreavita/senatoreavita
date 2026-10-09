# Planning repo — conventions for Claude

This repo holds the launch planning for StartUPlan (`SPRINT.md`) and backs the
planning artifacts on claude.ai (Launch Timeline, Mission Control, Launch
Readiness, etc.).

## Standing rules

- **Always bump the "Updated" date/time.** Whenever you edit **or** republish
  the **Launch Timeline** or **Mission Control** artifacts, set their
  displayed "Updated" stamp to the **current UTC time** (run `date -u`) before
  publishing. The timeline stores it in the `UPDATED` constant; Mission Control
  has its own stamp — update whichever the file uses. Do this on every single
  republish, even a one-line change.
- When you tick a task done in `SPRINT.md`, also flip the matching bar in the
  Launch Timeline artifact to `done` so the two stay in sync.
