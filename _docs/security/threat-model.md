# ClimbIt threat model (MVP)

This document satisfies spec section 10 and issue #57. It lists abuse cases, evidence in the repo, remediation status, and residual risks.

## Assets

- Route catalog, revision history, and maintainer review queue
- Trip capabilities (browser cookie), plan runs, and share-link snapshots
- Integration credentials and session secrets (environment variables only)
- Operator telemetry (traces, metrics, logs) in the observability stack

## Trust boundaries

| Boundary | Untrusted input | Controls |
| --- | --- | --- |
| Public HTTP API | Wiki text, GPX bytes, plan origins | Validation, sanitization, rate limits, quarantine, no SSRF |
| Outbound integrations | Remote API responses | Fixed host allowlist, timeouts, typed adapters, mocks in CI |
| Telemetry export | Log/metric attributes | Collector redaction, low-cardinality labels |
| Maintainer session | Username/password | Bcrypt, server-side session secret |

## Abuse cases

| ID | Abuse case | Evidence / mitigation | Status | Residual risk |
| --- | --- | --- | --- | --- |
| A1 | XSS via wiki description or season note | `app/security/free_text.py`, wiki PATCH tests in `tests/test_security_controls.py` | Mitigated | Plain text only; no rich-text renderer on server |
| A2 | SQL injection via search or wiki fields | SQLAlchemy ORM + static check in `test_repository_modules_avoid_interpolated_sql` | Mitigated | New raw SQL must stay parameterized |
| A3 | SSRF via GPX external URLs or closure links | GPX upload test refuses `urlopen`; closure URLs stored not fetched (`test_closure.py`); outbound allowlist in `app/security/outbound.py` | Mitigated | New outbound clients must call `assert_allowed_outbound_url` |
| A4 | Secret leakage in logs or health JSON | `tests/test_logging.py`, `tests/test_health.py`, `tests/test_security_controls.py` | Mitigated | New endpoints must not echo env vars |
| A5 | Silent publish of safety-critical route edits | Protected fields require maintainer review; anonymous descriptive edits only | Mitigated | Maintainer credential compromise |
| A6 | Trip capability theft via logs or share URLs | Capabilities in HttpOnly cookies; snapshots strip origin (`trip_snapshots.py`) | Mitigated | Physical access to browser |
| A7 | Telemetry exfiltration of exact origin or auth | Collector redaction (#55), access log path/query rules | Mitigated | Misconfigured collector |
| A8 | Dependency or container CVE | CI `security-scan` job: `pip-audit` + Trivy on API image | Monitored | Zero-day in base image |
| A9 | Wiki vandalism or low-quality edits | Review queue, revision history, revert, rate limits (`test_wiki_abuse_and_revert.py`) | **Accepted** | Public wiki remains editable; quality relies on community + maintainers |

## Accepted risk: wiki vandalism

The public route wiki may receive vandalism or low-quality contributions. Mitigations are review queues, revision history, reverts, soft delete, rate limiting, provenance labels, stale-data handling, and maintainer ownership. Full prevention would require closed editing and is out of scope for MVP.

## Verification

- Security regression tests: `backend/tests/test_security_controls.py`
- Related suites: `test_gpx_upload.py`, `test_logging.py`, `test_health.py`, `test_wiki_abuse_and_revert.py`
- CI: `.github/workflows/ci.yml` job `security-scan`

## Review cadence

Revisit when adding a new outbound integration, user-upload format, or authentication mechanism.
