# Source onboarding (regions and integrations)

When adding a weather, avalanche, transit, or OSM source:

1. Record terms, attribution, rate limits, and caching in [`../integrations.md`](../integrations.md).
2. Add the client behind an interface with a mock for tests (see `backend/app/planning/` adapters).
3. Extend configuration via `.env.example` only—no hardcoded secrets.
4. Add fixtures for empty, malformed, and missing-value responses.
5. Add unit tests that never touch the public network.
6. File a groomed GitHub issue before large imports or new regions.

Route seed and OSM import flows use quarantine and maintainer review—see [`route-data-review.md`](route-data-review.md).
