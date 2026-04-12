# Contributing

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) to drive automated releases.

Format: `<type>(<optional scope>): <subject>`

Types that trigger releases:
- `feat:` — minor version bump (new feature)
- `fix:` / `perf:` — patch version bump (bug fix / perf improvement)
- `feat!:` or `BREAKING CHANGE:` in body — major version bump

Types that do NOT trigger a release:
- `docs:`, `style:`, `test:`, `build:`, `ci:`, `chore:`, `refactor:`

## Branches

- `main` — stable releases (e.g. `1.2.0`)
- `dev` — pre-releases (e.g. `1.2.0-rc.1`); merges to `main` to promote

## Local checks

```bash
pre-commit run --all-files
pytest
mypy
```
