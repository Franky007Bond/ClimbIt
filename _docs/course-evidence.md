# Course deliverables and peer review

ClimbIt targets the [AI Dev Tools Zoomcamp final project](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md).

## Task tracker

Public backlog: [GitHub Issues](https://github.com/Franky007Bond/ClimbIt/issues) with groomed acceptance criteria (`mvp` / `post-mvp` labels). Process: [`process.md`](process.md).

## Agent evidence

When an agent completes a task, record handover in:

- The issue QA comment (`QA-VERDICT: PASS|FAIL`).
- [`evidence/README.md`](evidence/README.md) index for cross-issue drills.
- Operations drills under [`operations/evidence/`](operations/evidence/).

## Peer review (required to pass)

From the course README:

- You must **review three other participants' projects**.
- Submitting without peer reviews does **not** pass, regardless of project quality.
- **Exact deadlines and review workflow** are on the [course platform](https://courses.datatalks.club/ai-dev-tools-2026/) (check each cohort for current dates).

## Rubric mapping

| Criterion | Evidence in this repo |
| --- | --- |
| Product specification | [`specs.md`](specs.md), issues with acceptance criteria |
| Agent team | [`process.md`](process.md), [`agent/team-roles.md`](agent/team-roles.md) |
| Context management | [`../AGENTS.MD`](../AGENTS.MD), [`agent/`](agent/) |
| Application | `backend/`, `frontend/`, Compose |
| Testing | `uv run pytest`, frontend Vitest, CI |
| Containerization | `docker compose up` |
| Deployment | [`operations/deployment.md`](operations/deployment.md) |
| CI/CD | [`.github/workflows/`](../.github/workflows/), [`ci.md`](ci.md) |
| Observability | [`../observability/README.md`](../observability/README.md) |
| Alerting | Plan failure rate alert + drill |
| On-call agent | [`operations/oncall-responder.md`](operations/oncall-responder.md) |

Pass threshold: **10 / 24** points across 12 criteria.
