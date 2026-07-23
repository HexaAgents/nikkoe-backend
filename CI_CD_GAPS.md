# CI/CD Gap Analysis

Current audit of the Nikkoe frontend/backend delivery path.

## Canonical production

The supported production path is:

```text
platform.hexaagents.com
  -> Vercel project nikkoe-frontend
  -> https://nikkoe-backend.vercel.app/api
  -> Vercel project nikkoe-backend
```

Both projects deploy from their GitHub `main` branches through Vercel Git
integration. GitHub Actions validates changes but does not deploy to Google
Cloud.

## Already covered

- [x] Backend lint and format checks on pushes and pull requests.
- [x] Backend pytest suite with a 60% coverage floor.
- [x] Backend dependency vulnerability scanning with `pip-audit`.
- [x] Backend Docker build verification.
- [x] Migration filename and empty-file validation.
- [x] Frontend lint, type checking, tests, and production build verification.
- [x] Vercel production deployments from GitHub.
- [x] Vercel preview deployments for non-production branches.
- [x] Custom frontend domain `platform.hexaagents.com`.
- [x] Backend health endpoint.
- [x] CI concurrency controls.

## Deployment configuration checks

### Vercel environment variables

- [ ] Confirm `VITE_API_URL` on Vercel project `nikkoe-frontend` is scoped to
  Production and equals `https://nikkoe-backend.vercel.app/api`.
- [ ] Check Preview variables and branch overrides for conflicting API URLs.
- [ ] Record required backend variable names and their Production/Preview scopes
  without copying secret values into source control.

`VITE_API_URL` is embedded at frontend build time. Any value change requires a
new frontend build and verification of the resulting JavaScript.

### Duplicate frontend project

Vercel projects `nikkoe-frontend` and `nikkoe-frontend-1` both deploy the same
GitHub repository. Only `nikkoe-frontend` owns `platform.hexaagents.com`.

- [ ] Confirm `nikkoe-frontend-1` has no unique domains, variables, or consumers.
- [ ] Disable its Git integration or delete it only after separate approval.

No duplicate project cleanup is part of the current CI consolidation.

## Legacy Google Cloud infrastructure

### `nikkoe-api`

Google Cloud project `nikkoe-backend` (`492947344915`) contains Cloud Run
service `nikkoe-api` in `europe-west1`.

- It is deployed from the separate private repository
  `HexaAgents/nikkoe-api`.
- That repository has only three commits from 1 April 2026.
- Its Cloud Build history contains those commit builds plus a retry.
- Its API and CORS behavior do not match the maintained backend.
- The production frontend does not reference it.

Leave the service and Cloud Build trigger untouched until consumers, runtime
configuration, data access, and rollback requirements are audited.

### `valid-cedar-492118-d6`

The backend workflow previously targeted project `valid-cedar-492118-d6`
(`218784664685`), service `nikkoe-backend`, in `us-central1`.

- [x] Remove this stale deploy path from GitHub Actions.
- [ ] Review the project separately before any billing, IAM, or deletion action.

## Manual GitHub setup

### Branch protection

Configure both repositories' `main` branches to:

- [ ] Require a pull request before merging.
- [ ] Require at least one approval.
- [ ] Require all CI jobs to pass.
- [ ] Require branches to be up to date.
- [ ] Prevent bypass except for documented emergencies.

## Remaining test and observability gaps

### Browser-level end-to-end tests

Component interaction tests exist, but a deployed browser test should cover:

- [ ] Login and token refresh.
- [ ] Item search and item detail.
- [ ] Stock transfer.
- [ ] Create and void sale/receipt.
- [ ] Invoice parsing/streaming.
- [ ] Change password.

### Database migration CI

Migration files are structurally validated but not applied to a disposable
database.

- [ ] Apply migrations to a temporary Supabase/Postgres environment in CI.
- [ ] Test constraints, RPCs, and row-level security policies.

### Monitoring

- [ ] Configure alerts for Vercel backend 5xx rates.
- [ ] Configure uptime monitoring for `/api/health`.
- [ ] Add browser/runtime error tracking with release identifiers.
- [ ] Define a post-deployment observation window and owner.

## Rollback and recovery

### Application rollback

1. Record the current READY Vercel deployment before release.
2. If production regresses, restore the previous deployment alias using Vercel
   Instant Rollback.
3. If alias rollback is unavailable, revert the responsible Git commit and
   redeploy.
4. Repeat health, OpenAPI, CORS, bundle-target, and browser smoke tests.

Do not delete the failed deployment until the incident is understood.

### Database rollback

- [ ] Document when to use a forward-fix migration versus snapshot restore.
- [ ] Confirm Supabase backup retention and recovery access.
- [ ] Test a restore procedure in a non-production project.

## Current status

| Category | Status |
| --- | --- |
| Backend CI quality gates | In place |
| Frontend CI quality gates | In place |
| Production hosting | Vercel |
| Production backend target | `nikkoe-backend.vercel.app` |
| Preview deployments | Vercel Git integration |
| Google Cloud services | Legacy, not production |
| Branch protection | Manual verification required |
| Browser E2E | Gap |
| Migration execution in CI | Gap |
| Monitoring and alerts | Gap |
| Rollback procedure | Documented; exercise still required |
