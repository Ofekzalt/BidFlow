# AGENTS.md — docs

Read root [`AGENTS.md`](../AGENTS.md) before changing documentation.

## Agent rules

- Preserve approved requirements as the authoritative product scope.
- Preserve the accepted execution sequence until implementation evidence requires an update.
- Never rewrite history in an accepted ADR; supersede it with a new ADR.
- State whether a capability is planned, partially implemented, or verified.
- Keep event names, state names, route policies, and ownership consistent across documents.
- Do not introduce architecture through documentation alone.
- Link to source files and tests once they exist instead of duplicating implementation details.
- Update module documentation when responsibilities actually change.
- Keep failure scenarios and verification commands reproducible.

## ADR naming

Use `NNNN-short-kebab-case-title.md`, sequentially numbered. Include `Status`, `Context`, `Decision`, `Alternatives`, and `Consequences`.
