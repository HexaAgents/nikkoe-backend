# CI/CD Gap Analysis

Audit of both `nikkoe-backend` and `nikkoe-frontend` against the full CI/CD checklist. Items are grouped by what's already done, what was just fixed in CI files, and what still requires manual setup.

---

## Already Covered

- [x] Every code change triggers automated CI (both repos)
- [x] Lint and format checks on every PR
- [x] Frontend type checking (`tsc --noEmit`)
- [x] Frontend build verification (`npm run build`)
- [x] Backend unit tests (pytest, mocked dependencies)
- [x] Frontend unit tests (vitest) + integration tests on push
- [x] Dependency vulnerability scanning (pip-audit / npm audit)
- [x] OIDC-based deploy auth (short-lived credentials, no static keys)
- [x] Concurrency controls cancel stale CI runs
- [x] Secrets stored in GitHub, not in code
- [x] Migrations are version-controlled (`supabase/migrations/`)

---

## Fixed in CI Pipeline

These were addressed in the updated `.github/workflows/ci.yml`:

- [x] Backend split into parallel jobs (lint, test, security, build, migrations)
- [x] Lint and format scope expanded to include `tests/` directory
- [x] Docker build verified in CI (catches missing deps, bad Dockerfile)
- [x] Migration files validated (naming convention + non-empty check)
- [x] Deploy gated behind `environment: production` (supports approval rules)
- [x] Post-deploy health check verifies the app is alive after deploy
- [x] Deploy requires all CI jobs to pass (`needs: [lint, test, security, build, migrations]`)

---

## Requires Manual GitHub Setup

These items cannot be configured via CI files. They must be set in the GitHub web UI.

### Branch protection rules

**Where:** GitHub > Repository Settings > Branches > Add rule for `main`

- [ ] Require pull request before merging
- [ ] Require at least 1 approval
- [ ] Require status checks to pass before merging (select: `lint`, `test`, `security`, `build`, `migrations`)
- [ ] Require branches to be up to date before merging
- [ ] Do not allow bypassing the above settings

Do this for both `nikkoe-backend` and `nikkoe-frontend`.

### Create `production` environment

**Where:** GitHub > Repository Settings > Environments > New environment

- [ ] Create environment named `production` in `nikkoe-backend`
- [ ] Optionally add required reviewers (for deploy approval gate)
- [ ] Optionally restrict to `main` branch only

Without this environment created, the deploy job will still run but without the approval gate.

---

## Requires Infrastructure / Tooling Setup

These require work beyond CI configuration files.

### Preview environments (per PR)

**Effort:** Medium | **Impact:** High

Enables reviewers to test real workflows before merge. Options:

- **Cloud Run revisions per PR:** Deploy a tagged revision on PR open, tear down on close. Requires a new workflow job + service account permissions.
- **Vercel (frontend):** If the frontend moves to Vercel, preview deploys are automatic per PR.

Action items:
- [ ] Decide on preview environment strategy
- [ ] Implement PR-triggered preview deploy workflow
- [ ] Add preview URL as a PR comment

### E2E tests

**Effort:** High | **Impact:** High

No end-to-end tests exist in either repo. Critical flows to cover:

- [ ] User login
- [ ] Create a sale (with line items)
- [ ] Create a receipt
- [ ] Data appears correctly in UI
- [ ] Void a sale/receipt
- [ ] Permissions enforced (no cross-company access)

Recommended tool: **Playwright** (fast, reliable, good CI support). This is a separate project-level effort.

### Database CI (migrations against test DB)

**Effort:** Medium | **Impact:** Medium

Currently, migrations are only validated for file naming/emptiness. To actually test them:

- [ ] Option A: Use `supabase start` in CI to spin up a local Supabase instance, apply migrations, run integration tests
- [ ] Option B: Use a disposable PostgreSQL container in CI, apply raw SQL migrations
- [ ] Test constraints (e.g. no invalid sales data, foreign keys enforced)
- [ ] Test RLS policies if applicable

### Post-deploy monitoring and alerting

**Effort:** Medium | **Impact:** High

- [ ] Set up error tracking (e.g. Sentry) for both frontend and backend
- [ ] Configure alerts for deploy failures (GitHub Actions > Notifications, or Slack webhook)
- [ ] Set up Cloud Run monitoring dashboards (latency, error rate, instance count)
- [ ] Configure uptime monitoring for `/api/health`

### Frontend deployment

**Effort:** Low-Medium | **Impact:** High

The frontend repo has no deploy step. Options:

- [ ] **Vercel:** Connect repo, get automatic deploys + preview environments for free
- [ ] **Cloud Run / Cloud Storage:** Add a deploy job similar to the backend
- [ ] **GitHub Pages:** If the app is a static SPA with no SSR

### Scheduled / background CI tasks

**Effort:** Low | **Impact:** Medium

Add a separate workflow triggered on a schedule:

- [ ] Weekly dependency vulnerability scan (catches new CVEs between PRs)
- [ ] Weekly `pip-audit` / `npm audit` against latest advisories
- [ ] Optional: Dependabot or Renovate for automated dependency update PRs

Example workflow trigger:
```yaml
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am UTC
```

---

## Rollback & Recovery

These are operational procedures, not CI file changes.

### Cloud Run rollback

If a bad deploy reaches production, roll back to the previous revision:

```bash
# List revisions
gcloud run revisions list --service nikkoe-backend --region us-central1

# Route 100% traffic to a known-good revision
gcloud run services update-traffic nikkoe-backend \
  --region us-central1 \
  --to-revisions GOOD_REVISION=100
```

### Database rollback

- [ ] Document forward-fix strategy (new migration to undo changes) vs snapshot restore
- [ ] Ensure Supabase daily backups are enabled (check Supabase dashboard > Settings > Database)
- [ ] Test restore process at least once

---

## Checklist Summary

| Category | Status |
|----------|--------|
| Core CI (lint, test, build, security) | Done |
| Parallel jobs with granular feedback | Done |
| Docker build verification | Done |
| Migration validation | Done |
| Deploy gating (environment protection) | Done (needs GitHub env created) |
| Post-deploy health check | Done |
| Branch protection rules | Manual setup needed |
| Preview environments | Infrastructure needed |
| E2E tests | New project effort |
| Database CI (test migrations) | Infrastructure needed |
| Monitoring and alerting | Tooling needed |
| Frontend deployment | Decision needed |
| Scheduled scans | Low-effort addition |
| Rollback procedures | Documented above |
