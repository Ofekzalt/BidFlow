# workflows/

GitHub Actions workflow definitions for pull-request validation.

## Workflows

| Workflow | Trigger paths | Checks |
| --- | --- | --- |
| [`authentication-ci.yml`](authentication-ci.yml) | `authentication/**`, shared infra | Ruff format, Ruff lint |
| [`auction-ci.yml`](auction-ci.yml) | `auction/**`, shared infra | Ruff format, Ruff lint, Alembic, e2e tests |
| [`settlement-ci.yml`](settlement-ci.yml) | `settlement/**`, shared infra | Ruff format, Ruff lint, e2e tests |
| [`reusable-python-service.yml`](reusable-python-service.yml) | Called by service workflows | Shared uv, Ruff, Docker Compose, pytest steps |

All service workflows run on pull requests to `main`. Shared paths (`docker-compose.yml`, `scripts/init-databases.sql`, `.github/workflows/**`) trigger every affected service job.

See [`../AUTOMATION.md`](../AUTOMATION.md) for ownership boundaries and delivery scope.
