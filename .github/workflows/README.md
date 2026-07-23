# CI Pipeline and Production Deployment — nikkoe-backend

This document describes the checks in `ci.yml`, the production deployment path,
and the legacy deployment paths that must not be treated as production.

## Canonical production topology

Production is hosted on Vercel:

```text
platform.hexaagents.com
  -> Vercel project: nikkoe-frontend
  -> VITE_API_URL=https://nikkoe-backend.vercel.app/api
  -> Vercel project: nikkoe-backend
```

Both Vercel projects are connected directly to their GitHub repositories.
Vercel builds and deploys `main` automatically; deployment is not performed by
this GitHub Actions workflow.

The effective API target must be checked in both places:

1. Vercel project `nikkoe-frontend` > Settings > Environment Variables.
2. The built production JavaScript, because Vite embeds `VITE_API_URL` at build
   time. Changing the dashboard value requires a new frontend deployment.

## Legacy Google Cloud paths

Two Google Cloud paths exist, but neither serves the production frontend:

- Project `nikkoe-backend` (`492947344915`) contains Cloud Run service
  `nikkoe-api` in `europe-west1`. It is built from the separate, dormant
  `HexaAgents/nikkoe-api` repository. Its API contract and CORS configuration do
  not match the maintained backend.
- The backend workflow previously targeted project `valid-cedar-492118-d6`
  (`218784664685`), service `nikkoe-backend`, in `us-central1`. That target is
  stale and is no longer part of this workflow.

Do not point `VITE_API_URL` at either Cloud Run service or re-enable a Cloud Run
deploy job without a separately reviewed migration plan, API/CORS parity tests,
and an explicit rollback path.

## When CI runs

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

- Pull requests to `main` run every quality gate before merge.
- Pushes to `main` run the same quality gates.
- Vercel observes the Git push independently and creates the deployment.

Concurrency groups runs by workflow and Git ref, cancelling obsolete runs when
a newer commit arrives on the same ref.

## CI jobs

All jobs run independently for faster feedback.

### `lint`

- Installs Ruff on Python 3.12.
- Runs `ruff check app/ tests/`.
- Runs `ruff format --check app/ tests/`.

### `test`

- Installs production and development requirements.
- Runs the full pytest suite with short tracebacks.
- Enforces at least 60% application coverage.

```bash
pytest --tb=short -q --cov=app --cov-report=term-missing --cov-fail-under=60
```

### `security`

- Installs `pip-audit`.
- Fails when a production dependency has a known vulnerability.

```bash
pip-audit -r requirements.txt
```

### `build`

- Builds the production Dockerfile.
- Catches missing runtime dependencies and invalid container configuration.

```bash
docker build -t nikkoe-backend:ci .
```

The image is a verification artifact only; this workflow does not publish or
deploy it.

### `migrations`

- Verifies each SQL migration starts with a date-like prefix.
- Rejects empty migration files.
- Does not apply migrations to production.

## Deployment verification

Before and after a production-affecting change:

1. Record the current READY frontend and backend Vercel deployment IDs.
2. Confirm `platform.hexaagents.com` returns HTTP 200.
3. Confirm `https://nikkoe-backend.vercel.app/api/health` returns HTTP 200.
4. Confirm the production OpenAPI contract has the expected routes.
5. Confirm CORS accepts `platform.hexaagents.com` and
   `nikkoe-frontend.vercel.app`.
6. Confirm the production bundle still embeds the intended `VITE_API_URL`.
7. Check Vercel runtime errors after deployment.

If any check regresses, restore the previous READY Vercel deployment alias or
revert the responsible Git commit, then repeat the same verification.

## Modifying CI safely

1. Run the exact commands locally before pushing.
2. Make CI-only changes on a temporary branch.
3. Review the workflow diff for deployment commands or credentials.
4. Require all PR checks to pass.
5. Verify the Vercel preview before merging.
6. Monitor the production deployment and retain the previous READY deployment
   as a rollback candidate.

## Files involved

| File | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | CI quality gates |
| `requirements.txt` | Production dependencies |
| `requirements-dev.txt` | Development and CI dependencies |
| `pyproject.toml` | Ruff and pytest configuration |
| `Dockerfile` | Production container definition and CI build target |
| `tests/` | Backend test suite |
