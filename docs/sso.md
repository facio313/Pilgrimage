# Pilgrimage portfolio SSO contract

## Branch-bound mode selection

Authentication mode is derived by `scripts/portfolio-auth-mode.sh`. The
resolver uses `PORTFOLIO_BRANCH`, then `GITHUB_REF_NAME`, then the current Git
branch. `main` and `dev` are always `sso`; all other branches are `local`.
`PORTFOLIO_AUTH_MODE` may be supplied as an assertion, but a mismatch fails
before Django or Vite starts. Packaged builds and containers must explicitly
inject the branch and mode; only a local checkout may rely on Git detection.

The existing `PILGRIMAGE_SSO_ENABLED` and `VITE_SSO_ENABLED` variables remain
compatibility adapters. If explicitly set, each must agree with the canonical
mode. SSO backend startup requires a valid edge secret. A local branch does not
load or require the central edge secret and keeps registration and password
login available.

`npm run dev` and `npm run preview` are deliberately local-auth commands. They
assert `PORTFOLIO_AUTH_MODE=local` through the resolver and therefore fail
immediately on `main` or `dev`; use a non-main/dev branch for interactive local
development.

Vite authentication flags are compiled into the static frontend bundle. The
final Nginx image's canonical environment values and
`org.opencontainers.image.ref.name` / `io.bonifacio.portfolio.auth-mode` labels
are deployment audit metadata, not runtime switches. A mode change requires an
image rebuild, and every `main`/`dev` static image must remain behind the trusted
SSO edge. Both application images bake the normalized branch and mode as the
two mode-0444 lines in `/etc/portfolio-auth-build`. Django settings compare that
file to the runtime canonical pair, and the frontend Nginx entrypoint invokes
the canonical resolver and performs the same comparison before serving files.
Overriding container environment variables cannot change or bypass the build
contract.

Django registers `/admin/` only in local mode. SSO mode returns 404 for
`/admin/login/` even through direct loopback backend access; portfolio account
administration stays centralized outside this application.

Useful checks:

```bash
scripts/portfolio-auth-mode.sh print
scripts/portfolio-auth-mode.sh check
scripts/portfolio-auth-mode.sh exec -- python backend/manage.py check
```

Production Compose environment must contain the matching assertions:

```dotenv
PORTFOLIO_BRANCH=main
PORTFOLIO_AUTH_MODE=sso
PILGRIMAGE_SSO_ENABLED=true
VITE_SSO_ENABLED=true
PILGRIMAGE_SSO_EDGE_SECRET_HOST_FILE=/absolute/private/path/pilgrimage-edge-secret
```

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

Approval immediately replaces that user's local password with an unusable
credential in the same transaction. Do not approve the account until the
central identity and edge path are ready; password login cannot be used after
this step.

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

The `main` CI run explicitly sets `PORTFOLIO_BRANCH=main`,
`PORTFOLIO_AUTH_MODE=sso`, and the legacy adapters to SSO. It uses a
non-production direct test secret and never
reads the production edge-secret file. Its 20-minute timeout plus the dependent
build/deploy job remains bounded by the workflow timeout budget.

The workflow also runs for `dev`, injecting `PORTFOLIO_BRANCH=dev` with the same
SSO contract and building both ARM64 images as validation only. A `dev` run does
not log in to GHCR, push a SHA or `latest` tag, or execute the SSH deployment;
those mutations remain restricted to `main`.

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
