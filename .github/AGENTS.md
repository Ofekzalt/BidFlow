# AGENTS.md — .github

Read [`AUTOMATION.md`](AUTOMATION.md) and root [`AGENTS.md`](../AGENTS.md) before changing repository automation.

## Agent rules

- Never embed credentials, private keys, Stripe secrets, or environment-specific tokens.
- Use least-privilege workflow permissions.
- Pin third-party actions to an intentional version.
- Keep CI deterministic and non-interactive.
- Add automation only for tooling that exists in the repository.
- Keep workflows path-aware when doing so does not skip required e2e checks.
- Do not add deployment workflows.
- Backend CI should run Ruff, e2e tests against owned PostgreSQL (service port until Kong exists, then through Kong), and service-owned Alembic migrations once those tools exist.
- Frontend CI should run type checking and build once the frontend toolchain exists; add browser e2e jobs when the UI exists.
- Update [`AUTOMATION.md`](AUTOMATION.md) when automation ownership or delivery boundaries change.
- Follow the pull request template for every change.
