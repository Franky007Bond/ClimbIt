# Agent workflow

Agents follow [`../process.md`](../process.md):

1. Pick the next open GitHub issue.
2. PM grooms it (acceptance criteria, constraints, labels).
3. Engineer implements against the criteria.
4. QA verifies with tests and checklists.
5. On PASS, the orchestrator commits, pushes, and closes the issue.

Do not skip grooming. Engineers do not close issues; QA does not fix code.
