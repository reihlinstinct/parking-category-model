# Contributing


## Issues: labels, milestones and order

The same scheme is used in every public repo. Do not add parallel label schemes.

**Labels** (every open issue has one type, one area and one priority)
- `type: feature | fix | task | docs | security` - the kind of work.
- `area: ...` - the part of the project (for example api, ci, containers, data, docs, quality, security). The list is per repo.
- `priority: high | medium | low` - high is done first.
- `status: blocked | held | in-progress | needs-review` - only when it applies. `status: in-progress` means someone claimed it.
- `needs-triage` - not sorted yet. Remove it when the three labels above are set.
- `good first issue` - small and clear, a good place to start.

**Milestones**
- `Now` - in progress or due this week. `Next` - planned after Now. `Later` - backlog.
- Every open issue is in exactly one. High priority goes to Now, medium to Next, low to Later, unless the maintainer decides otherwise. Repos may keep their own dated or goal milestones as well.

**How to pick an issue**
1. Open the repo's issues filtered by milestone `Now`, then `Next`.
2. Within a milestone, take `priority: high` first, then medium, then low. Prefer `good first issue` if you are new.
3. Skip anything with `status: blocked`, `status: held` or `status: in-progress`.
4. Comment "taking this" on the issue, then work from a fork and open a PR that references it.