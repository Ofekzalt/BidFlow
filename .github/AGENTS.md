# AGENTS.md — .github

Read [`AUTOMATION.md`](AUTOMATION.md) and root [`AGENTS.md`](../AGENTS.md) before changing repository automation.

## Agent rules

- Never embed credentials, private keys, Stripe secrets, or environment-specific tokens.
- Use least-privilege workflow permissions.
- Pin third-party actions to an intentional version.
- Keep CI deterministic and non-interactive.
- Add automation only for tooling that exists in the repository.
- Keep workflows path-aware when doing so does not skip required integration checks.
- Do not add deployment workflows.
- Backend CI should run Ruff, pytest, and service-owned Alembic migrations once those tools exist.
- Frontend CI should run tests, type checking, and build once the frontend toolchain exists.
- Update [`AUTOMATION.md`](AUTOMATION.md) when automation ownership or delivery boundaries change.
- Follow the pull request template for every change.
