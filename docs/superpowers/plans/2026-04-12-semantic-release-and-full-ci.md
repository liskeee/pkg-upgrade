# Semantic Release and Full CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate versioning and release (PyPI, GitHub Release, Homebrew) driven by Conventional Commits, with expanded CI that catches release-breaking issues before shipping.

**Architecture:** python-semantic-release drives version bumps on `main` (stable) and `dev` (rc pre-releases). A `release.yml` workflow publishes to PyPI via OIDC and creates GitHub Releases. A separate `formula-bump.yml` opens a PR updating the Homebrew formula on stable releases. `ci.yml` gains `pre-commit`, `build`, `smoke`, `brew`, and `security` jobs.

**Tech Stack:** Python 3.12/3.13, python-semantic-release, GitHub Actions, PyPI Trusted Publishing (OIDC), Homebrew, Dependabot.

**Spec:** `docs/superpowers/specs/2026-04-12-semantic-release-and-full-ci-design.md`

---

## File Structure

**New files:**
- `.github/workflows/release.yml` — semantic-release + PyPI publish
- `.github/workflows/formula-bump.yml` — formula-bump PR on stable release
- `.github/dependabot.yml` — weekly dep updates
- `CHANGELOG.md` — seed file, maintained by semantic-release
- `docs/CONTRIBUTING.md` — Conventional Commits guide

**Modified:**
- `pyproject.toml` — `[tool.semantic_release]` config, add `build` to dev deps
- `.github/workflows/ci.yml` — add jobs, trigger on `dev`

**Rewritten on first release (by workflow):**
- `Formula/mac-upgrade.rb`

Note: Verification for workflow files uses `actionlint` where available, plus PR-run validation. Classical unit-test TDD does not apply to YAML workflow files — each task commits a self-contained, individually reviewable change.

---

## Task 1: Add semantic-release configuration to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `build` to dev deps**

Edit `pyproject.toml`, under `[project.optional-dependencies].dev`, add `"build>=1.2",`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.11",
    "pre-commit>=3.8",
    "build>=1.2",
]
```

- [ ] **Step 2: Append semantic_release config**

Append to end of `pyproject.toml`:

```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
build_command = "python -m build"
commit_message = "chore(release): {version} [skip ci]"
changelog_file = "CHANGELOG.md"
tag_format = "v{version}"

[tool.semantic_release.branches.main]
match = "main"
prerelease = false

[tool.semantic_release.branches.dev]
match = "dev"
prerelease = true
prerelease_token = "rc"

[tool.semantic_release.commit_parser_options]
allowed_tags = ["feat", "fix", "perf", "refactor", "docs", "style", "test", "build", "ci", "chore"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
```

- [ ] **Step 3: Verify TOML parses**

Run: `python -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"`
Expected: exits 0, no output.

- [ ] **Step 4: Install and verify semantic-release sees the config**

Run: `python -m pip install python-semantic-release==9.* && semantic-release --noop version --print`
Expected: prints a version string (likely `0.1.0` or `0.1.1`) with no error. The `--noop` flag prevents any write/push.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "build: configure python-semantic-release and add build dep"
```

---

## Task 2: Seed CHANGELOG.md and CONTRIBUTING.md

**Files:**
- Create: `CHANGELOG.md`
- Create: `docs/CONTRIBUTING.md`

- [ ] **Step 1: Create empty CHANGELOG.md**

Write `CHANGELOG.md`:

```markdown
# CHANGELOG

<!-- Maintained automatically by python-semantic-release. Do not edit manually. -->
```

- [ ] **Step 2: Create CONTRIBUTING.md**

Write `docs/CONTRIBUTING.md`:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md docs/CONTRIBUTING.md
git commit -m "docs: seed changelog and contributing guide"
```

---

## Task 3: Expand ci.yml with pre-commit, build, and smoke jobs; add dev branch trigger

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Replace ci.yml**

Overwrite `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 06:00 UTC for brew job

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .

  typecheck:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: mypy

  test:
    runs-on: macos-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: pytest --cov --cov-report=xml
      - uses: actions/upload-artifact@v4
        if: matrix.python-version == '3.12'
        with:
          name: coverage-xml
          path: coverage.xml

  pre-commit:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: pre-commit run --all-files --show-diff-on-failure

  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install build twine
      - run: python -m build
      - run: python -m twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  smoke:
    runs-on: macos-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Install built wheel in clean venv
        run: |
          python -m venv .smoke
          .smoke/bin/pip install dist/*.whl
          .smoke/bin/mac-upgrade --version
          .smoke/bin/mac-upgrade --help

  security:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install pip-audit
      - run: pip-audit --strict --progress-spinner=off .

  brew:
    runs-on: macos-latest
    if: |
      github.event_name == 'schedule' ||
      (github.event_name == 'pull_request' && contains(toJSON(github.event.pull_request.labels.*.name), 'formula')) ||
      github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - name: Install formula from source
        run: brew install --build-from-source ./Formula/mac-upgrade.rb
      - name: Test formula
        run: brew test mac-upgrade
```

Notes on the `brew` job trigger:
- On `schedule` — weekly.
- On `pull_request` — only when the PR has a `formula` label (keeps regular PRs fast). Path-based trigger is deliberately not used because GitHub Actions can't skip a required check by path without making the check non-required.
- On `push` — runs on `main`/`dev` pushes so formula issues surface immediately after merge.

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: exits 0.

- [ ] **Step 3: Optional actionlint**

Run (if installed): `actionlint .github/workflows/ci.yml`
Expected: no errors. If actionlint is not installed, skip — CI itself will validate on push.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add pre-commit, build, smoke, security, and brew jobs"
```

---

## Task 4: Add Dependabot config

**Files:**
- Create: `.github/dependabot.yml`

- [ ] **Step 1: Create dependabot.yml**

Write `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
    commit-message:
      prefix: "ci"
      include: "scope"

  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    commit-message:
      prefix: "build"
      include: "scope"
```

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add .github/dependabot.yml
git commit -m "ci: enable Dependabot for actions and pip"
```

---

## Task 5: Add release.yml

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release.yml**

Write `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    branches: [main, dev]

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: macos-latest
    # Skip the automated release commit to avoid loops
    if: "!contains(github.event.head_commit.message, '[skip ci]')"
    permissions:
      contents: write
      id-token: write
    environment:
      name: pypi
      url: https://pypi.org/project/mac-upgrade/
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install release tooling
        run: python -m pip install "python-semantic-release==9.*" build

      - name: Run semantic-release
        id: release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          semantic-release version
          echo "released=$(semantic-release --noop version --print | grep -q "$(git describe --tags --abbrev=0 2>/dev/null || echo none)" && echo true || echo false)" >> "$GITHUB_OUTPUT"

      - name: Publish GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: semantic-release publish

      - name: Publish to PyPI
        if: hashFiles('dist/*') != ''
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist
```

Notes:
- `environment: pypi` is required for OIDC Trusted Publishing (see manual setup in spec).
- `concurrency.cancel-in-progress: false` — never interrupt a release mid-publish.
- The `semantic-release version` step is a no-op when no releasable commits exist; the subsequent steps still run but find nothing to publish (guarded by `hashFiles('dist/*') != ''`).

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow with semantic-release and PyPI OIDC publish"
```

---

## Task 6: Add formula-bump.yml

**Files:**
- Create: `.github/workflows/formula-bump.yml`

- [ ] **Step 1: Create formula-bump.yml**

Write `.github/workflows/formula-bump.yml`:

```yaml
name: Bump Homebrew Formula

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      tag:
        description: "Release tag to bump formula to (e.g. v1.2.0)"
        required: true

permissions:
  contents: write
  pull-requests: write

jobs:
  bump:
    # Skip pre-releases on the automatic trigger; workflow_dispatch always runs
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.release.prerelease == false }}
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Resolve tag
        id: tag
        run: |
          TAG="${{ github.event.inputs.tag || github.event.release.tag_name }}"
          VERSION="${TAG#v}"
          echo "tag=$TAG" >> "$GITHUB_OUTPUT"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Compute release tarball SHA256
        id: sha
        run: |
          URL="https://github.com/${{ github.repository }}/archive/refs/tags/${{ steps.tag.outputs.tag }}.tar.gz"
          curl -fsSL "$URL" -o release.tar.gz
          SHA=$(shasum -a 256 release.tar.gz | awk '{print $1}')
          echo "sha=$SHA" >> "$GITHUB_OUTPUT"
          echo "url=$URL" >> "$GITHUB_OUTPUT"

      - name: Update url, sha256, and resources in formula
        run: |
          python3 <<'PY'
          import re, pathlib, os
          p = pathlib.Path("Formula/mac-upgrade.rb")
          s = p.read_text()
          url = os.environ["URL"]
          sha = os.environ["SHA"]
          s = re.sub(r'url "https://github\.com/[^"]+"', f'url "{url}"', s, count=1)
          s = re.sub(r'sha256 "[^"]+"', f'sha256 "{sha}"', s, count=1)
          p.write_text(s)
          PY
        env:
          URL: ${{ steps.sha.outputs.url }}
          SHA: ${{ steps.sha.outputs.sha }}

      - name: Refresh Python resources
        run: |
          brew update-python-resources Formula/mac-upgrade.rb || true

      - name: Open pull request
        uses: peter-evans/create-pull-request@v7
        with:
          branch: formula-bump/${{ steps.tag.outputs.tag }}
          commit-message: "chore(formula): bump to ${{ steps.tag.outputs.tag }}"
          title: "chore(formula): bump to ${{ steps.tag.outputs.tag }}"
          body: |
            Automated formula bump for ${{ steps.tag.outputs.tag }}.

            - Updated `url` and `sha256`
            - Ran `brew update-python-resources`

            Merging will trigger the `brew` CI job which validates `brew install --build-from-source` and `brew test`.
          labels: formula
          base: main
```

Notes:
- The `formula` label added by the PR ensures the `brew` CI job runs on this PR (ci.yml Task 3 `brew` condition).
- `brew update-python-resources` is best-effort; if it fails, the PR still opens with the tarball changes and can be finished manually.

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/formula-bump.yml'))"`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/formula-bump.yml
git commit -m "ci: add formula bump workflow on stable releases"
```

---

## Task 7: Document manual setup steps

**Files:**
- Modify: `docs/CONTRIBUTING.md`

- [ ] **Step 1: Append "Release setup" section**

Append to `docs/CONTRIBUTING.md`:

```markdown

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
```

- [ ] **Step 2: Commit**

```bash
git add docs/CONTRIBUTING.md
git commit -m "docs: document release setup and flow"
```

---

## Task 8: End-to-end validation on a throwaway PR

**Files:** none (operational).

- [ ] **Step 1: Push branch and open PR**

Push the feature branch (if not already) and open a PR against `main`. Confirm all CI jobs run and pass except `brew` (no `formula` label on this PR — expected skip) and `release` (only runs on push to `main`/`dev`).

- [ ] **Step 2: Confirm workflow syntax via GitHub**

In the PR's Actions tab, ensure each workflow file was parsed without syntax errors (no "workflow is invalid" annotations).

- [ ] **Step 3: After merge to main**

- Verify `release.yml` runs on `main` push.
- If the head commit qualifies (`feat:` / `fix:`), verify a new tag is created, a GitHub Release is published, and PyPI receives the package.
- Verify `formula-bump.yml` opens a PR titled `chore(formula): bump to vX.Y.Z`.

- [ ] **Step 4: Merge the formula-bump PR**

Add the `formula` label if the bot didn't. Confirm the `brew` CI job runs and passes. Merge.

---

## Self-Review Notes

- **Spec coverage**: all spec sections mapped to tasks — semantic-release config (T1), conventional commits docs (T2), ci.yml jobs (T3), dependabot (T4), release workflow (T5), formula-bump workflow (T6), manual setup docs (T7), validation (T8). Pre-release `dev` branch behavior is implicit in T1 (branch config) and T5 (trigger). ✓
- **Placeholders**: none. All config snippets complete. ✓
- **Consistency**: tag format `v{version}` used in T1 and referenced in T6; workflow names match across files. ✓
- **Open spec questions**: spec flagged `needs:` vs `workflow_run` — plan resolves to trigger-based (release.yml runs on push, same triggers as ci.yml; GitHub merges branch protection rules to prevent release without green CI). Spec flagged PR-title lint — deferred (not in any task) as it is explicitly optional in the spec and adds friction for a solo project.
