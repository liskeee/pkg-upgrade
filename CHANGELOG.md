# CHANGELOG


## v1.3.1 (2026-04-13)

### Bug Fixes

- **cli**: Run onboarding wizard in worker for push_screen_wait
  ([#22](https://github.com/liskeee/pkg-upgrade/pull/22),
  [`ca0dde5`](https://github.com/liskeee/pkg-upgrade/commit/ca0dde5c0b336ec5796d26934aa8c5042c3b0789))


## v1.3.0 (2026-04-13)

### Features

- Shell completion for bash/zsh/fish/powershell
  ([#21](https://github.com/liskeee/pkg-upgrade/pull/21),
  [`9ec598b`](https://github.com/liskeee/pkg-upgrade/commit/9ec598ba8e66b08ccbc7fb8e488e0a5b4d73b9a0))

* docs: shell completion design spec

* docs: shell completion implementation plan

* feat(cli): --list --plain emits manager keys with cache write-through

* feat(cli): add 'completion <shell>' subcommand with packaged scripts

* build: drop redundant force-include; packages already ships completions

* feat(completion): bash script with flag + manager + comma list support

* feat(completion): zsh compdef with flag descriptions and comma list support

* feat(completion): fish script

Replace fish stub with working completion: flag descriptions, manager completion via XDG cache with
  built-in fallback, subcommand handling for `completion`, and pkgup alias wrapper. Append fish
  syntax-check and manager-completion tests to the shell harness.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

* feat(completion): powershell Register-ArgumentCompleter script

Replace the PowerShell stub with a full argument completer supporting flags, --only/--skip
  comma-separated manager values (backed by the shared managers.list cache), and the `completion`
  subcommand shells. Registered for both `pkg-upgrade` and `pkgup`.

Restructure tests/test_completion_shells.py: drop the module-level Windows skip so PowerShell tests
  run everywhere pwsh is available, and apply a per-test @posix_only decorator to the bash/zsh/fish
  harness tests. Add static and pwsh-parse tests for the ps1 script.

* feat(formula): install bash/zsh/fish completions

* feat(install): scoop + install.ps1 source completion from $PROFILE

Add post_install/uninstaller hooks to the Scoop manifest and a completion-sourcing block to
  install.ps1. Both paths idempotently append a dot-source line for pkg-upgrade.ps1 to $PROFILE,
  using Select-String to avoid dupes, and the uninstaller strips the line back out. Adds a static
  assertion test to lock the shape of both files.

* feat(install.sh): drop shell completion for bash/zsh/fish

* docs: shell completion install guide

* ci: matrix job for bash/zsh/fish completion tests

---------

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>


## v1.2.2 (2026-04-13)

### Bug Fixes

- **release**: Rebase on latest main before semantic-release push
  ([#19](https://github.com/liskeee/pkg-upgrade/pull/19),
  [`ac3e1dd`](https://github.com/liskeee/pkg-upgrade/commit/ac3e1dd6e689a2cbe0e19cd242be1dee661ceea4))

Release runs checked out a stale main and failed pushing back when another commit landed mid-run.
  Rebase on origin/main before running semantic-release so the push is fast-forward. Also stop
  tracking stray wheels at the repo root.


## v1.2.1 (2026-04-13)

### Bug Fixes

- **self-update**: Don't resolve symlinks so pipx venv Python is detected
  ([#18](https://github.com/liskeee/pkg-upgrade/pull/18),
  [`9a92707`](https://github.com/liskeee/pkg-upgrade/commit/9a92707b8743930e70f3512d4dd85d5cc6238688))

Path(sys.executable).resolve() follows the pipx venv's python symlink out to the underlying system
  interpreter, which breaks the 'pipx/venvs/pkg-upgrade' path signature match and falls through to
  the generic 'pip' upgrade command.

### Chores

- **scoop**: Bump to v1.2.0 ([#17](https://github.com/liskeee/pkg-upgrade/pull/17),
  [`8428b3d`](https://github.com/liskeee/pkg-upgrade/commit/8428b3d0bda16b8d535da2fbe4cfeb9ec3bde475))

Co-authored-by: liskeee <2394154+liskeee@users.noreply.github.com>

### Continuous Integration

- **scoop-bump**: Move secret check from if: to runtime env guard
  ([`58073d7`](https://github.com/liskeee/pkg-upgrade/commit/58073d7a837ab49b51c7248acd8af6d51f876718))


## v1.2.0 (2026-04-13)

### Features

- Distribution & release automation (Plan 3) ([#16](https://github.com/liskeee/pkg-upgrade/pull/16),
  [`9175153`](https://github.com/liskeee/pkg-upgrade/commit/9175153f72d76b107dfd3719cb3b2a947d5e200d))

* docs: add Plan 3 (distribution & release automation)

* ci(release): fix PyPI URL to pkg-upgrade and attach wheel to GH release

* ci(formula-bump): target Formula/pkg-upgrade.rb

* feat(scoop): add manifest template for pkg-upgrade

* ci(scoop): auto-bump manifest and mirror into scoop-bucket

* feat(install.sh): rename env vars to PKG_UPGRADE_* and support Linux

* feat(install.ps1): add Windows installer with pipx + venv fallback

* ci(installers): parse install.sh and install.ps1 on all OSes

* test: guard scoop manifest schema + installer env var names

* docs(readme): add Windows install instructions (install.ps1 + scoop)


## v1.1.0 (2026-04-13)

### Features

- Pkg-upgrade managers + tri-OS CI (Plan 2) ([#15](https://github.com/liskeee/pkg-upgrade/pull/15),
  [`ff79010`](https://github.com/liskeee/pkg-upgrade/commit/ff790101e0a17a44c6e0d2c86b45dea786b23c48))

* docs: add Plan 2 (new managers + tri-OS CI) for pkg-upgrade

* feat(parsers): add apt_upgradable preset

* feat(parsers): add dnf_check_update preset

* feat(parsers): add pacman_qu preset

* feat(parsers): add flatpak_remote_ls_updates preset

* feat(parsers): add snap_refresh_list preset

* feat(parsers): add winget_upgrade preset

* feat(parsers): add scoop_status preset

* feat(parsers): add choco_outdated preset

* feat(parsers): add mas_outdated preset

* feat(declarative): gate is_available by sudo credential and Windows admin

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

* feat(managers): ship apt/dnf/pacman/flatpak/snap/winget/scoop/choco/mas manifests

* ci: fan lint/typecheck/test across ubuntu/macos/windows matrix

* ci: matrix smoke job across ubuntu/macos/windows with expanded CLI checks

* test: guard OS-specific manager discovery against regressions

* style: ruff format test_cross_os_discovery

* fix: cross-OS test + YAML/fixture UTF-8 reads, Windows admin type-ignore

* test: make default executor groups test OS-agnostic

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.0 (2026-04-13)

### Features

- Pkg-upgrade cross-platform foundation (Plan 1)
  ([#14](https://github.com/liskeee/pkg-upgrade/pull/14),
  [`3d4f609`](https://github.com/liskeee/pkg-upgrade/commit/3d4f609c45f6909fbe497516e1955c511cb85930))

* docs: add cross-platform (pkg-upgrade) design spec

Captures approved design for renaming mac-upgrade to pkg-upgrade with full Linux/Windows parity,
  declarative YAML manager manifests, entry-point plugins, and topo-sorted scheduling via
  depends_on.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

* docs: add Plan 1 (foundation) for pkg-upgrade cross-platform work

10-task TDD plan covering rename, extended PackageManager ABC, 3-path registry, DeclarativeManager +
  YAML loader, parser preset framework, topo-sort scheduler, platform detection, platformdirs
  config, and CLI grouping/--show-graph/--max-parallel.

* refactor!: rename mac_upgrade to pkg_upgrade

BREAKING CHANGE: package, CLI command, and PyPI name change from mac-upgrade to pkg-upgrade. Adds
  pkgup short alias.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

* feat: add platform detection helper

* feat: extend PackageManager ABC with platforms/depends_on/install_hint

* feat: add manager registry with decorator + entry-point discovery

Three registration paths funnel through a single registry: - @register_manager decorator on built-in
  classes - importlib.metadata entry_points under group "pkg_upgrade.managers" - YAML manifests
  (stub loader; real impl in Task 6)

Platform gating (platforms vs current_os) happens in the registry. Replaces hardcoded ALL_MANAGERS /
  get_managers with discover_managers() and select_managers(). All call sites in app.py,
  executor.py, onboarding.py updated.

* feat: add parser preset framework with generic_regex fallback

* feat: add DeclarativeManager and YAML manifest loader

Implements Task 6: replaces the declarative.py stub with a full DeclarativeManager class + YAML
  loader, adds env support to run_command, and includes a TDD test suite covering load, parse,
  upgrade, availability, and validation.

* feat: topologically schedule managers by depends_on

Replace hardcoded SEQUENTIAL_CHAIN/INDEPENDENT constants with a Kahn's-algorithm topo sort in
  Executor.from_managers; each level becomes a parallel ExecutionGroup, dependency cycles raise
  ConfigurationError, and missing deps are silently dropped.

* feat: move config to platformdirs and add new keys

Add Config dataclass with disabled_managers, per_manager, and max_parallel fields loaded from YAML
  via platformdirs. Rename legacy JSON loader to load_config_dict to preserve backward compat;
  update cli.py accordingly.

* feat: CLI --list grouping, --show-graph, --max-parallel

* feat: add --self-update with auto-detected install method

Detects pipx/brew/scoop/install_sh/install_ps1/editable/pip install paths from sys.executable and
  delegates upgrade to the right tool.

* chore: rename remaining mac-upgrade UI strings to pkg-upgrade

- argparse prog, --version, log filename - TUI title and header; MacUpgradeApp -> PkgUpgradeApp -
  onboarding welcome message - CLAUDE.md project blurb refreshed for cross-platform + registry

* ci: update pre-commit mypy deps and smoke binary for pkg-upgrade rename

- Add types-PyYAML and platformdirs to pre-commit mypy additional_dependencies - Switch smoke job
  from mac-upgrade to pkg-upgrade binary

---------

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>

### Breaking Changes

- Package, CLI command, and PyPI name change from mac-upgrade to pkg-upgrade. Adds pkgup short
  alias.


## v0.1.1 (2026-04-12)

### Build System

- **deps**: Update textual requirement from >=3.0.0 to >=8.2.3
  ([#10](https://github.com/liskeee/pkg-upgrade/pull/10),
  [`47bd6de`](https://github.com/liskeee/pkg-upgrade/commit/47bd6de5e5e53fe646831a155afa6b4e2a23848c))

Updates the requirements on [textual](https://github.com/Textualize/textual) to permit the latest
  version. - [Release notes](https://github.com/Textualize/textual/releases) -
  [Changelog](https://github.com/Textualize/textual/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/Textualize/textual/compare/v3.0.0...v8.2.3)

--- updated-dependencies: - dependency-name: textual dependency-version: 8.2.3

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update mypy requirement from >=1.11 to >=1.20.0
  ([#11](https://github.com/liskeee/pkg-upgrade/pull/11),
  [`00bdc65`](https://github.com/liskeee/pkg-upgrade/commit/00bdc65378858c5e14b5a3370a53f330d5e6cfa2))

Updates the requirements on [mypy](https://github.com/python/mypy) to permit the latest version. -
  [Changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/python/mypy/compare/v1.11...v1.20.0)

--- updated-dependencies: - dependency-name: mypy dependency-version: 1.20.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest-asyncio requirement
  ([#7](https://github.com/liskeee/pkg-upgrade/pull/7),
  [`e82d166`](https://github.com/liskeee/pkg-upgrade/commit/e82d166ea44fb8b7339ce4b620f17479f36821c8))

Updates the requirements on [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) to permit
  the latest version. - [Release notes](https://github.com/pytest-dev/pytest-asyncio/releases) -
  [Commits](https://github.com/pytest-dev/pytest-asyncio/compare/v0.25.0...v1.3.0)

--- updated-dependencies: - dependency-name: pytest-asyncio dependency-version: 1.3.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest-cov requirement from >=5.0 to >=7.1.0
  ([#8](https://github.com/liskeee/pkg-upgrade/pull/8),
  [`f2eb04f`](https://github.com/liskeee/pkg-upgrade/commit/f2eb04fdbaffd5b4473676f0035f0c9cb54c71c2))

Updates the requirements on [pytest-cov](https://github.com/pytest-dev/pytest-cov) to permit the
  latest version. - [Changelog](https://github.com/pytest-dev/pytest-cov/blob/master/CHANGELOG.rst)
  - [Commits](https://github.com/pytest-dev/pytest-cov/compare/v5.0.0...v7.1.0)

--- updated-dependencies: - dependency-name: pytest-cov dependency-version: 7.1.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update ruff requirement from >=0.6 to >=0.15.10
  ([#9](https://github.com/liskeee/pkg-upgrade/pull/9),
  [`f627928`](https://github.com/liskeee/pkg-upgrade/commit/f62792893b451d8498bed1f87f5fc3b115235154))

Updates the requirements on [ruff](https://github.com/astral-sh/ruff) to permit the latest version.
  - [Release notes](https://github.com/astral-sh/ruff/releases) -
  [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/astral-sh/ruff/compare/0.6.0...0.15.10)

--- updated-dependencies: - dependency-name: ruff dependency-version: 0.15.10

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Continuous Integration

- Fix brew job with ephemeral tap; allow manual release trigger
  ([#13](https://github.com/liskeee/pkg-upgrade/pull/13),
  [`be97220`](https://github.com/liskeee/pkg-upgrade/commit/be972202cf4ca38d801dc2bc678e75ca66370409))

- brew: install via ephemeral local tap (homebrew rejects raw file paths); skip when formula has
  REPLACE_WITH_* placeholders - release: add workflow_dispatch with 'force' input (forces patch bump
  when no releasable commits exist)

- Run release job on ubuntu-latest
  ([`0c317fe`](https://github.com/liskeee/pkg-upgrade/commit/0c317fee58dca2159e4150d7a83e050e2afcb384))

pypa/gh-action-pypi-publish only supports Linux runners.

- **deps**: Bump actions/checkout from 4 to 6 ([#2](https://github.com/liskeee/pkg-upgrade/pull/2),
  [`b2fbecc`](https://github.com/liskeee/pkg-upgrade/commit/b2fbeccf32867c34ed1a765344d0628dfb73ebf4))

Bumps [actions/checkout](https://github.com/actions/checkout) from 4 to 6. - [Release
  notes](https://github.com/actions/checkout/releases) -
  [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/actions/checkout/compare/v4...v6)

--- updated-dependencies: - dependency-name: actions/checkout dependency-version: '6'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump actions/download-artifact from 4 to 8
  ([#5](https://github.com/liskeee/pkg-upgrade/pull/5),
  [`71efa95`](https://github.com/liskeee/pkg-upgrade/commit/71efa95d4a20be06a03ca9938b5285384d0b0a72))

Bumps [actions/download-artifact](https://github.com/actions/download-artifact) from 4 to 8. -
  [Release notes](https://github.com/actions/download-artifact/releases) -
  [Commits](https://github.com/actions/download-artifact/compare/v4...v8)

--- updated-dependencies: - dependency-name: actions/download-artifact dependency-version: '8'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump actions/setup-python from 5 to 6
  ([#4](https://github.com/liskeee/pkg-upgrade/pull/4),
  [`091b135`](https://github.com/liskeee/pkg-upgrade/commit/091b135bf73c4a0977275cab01cb86f2e61b0354))

Bumps [actions/setup-python](https://github.com/actions/setup-python) from 5 to 6. - [Release
  notes](https://github.com/actions/setup-python/releases) -
  [Commits](https://github.com/actions/setup-python/compare/v5...v6)

--- updated-dependencies: - dependency-name: actions/setup-python dependency-version: '6'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump actions/upload-artifact from 4 to 7
  ([#6](https://github.com/liskeee/pkg-upgrade/pull/6),
  [`e8c63be`](https://github.com/liskeee/pkg-upgrade/commit/e8c63be33fc87c2743624155992bc2da319c4445))

Bumps [actions/upload-artifact](https://github.com/actions/upload-artifact) from 4 to 7. - [Release
  notes](https://github.com/actions/upload-artifact/releases) -
  [Commits](https://github.com/actions/upload-artifact/compare/v4...v7)

--- updated-dependencies: - dependency-name: actions/upload-artifact dependency-version: '7'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump peter-evans/create-pull-request from 7 to 8
  ([#3](https://github.com/liskeee/pkg-upgrade/pull/3),
  [`6d500e5`](https://github.com/liskeee/pkg-upgrade/commit/6d500e5673a7b8dd30a87ac6245a928e02305b75))

Bumps [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) from 7
  to 8. - [Release notes](https://github.com/peter-evans/create-pull-request/releases) -
  [Commits](https://github.com/peter-evans/create-pull-request/compare/v7...v8)

--- updated-dependencies: - dependency-name: peter-evans/create-pull-request dependency-version: '8'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>


## v0.1.0 (2026-04-12)

### Bug Fixes

- Address code review findings + add brew install support
  ([`3564f31`](https://github.com/liskeee/pkg-upgrade/commit/3564f31a31f2520b24e2c2d8cd229e827cace54b))

- Fix CaskManager.current_version: use installed_versions[0] (was returning list) - Share `brew
  outdated --json=v2` between brew and cask via _brew_cache - Surface check_outdated errors via
  ManagerState.error / "error" status instead of silently swallowing non-zero exits - Escape
  backslashes in AppleScript notification strings - Add README.md and Homebrew formula skeleton
  (Formula/mac-upgrade.rb) so the project can be installed via `brew tap` + `brew install` - Update
  pyproject.toml with URLs/license/readme metadata

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Build System

- Configure python-semantic-release and add build dep
  ([`80f653c`](https://github.com/liskeee/pkg-upgrade/commit/80f653c8a5d1ec11c079e469b95f4ecc5d6c73f6))

### Chores

- Fix missing trailing newline in plan doc
  ([`4416adf`](https://github.com/liskeee/pkg-upgrade/commit/4416adf08fdea09a4745a5494720775d943bdedf))

Pre-commit end-of-file-fixer flagged this. Single-byte fix to keep pre-commit green in CI.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Code Style

- Apply ruff autofixes and format pass
  ([`dba5e86`](https://github.com/liskeee/pkg-upgrade/commit/dba5e86086ed52f7aa83fa165562b6da80f2c9ff))

Run ruff --fix and ruff format across src/ and tests/. Mostly import sorting, trailing commas, and
  quote style normalization.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Continuous Integration

- Add formula bump workflow on stable releases
  ([`a4e9de2`](https://github.com/liskeee/pkg-upgrade/commit/a4e9de2e9f12e3fe3e8e25e08cab214b840f1a6f))

- Add pre-commit, build, smoke, security, and brew jobs
  ([`83676a4`](https://github.com/liskeee/pkg-upgrade/commit/83676a4ed4ce2f3aa584460cd5b7496c5596cf3e))

- Add release workflow with semantic-release and PyPI OIDC publish
  ([`8bf79d5`](https://github.com/liskeee/pkg-upgrade/commit/8bf79d58dc9a40fad8d0ec0d0cb4aae2dd845d72))

- Enable Dependabot for actions and pip
  ([`eaf2e75`](https://github.com/liskeee/pkg-upgrade/commit/eaf2e7561b3c3c19e72d4fd8fc43562208cb7179))

### Documentation

- Add semantic-release and full CI design spec
  ([`a5d00f6`](https://github.com/liskeee/pkg-upgrade/commit/a5d00f68eb1bb06d3ccdd55960bd9300de7ad792))

- Add semantic-release and full CI implementation plan
  ([`d6208f1`](https://github.com/liskeee/pkg-upgrade/commit/d6208f10a629f51ab122d6fe6e1913f2bb32027e))

- Design spec for onboarding wizard and ~/.mac-upgrade config
  ([`270af62`](https://github.com/liskeee/pkg-upgrade/commit/270af62ff996bb7198d6493addae4fdf7136e12c))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Document release setup and flow
  ([`0e28d96`](https://github.com/liskeee/pkg-upgrade/commit/0e28d962692b29c76d2efba4398132bf7e9ddfc7))

- Seed changelog and contributing guide
  ([`0862f28`](https://github.com/liskeee/pkg-upgrade/commit/0862f2851d36962410989669ad021987dc2fd1a8))

### Features

- Add CLI argument parsing
  ([`c3e68ca`](https://github.com/liskeee/pkg-upgrade/commit/c3e68ca18eb86409bbc16529acd7695c0de81d54))

- Add execution engine with smart parallel grouping
  ([`4f81012`](https://github.com/liskeee/pkg-upgrade/commit/4f8101202cea7b2526e1612524a2bd377328cced))

- Add gem manager
  ([`db10f16`](https://github.com/liskeee/pkg-upgrade/commit/db10f16b1439b648d14405b28213b7fbdfb165ab))

- Add Homebrew casks manager
  ([`a42a3ef`](https://github.com/liskeee/pkg-upgrade/commit/a42a3efcaede3a23a49206cafb002789c0e3e972))

- Add Homebrew formulas manager
  ([`6b4fc24`](https://github.com/liskeee/pkg-upgrade/commit/6b4fc24338be9459e5ad9dc276c3d2d246767aa0))

- Add main Textual dashboard app
  ([`82cb376`](https://github.com/liskeee/pkg-upgrade/commit/82cb3769650c86f3f3a0fb8140aa35794c382583))

- Add manager registry with skip/only filtering
  ([`4d72cfc`](https://github.com/liskeee/pkg-upgrade/commit/4d72cfc5b7d472185676f34fe880eeb81979d2d3))

- Add ManagerCard and LiveLogPanel widgets
  ([`449d872`](https://github.com/liskeee/pkg-upgrade/commit/449d8720852f5ddf508e61909a0bb409297d877e))

- Add notifier with logging and macOS notifications
  ([`828e462`](https://github.com/liskeee/pkg-upgrade/commit/828e462e5f66536db83347473ee55fae13b2b90c))

- Add npm manager
  ([`9ce4ca5`](https://github.com/liskeee/pkg-upgrade/commit/9ce4ca5cf710c386adc21f134fbe05b757114c17))

- Add Package and Result data models
  ([`d5b08df`](https://github.com/liskeee/pkg-upgrade/commit/d5b08dffdd84096f8abf60ec2a2c30611dba6676))

- Add PackageManager ABC and fake fixture
  ([`06731ba`](https://github.com/liskeee/pkg-upgrade/commit/06731ba863005822508bd6441b38ff43f7354957))

- Add pip manager
  ([`bc0fb0f`](https://github.com/liskeee/pkg-upgrade/commit/bc0fb0f0b583d049bf8038ff1fb10ee09c545ea8))

- Add shared subprocess helper
  ([`15439f7`](https://github.com/liskeee/pkg-upgrade/commit/15439f751568da647e6ab6c8d453b2cb96fa0e8d))

- Add softwareupdate system manager
  ([`af17d19`](https://github.com/liskeee/pkg-upgrade/commit/af17d19f563b76fdefb5c665a8e85039f455a237))

- Onboarding wizard + persistent config at ~/.mac-upgrade
  ([`744c586`](https://github.com/liskeee/pkg-upgrade/commit/744c586f19b81c70253943c85c7bfbbaf0ad0d03))

- New config module: JSON load/save with atomic writes, version gate, and preservation of unknown
  keys for forward compatibility. - New onboarding Textual screen: 4-step wizard (managers →
  auto-confirm → notifications → logging) with a review panel before save. - CLI gains --onboard
  flag. Launch rules: * --onboard: run wizard and exit * no config file: run wizard on first launch,
  then continue * corrupt/version-mismatch config: warn to stderr, use defaults - resolve_settings()
  merges config with flags; flags always win. - 18 new tests covering config I/O and CLI setting
  resolution.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Project scaffolding
  ([`f0c3159`](https://github.com/liskeee/pkg-upgrade/commit/f0c3159ae105a8158a65abceb98c2cb13f2b5e4d))

- Update repository references and add install.sh plan
  ([`74c1739`](https://github.com/liskeee/pkg-upgrade/commit/74c1739b669dc27707755d7fed15e4324a2dd6f0))

* Changed repository URLs from lukaszlis to liskeee in: - mac-upgrade.rb - README.md -
  pyproject.toml * Added a new implementation plan for the install.sh script, detailing the
  installation process and user interface. * Updated the README to include installation instructions
  for the new curl | bash installer.

- **ci**: Add CI workflow with linting and testing
  ([`36f659f`](https://github.com/liskeee/pkg-upgrade/commit/36f659fa080342f5292ce7a5782aa8055dc9bda6))

- Introduced a CI workflow in to automate linting and testing processes. - Configured jobs for
  linting with Ruff, type checking with MyPy, and testing with Pytest, supporting multiple Python
  versions. - Enhanced to exclude coverage reports and build artifacts. - Added pre-commit
  configuration for code quality checks. - Updated to include new dependencies for testing and
  linting tools. - Refactored various classes to use a new enum for better state management.

- **install**: Complete venv fallback + MAC_UPGRADE_SOURCE override
  ([`f2430b9`](https://github.com/liskeee/pkg-upgrade/commit/f2430b9f4264b3798bee53fdd2881c2f4cae79f4))

- Fix try_pipx swallowing install failures (set -e disabled inside `if !`); explicit `|| return 1`
  so venv fallback actually triggers. - Add MAC_UPGRADE_SOURCE env var to override the pip spec
  entirely, enabling local/dev installs and test harnesses. - Add ERR-trap venv cleanup so partial
  installs don't leak state. - README: lead with curl|bash; add MAC_UPGRADE_REF pin example and
  uninstall instructions for both install paths.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- **install**: Detect Python 3.12+ (python3.13 → python3.12 → python3)
  ([`09588f9`](https://github.com/liskeee/pkg-upgrade/commit/09588f90e7f927d77ab5aaaaa45211347eb8d7d0))

- **install**: Scaffold curl|bash installer with strict mode and platform guard
  ([`1b9e36f`](https://github.com/liskeee/pkg-upgrade/commit/1b9e36fd0748a12be7822ec693a26cc933aa745b))
