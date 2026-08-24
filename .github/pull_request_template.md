## Summary

What changed and why?

## Modules

Which modules own the changed artifacts? If several modules changed, why must the work coordinate them?

## Verification

List the commands or checks run and their results.

## Checklist

- [ ] Every changed artifact has exactly one owning module
- [ ] Cross-module coordination is explained when applicable
- [ ] No secrets or environment-specific credentials are committed
- [ ] Tests cover behavior changes
- [ ] Schema changes include an owning-service Alembic migration
- [ ] Module documentation or an ADR was updated when responsibilities or architecture changed
- [ ] The change contains no unrelated refactoring