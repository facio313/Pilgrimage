# Pilgrimage portfolio SSO contract

Pilgrimage trusts an Authelia identity only when every protected request contains
both the proxy identity headers and the Pilgrimage-specific
`X-Portfolio-Edge-Secret`. The host proxy must delete client-supplied values for
all of these headers and then inject its own values. The frontend proxy forwards
them to Django; it never manufactures them.

## Edge secret

Production Compose should set `PILGRIMAGE_SSO_EDGE_SECRET_HOST_FILE` to the
absolute host path of a dedicated secret. Compose bind-mounts it read-only at
`/run/secrets/pilgrimage_sso_edge_secret` and sets
`PILGRIMAGE_SSO_EDGE_SECRET_FILE` to that stable in-container path. Direct
backend runs may set `PILGRIMAGE_SSO_EDGE_SECRET_FILE` themselves. The file
must:

- contain 32–512 bytes of printable ASCII without whitespace;
- be a regular file, not a symlink;
- be `cks:cks` with mode `0640` on the rootless Docker host. Rootless UID/GID
  mapping presents that file as `root:root 0640` inside the container;
- be read by the backend running as non-root UID `10001` with effective GID
  `0`. The validator accepts this exact container ownership/mode contract and
  rejects group-writable or world-accessible files.

For a direct backend process outside Compose, an alternative file owned by the
runtime user with mode `0400` or `0600` is accepted. Do not use host mode `0600`
for the rootless Compose bind mount: it maps to container owner `root` and is
therefore unreadable by UID `10001`.

`PILGRIMAGE_SSO_EDGE_SECRET` is a development fallback. The file takes
precedence when both are configured. Never reuse another application's edge
secret and never place the production value in Compose, Git, logs, or image
layers.

When SSO is disabled, Compose defaults the source mount to `/dev/null`, so the
application remains usable without creating a secret. Enabling SSO without a
valid host file fails closed during Django startup.

The host must inject the secret only for protected API paths. It must not inject
identity headers or the edge secret into `/api/health/` or
`/api/shared/:token/`. The baked frontend Nginx configuration clears those
headers again for both public paths as defense in depth.

## Identity and token binding

`Remote-User` is the stable external subject. It is stored in the unique
`User.sso_subject` field and cannot be changed or cleared after it is linked.
Pilgrimage does not look up or link accounts by Django `username`.

SSO refresh and access tokens contain the `sso_subject` claim. In SSO mode,
every authenticated access, refresh, and logout request must satisfy all of the
following:

1. the edge secret is valid;
2. current `Remote-User` equals the token subject;
3. the token subject equals the current user's immutable `sso_subject`;
4. the user is active.

Tokens issued before this migration intentionally stop working in SSO mode.

## Existing account link procedure

The migration does not infer that an existing email is verified and does not
backfill subjects. Before enabling the new image for an existing account, an
operator must verify the local email out of band and approve exactly one user:

```bash
python manage.py prepare_sso_link \
  --user-id '<existing-user-uuid>' \
  --verified-email '<verified-central-email>'
```

On the next valid SSO exchange, Pilgrimage links that one active account only
when the case-insensitive email match is unique, `email_verified` is true, and
the one-time `sso_link_allowed` flag is true. The flag is consumed immediately.
If any condition fails, the exchange returns HTTP 409 instead of taking over an
account. New central subjects receive a new internal user with an opaque Django
username.

For a safe rollout, apply migration `users.0002_user_sso_identity`, approve the
existing user, mount the edge secret, update the outer proxy header injection,
and only then send traffic to the new containers.

## Deployment validation gate

`.github/workflows/deploy.yml` runs an x64 validation job before the ARM64 image
build and production deploy. The job uses isolated PostGIS and Redis services,
runs full backend Ruff checks, checks for migration drift, applies all
migrations, runs pytest, runs the frontend tests and production build, and
validates the Compose configuration. The build/deploy job has `needs: validate`,
so none of its image pushes or SSH steps can run after a failed validation.
Generated Django migration files are the only Ruff exclusion; all application
source remains part of the full backend lint gate.

CI deliberately sets `PILGRIMAGE_SSO_ENABLED=false` and never reads the
production edge-secret file. Its 20-minute timeout plus the dependent
build/deploy job's 40-minute timeout caps the sequential workflow budget at 60
minutes.

## Logout and public/readiness endpoints

`POST /api/auth/logout/` blacklists the submitted refresh token. The browser
attempts this local revocation and always clears its persisted tokens before
redirecting to central Authelia logout, even if local revocation fails.

Public shares return HTTP 404 when the token is missing or expired. Public share
and readiness views disable DRF authentication so forged identity, edge-secret,
or Authorization headers are ignored. `/api/health/` reports ready only when
both PostgreSQL and Redis answer their probes and otherwise returns a generic
HTTP 503 without dependency error details.

Production uses the digest-pinned `pilgrimageRedis` service on the private
`pilgrimage` network with no published host port. Its AOF data lives in the
dedicated `pilgrimage_redis_data` volume; application deploys must preserve that
container and volume and must not attach to another portfolio application's
Redis.
