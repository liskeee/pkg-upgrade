# Semantic Release and Full CI — Design

**Date:** 2026-04-12
**Status:** Approved (pending user review of written spec)
**Scope:** Automate versioning and release for `mac-upgrade`; expand CI to catch release-breaking issues before they ship.

## Goals

- A green `main` is always releasable: PyPI, GitHub Release, and Homebrew formula stay consistent.
- Conventional Commits drive automatic, reviewable version bumps.
- Pre-releases can be cut from a `dev` branch without disturbing stable users.
- Solo-maintainer friendly: minimal secrets, minimal manual steps.

## Non-Goals

- Linux support (project is macOS-only by design).
- Separate Homebrew tap repository (in-repo formula is sufficient).
- Coverage enforcement thresholds (defer until project matures).
- Release dry-run comments on PRs (defer — noisy for a solo project).

## Tooling Decisions

| Concern | Choice | Why |
|---|---|---|
| Release tool | **python-semantic-release** | Python-native, reads Conventional Commits, writes `pyproject.toml` version, tags, builds, publishes |
| Commit convention | **Conventional Commits** (angular parser) | Standard, tool-native |
| PR title lint | `wagoid/commitlint-github-action` on PR title only | Solo-use friendly; doesn't block individual commits |
| PyPI auth | **OIDC Trusted Publishing** | No long-lived tokens |
| Formula bump | **Separate `formula-bump.yml` on `release: published`**, opens PR | Reviewable; release itself stays atomic |
| Pre-releases | `dev` branch → `X.Y.Z-rc.N` on real PyPI | Native semantic-release feature; no TestPyPI juggling |

## Release Flow

```
commit to main (Conventional Commit)
         │
         ▼
    ci.yml  (lint, typecheck, test, pre-commit, build, smoke, security)
         │  all green
         ▼
    release.yml
       ├── semantic-release: compute vX.Y.Z from commits since last tag
       ├── update pyproject.toml + CHANGELOG.md; commit [skip ci]; tag; push
       ├── build sdist + wheel
       ├── create GitHub Release with changelog + artifacts
       └── publish to PyPI (OIDC)
         │
         ▼  (release: published, prerelease == false)
    formula-bump.yml
       ├── fetch tarball; compute SHA256
       ├── brew update-python-resources (refresh resource SHAs)
       └── open PR: chore(formula): bump to vX.Y.Z
         │
         ▼  (user merges)
    ci.yml `brew` job validates → installable via brew
```

Pre-release flow is identical except: triggered by push to `dev`, produces `X.Y.Z-rc.N`, GitHub Release is marked pre-release, `formula-bump.yml` is skipped.

## Workflows

### `ci.yml` (expanded)

Triggers: `push` to `main` or `dev`, `pull_request`.

Jobs (all on `macos-latest` unless noted):

- **lint** — `ruff check .` + `ruff format --check .`
- **typecheck** — `mypy`
- **test** — pytest matrix Python 3.12 / 3.13; upload `coverage.xml`
- **pre-commit** — `pre-commit run --all-files`
- **build** — `python -m build` + `twine check dist/*`; upload artifacts
- **smoke** — install built wheel into clean venv; run `mac-upgrade --version` and `--help`
- **brew** — `brew install --build-from-source ./Formula/mac-upgrade.rb` + `brew test mac-upgrade`
  - Runs on PR only when `Formula/**` changes, plus weekly cron (`schedule: cron: '0 6 * * 1'`)
- **security** — `pip-audit` against runtime + dev deps

### `release.yml`

Triggers: `push` to `main` or `dev`, gated on `ci.yml` success via `needs:` (single workflow with `ci` job as dependency) or `workflow_run` (TBD during implementation — prefer single-workflow with `needs` for simplicity).

Permissions: `contents: write`, `id-token: write`.

Steps:
1. Checkout with `fetch-depth: 0` (full history + tags).
2. Install `python-semantic-release` and `build`.
3. `semantic-release version` — determines next version per branch config, updates files, tags, commits `[skip ci]`, pushes.
4. `semantic-release publish` — uploads artifacts to GitHub Release.
5. `pypa/gh-action-pypi-publish@release/v1` — OIDC publish.

Skip conditions: commit message contains `[skip ci]`, or no releasable commits (semantic-release exits 0).

### `formula-bump.yml`

Trigger: `release: published` AND `github.event.release.prerelease == false`. Also `workflow_dispatch` for manual re-runs.

Runs on `macos-latest`.

Steps:
1. Checkout `main`.
2. Fetch release tarball URL; compute SHA256.
3. Rewrite `Formula/mac-upgrade.rb` `url` and `sha256`.
4. `brew update-python-resources Formula/mac-upgrade.rb` to refresh resource SHAs.
5. Create branch `formula-bump/vX.Y.Z`; open PR with title `chore(formula): bump to vX.Y.Z`.

### `dependabot.yml`

Weekly updates for `github-actions` and `pip` ecosystems.

## `pyproject.toml` Additions

```toml
[project.optional-dependencies]
dev = [
    # ...existing...
    "build>=1.2",
]

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
build_command = "python -m build"
commit_message = "chore(release): {version} [skip ci]"
changelog_file = "CHANGELOG.md"

[tool.semantic_release.branches.main]
match = "main"
prerelease = false

[tool.semantic_release.branches.dev]
match = "dev"
prerelease = true
prerelease_token = "rc"

[tool.semantic_release.commit_parser_options]
# angular parser defaults; documented for clarity
allowed_tags = ["feat", "fix", "perf", "refactor", "docs", "style", "test", "build", "ci", "chore"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
```

## Error Handling & Edge Cases

- **No releasable commits** (only `chore:`/`docs:`): semantic-release exits 0; release workflow no-ops.
- **Recursive release commits**: `[skip ci]` in release commit message prevents CI re-trigger.
- **PyPI publish fails after tag push**: tag + GitHub Release exist, package missing. Recovery: rerun workflow (semantic-release is idempotent on existing versions) or manual `twine upload`.
- **Formula bump PR fails** (`brew update-python-resources` can't resolve a dep): PR marked failing; fix manually. Release itself remains successful.
- **First release**: `pyproject.toml` currently at `0.1.0` with no prior tag. Option 1: create anchor tag `v0.1.0` manually before first run. Option 2: let first qualifying commit produce `0.1.1` or `0.2.0` per Conventional Commits.
- **PyPI name collision**: verify `mac-upgrade` is available on PyPI before first publish (one-time manual check).
- **`dev` → `main` merge jump**: `1.2.0-rc.3` on dev resolves to `1.2.0` on main — intended behavior.

## Files Created / Modified

**New:**
- `.github/workflows/release.yml`
- `.github/workflows/formula-bump.yml`
- `.github/dependabot.yml`
- `CHANGELOG.md` (empty seed)
- `docs/CONTRIBUTING.md` (brief Conventional Commits note)

**Modified:**
- `.github/workflows/ci.yml` — add `pre-commit`, `build`, `smoke`, `brew`, `security` jobs; add `dev` branch
- `pyproject.toml` — add `[tool.semantic_release]` config; add `build` to dev deps
- `Formula/mac-upgrade.rb` — will be rewritten by `formula-bump.yml` on first stable release

## One-Time Manual Setup

1. **PyPI Trusted Publisher**: PyPI → project → Publishing → add GitHub publisher
   - Owner: `liskeee`
   - Repo: `mac-upgrade`
   - Workflow: `release.yml`
   - Environment: `pypi`
2. **GitHub Environment `pypi`**: create in repo settings; optionally require reviewers.
3. **Verify PyPI name**: confirm `mac-upgrade` is available.
4. **Anchor tag** (optional): `git tag v0.1.0 && git push --tags` to start stable series at current version.
5. **Create `dev` branch**: `git checkout -b dev && git push -u origin dev`.
6. **Branch protection**: require `ci.yml` on `main` and `dev`.

## Testing

- CI changes are self-testing: the PR introducing these files runs the new workflow.
- `formula-bump.yml` includes `workflow_dispatch` — exercise it manually against an existing release before relying on the event trigger.

## Open Questions (resolve during implementation)

- Whether `release.yml` uses `needs: [ci]` single-workflow or `workflow_run` trigger. Prefer `needs:` for simplicity unless it forces duplicated setup.
- Whether PR-title lint is a required check or informational.
