# Route data review

Safety-critical route fields (difficulty, closure, season, transit accessibility) require maintainer review before publication.

- Anonymous editors may change descriptive text only; protected edits land in the review queue.
- Imports from OSM or GPX start in **quarantine** until a maintainer publishes them.
- Revisions are immutable history; soft delete keeps saved trips stable with stale markers.
- Difficulty mappings live in `backend/app/data/difficulty_mappings.json`—changes require tests (see guardrail below).

Design references: [`../design/README.md`](../design/README.md).
