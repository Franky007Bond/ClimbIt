## Goal

Per spec section 3.3, a browser can hold a private, unguessable trip capability in an HTTP-only cookie that is separate from maintainer sessions. The server can invalidate that capability without affecting maintainer login or any other browser's trips.

## Acceptance criteria

- [ ] With `TRIP_CAPABILITY_SECRET` unset or empty, `GET /trips/capability` returns 503 with `detail.reason` of `trip_capability_unconfigured` and does not set `climbit_trip_capability`
- [ ] `GET /trips/capability` with no trip cookie returns 200, sets `climbit_trip_capability` (`HttpOnly`, `Path=/`, `SameSite=Lax`, `Secure` when the request is HTTPS), and the JSON body does not contain the raw token or any key named `token`, `capability`, or `secret` (case-insensitive)
- [ ] A repeat `GET /trips/capability` with a valid cookie returns 200, does not rotate the cookie value, and does not create a second persisted capability record for that browser
- [ ] `GET /trips/capability` with a missing, tampered, unknown, or server-invalidated cookie returns 200, sets a new `climbit_trip_capability`, and persists a new capability whose id differs from any invalidated one
- [ ] `DELETE /trips/capability` with a valid cookie returns 204, clears the cookie, and invalidates the capability server-side so the pre-delete cookie value no longer counts as valid
- [ ] `DELETE /trips/capability` with no valid trip cookie returns 401
- [ ] After `DELETE /trips/capability`, a `GET /trips/capability` that still sends the pre-delete cookie returns 200 with a new cookie value and a new persisted capability id
- [ ] Trip capability cookies use a cookie name and signing secret distinct from `climbit_maintainer_session` / `MAINTAINER_SESSION_SECRET`; issuing or deleting a trip capability does not set, clear, or change the maintainer session cookie when both are present
- [ ] These endpoints do not accept the capability in query parameters; response `Location` headers (if any) never contain the token
- [ ] Access logs for `/trips/capability` requests log only `request.url.path` (no query string) and never contain the cookie value
- [ ] Automated tests cover the above and assert the capability token is absent from response bodies and from captured access log lines

## Out of scope

- Saving or listing trips (#35)
- Re-evaluate, delete, and expiry behavior for saved trips (#36, #37)
- Share links (#38)
- Trips UI (#39)

## Constraints

- Label: `mvp`
- Files: `backend/app/trip_auth.py`, `backend/app/api/trips.py`, `backend/app/models/trip_capability.py`, Alembic migration, `backend/app/main.py` (router registration), `backend/tests/test_trip_capability.py`, `contracts/openapi.json`, `.env.example`, `docker-compose.yml` (`TRIP_CAPABILITY_SECRET` with a dev default mirroring maintainer session)
- Follow maintainer cookie patterns in `backend/app/maintainer_auth.py` for signing, `HttpOnly`/`SameSite`/`Secure`, and 503 when the secret is missing; unlike maintainer sessions, persist each capability in the database so `DELETE` is real invalidation, not only clearing the browser cookie
- Cookie value is a signed opaque token referencing a persisted capability id; do not return that value in JSON or OpenAPI response schemas
- OpenAPI first: update the contract, export, regenerate the frontend client in the same commit as API changes (even if the frontend does not call it yet)
