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

## Release setup (maintainer, one-time)

1. **PyPI Trusted Publisher**: on PyPI, under the project → Publishing → add a GitHub publisher:
   - Owner: `liskeee`
   - Repository: `mac-upgrade`
   - Workflow: `release.yml`
   - Environment: `pypi`
2. **GitHub Environment `pypi`**: create in repo Settings → Environments. Optionally require a reviewer.
3. **Verify PyPI name availability**: https://pypi.org/project/mac-upgrade/ — must be unclaimed before first publish.
4. **Anchor tag (optional)**: `git tag v0.1.0 && git push --tags` to start the stable series at the current version.
5. **Create `dev` branch**: `git checkout -b dev && git push -u origin dev`.
6. **Branch protection**: require `ci.yml` jobs on both `main` and `dev`.

## Release flow

- Merge Conventional Commits to `dev` → automated pre-release `X.Y.Z-rc.N` on PyPI and GitHub.
- Merge `dev` → `main` → automated stable `X.Y.Z`; a PR opens to bump `Formula/mac-upgrade.rb`. Merge it to finalize Homebrew support.
