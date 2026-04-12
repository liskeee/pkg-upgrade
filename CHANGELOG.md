# CHANGELOG


## v0.1.1 (2026-04-12)

### Build System

- **deps**: Update textual requirement from >=3.0.0 to >=8.2.3
  ([#10](https://github.com/liskeee/mac-upgrade/pull/10),
  [`47bd6de`](https://github.com/liskeee/mac-upgrade/commit/47bd6de5e5e53fe646831a155afa6b4e2a23848c))

Updates the requirements on [textual](https://github.com/Textualize/textual) to permit the latest
  version. - [Release notes](https://github.com/Textualize/textual/releases) -
  [Changelog](https://github.com/Textualize/textual/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/Textualize/textual/compare/v3.0.0...v8.2.3)

--- updated-dependencies: - dependency-name: textual dependency-version: 8.2.3

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update mypy requirement from >=1.11 to >=1.20.0
  ([#11](https://github.com/liskeee/mac-upgrade/pull/11),
  [`00bdc65`](https://github.com/liskeee/mac-upgrade/commit/00bdc65378858c5e14b5a3370a53f330d5e6cfa2))

Updates the requirements on [mypy](https://github.com/python/mypy) to permit the latest version. -
  [Changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/python/mypy/compare/v1.11...v1.20.0)

--- updated-dependencies: - dependency-name: mypy dependency-version: 1.20.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest-asyncio requirement
  ([#7](https://github.com/liskeee/mac-upgrade/pull/7),
  [`e82d166`](https://github.com/liskeee/mac-upgrade/commit/e82d166ea44fb8b7339ce4b620f17479f36821c8))

Updates the requirements on [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) to permit
  the latest version. - [Release notes](https://github.com/pytest-dev/pytest-asyncio/releases) -
  [Commits](https://github.com/pytest-dev/pytest-asyncio/compare/v0.25.0...v1.3.0)

--- updated-dependencies: - dependency-name: pytest-asyncio dependency-version: 1.3.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update pytest-cov requirement from >=5.0 to >=7.1.0
  ([#8](https://github.com/liskeee/mac-upgrade/pull/8),
  [`f2eb04f`](https://github.com/liskeee/mac-upgrade/commit/f2eb04fdbaffd5b4473676f0035f0c9cb54c71c2))

Updates the requirements on [pytest-cov](https://github.com/pytest-dev/pytest-cov) to permit the
  latest version. - [Changelog](https://github.com/pytest-dev/pytest-cov/blob/master/CHANGELOG.rst)
  - [Commits](https://github.com/pytest-dev/pytest-cov/compare/v5.0.0...v7.1.0)

--- updated-dependencies: - dependency-name: pytest-cov dependency-version: 7.1.0

dependency-type: direct:development ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps-dev**: Update ruff requirement from >=0.6 to >=0.15.10
  ([#9](https://github.com/liskeee/mac-upgrade/pull/9),
  [`f627928`](https://github.com/liskeee/mac-upgrade/commit/f62792893b451d8498bed1f87f5fc3b115235154))

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
  ([#13](https://github.com/liskeee/mac-upgrade/pull/13),
  [`be97220`](https://github.com/liskeee/mac-upgrade/commit/be972202cf4ca38d801dc2bc678e75ca66370409))

- brew: install via ephemeral local tap (homebrew rejects raw file paths); skip when formula has
  REPLACE_WITH_* placeholders - release: add workflow_dispatch with 'force' input (forces patch bump
  when no releasable commits exist)

- Run release job on ubuntu-latest
  ([`0c317fe`](https://github.com/liskeee/mac-upgrade/commit/0c317fee58dca2159e4150d7a83e050e2afcb384))

pypa/gh-action-pypi-publish only supports Linux runners.

- **deps**: Bump actions/checkout from 4 to 6 ([#2](https://github.com/liskeee/mac-upgrade/pull/2),
  [`b2fbecc`](https://github.com/liskeee/mac-upgrade/commit/b2fbeccf32867c34ed1a765344d0628dfb73ebf4))

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
  ([#5](https://github.com/liskeee/mac-upgrade/pull/5),
  [`71efa95`](https://github.com/liskeee/mac-upgrade/commit/71efa95d4a20be06a03ca9938b5285384d0b0a72))

Bumps [actions/download-artifact](https://github.com/actions/download-artifact) from 4 to 8. -
  [Release notes](https://github.com/actions/download-artifact/releases) -
  [Commits](https://github.com/actions/download-artifact/compare/v4...v8)

--- updated-dependencies: - dependency-name: actions/download-artifact dependency-version: '8'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump actions/setup-python from 5 to 6
  ([#4](https://github.com/liskeee/mac-upgrade/pull/4),
  [`091b135`](https://github.com/liskeee/mac-upgrade/commit/091b135bf73c4a0977275cab01cb86f2e61b0354))

Bumps [actions/setup-python](https://github.com/actions/setup-python) from 5 to 6. - [Release
  notes](https://github.com/actions/setup-python/releases) -
  [Commits](https://github.com/actions/setup-python/compare/v5...v6)

--- updated-dependencies: - dependency-name: actions/setup-python dependency-version: '6'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump actions/upload-artifact from 4 to 7
  ([#6](https://github.com/liskeee/mac-upgrade/pull/6),
  [`e8c63be`](https://github.com/liskeee/mac-upgrade/commit/e8c63be33fc87c2743624155992bc2da319c4445))

Bumps [actions/upload-artifact](https://github.com/actions/upload-artifact) from 4 to 7. - [Release
  notes](https://github.com/actions/upload-artifact/releases) -
  [Commits](https://github.com/actions/upload-artifact/compare/v4...v7)

--- updated-dependencies: - dependency-name: actions/upload-artifact dependency-version: '7'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump peter-evans/create-pull-request from 7 to 8
  ([#3](https://github.com/liskeee/mac-upgrade/pull/3),
  [`6d500e5`](https://github.com/liskeee/mac-upgrade/commit/6d500e5673a7b8dd30a87ac6245a928e02305b75))

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
  ([`3564f31`](https://github.com/liskeee/mac-upgrade/commit/3564f31a31f2520b24e2c2d8cd229e827cace54b))

- Fix CaskManager.current_version: use installed_versions[0] (was returning list) - Share `brew
  outdated --json=v2` between brew and cask via _brew_cache - Surface check_outdated errors via
  ManagerState.error / "error" status instead of silently swallowing non-zero exits - Escape
  backslashes in AppleScript notification strings - Add README.md and Homebrew formula skeleton
  (Formula/mac-upgrade.rb) so the project can be installed via `brew tap` + `brew install` - Update
  pyproject.toml with URLs/license/readme metadata

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Build System

- Configure python-semantic-release and add build dep
  ([`80f653c`](https://github.com/liskeee/mac-upgrade/commit/80f653c8a5d1ec11c079e469b95f4ecc5d6c73f6))

### Chores

- Fix missing trailing newline in plan doc
  ([`4416adf`](https://github.com/liskeee/mac-upgrade/commit/4416adf08fdea09a4745a5494720775d943bdedf))

Pre-commit end-of-file-fixer flagged this. Single-byte fix to keep pre-commit green in CI.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Code Style

- Apply ruff autofixes and format pass
  ([`dba5e86`](https://github.com/liskeee/mac-upgrade/commit/dba5e86086ed52f7aa83fa165562b6da80f2c9ff))

Run ruff --fix and ruff format across src/ and tests/. Mostly import sorting, trailing commas, and
  quote style normalization.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Continuous Integration

- Add formula bump workflow on stable releases
  ([`a4e9de2`](https://github.com/liskeee/mac-upgrade/commit/a4e9de2e9f12e3fe3e8e25e08cab214b840f1a6f))

- Add pre-commit, build, smoke, security, and brew jobs
  ([`83676a4`](https://github.com/liskeee/mac-upgrade/commit/83676a4ed4ce2f3aa584460cd5b7496c5596cf3e))

- Add release workflow with semantic-release and PyPI OIDC publish
  ([`8bf79d5`](https://github.com/liskeee/mac-upgrade/commit/8bf79d58dc9a40fad8d0ec0d0cb4aae2dd845d72))

- Enable Dependabot for actions and pip
  ([`eaf2e75`](https://github.com/liskeee/mac-upgrade/commit/eaf2e7561b3c3c19e72d4fd8fc43562208cb7179))

### Documentation

- Add semantic-release and full CI design spec
  ([`a5d00f6`](https://github.com/liskeee/mac-upgrade/commit/a5d00f68eb1bb06d3ccdd55960bd9300de7ad792))

- Add semantic-release and full CI implementation plan
  ([`d6208f1`](https://github.com/liskeee/mac-upgrade/commit/d6208f10a629f51ab122d6fe6e1913f2bb32027e))

- Design spec for onboarding wizard and ~/.mac-upgrade config
  ([`270af62`](https://github.com/liskeee/mac-upgrade/commit/270af62ff996bb7198d6493addae4fdf7136e12c))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Document release setup and flow
  ([`0e28d96`](https://github.com/liskeee/mac-upgrade/commit/0e28d962692b29c76d2efba4398132bf7e9ddfc7))

- Seed changelog and contributing guide
  ([`0862f28`](https://github.com/liskeee/mac-upgrade/commit/0862f2851d36962410989669ad021987dc2fd1a8))

### Features

- Add CLI argument parsing
  ([`c3e68ca`](https://github.com/liskeee/mac-upgrade/commit/c3e68ca18eb86409bbc16529acd7695c0de81d54))

- Add execution engine with smart parallel grouping
  ([`4f81012`](https://github.com/liskeee/mac-upgrade/commit/4f8101202cea7b2526e1612524a2bd377328cced))

- Add gem manager
  ([`db10f16`](https://github.com/liskeee/mac-upgrade/commit/db10f16b1439b648d14405b28213b7fbdfb165ab))

- Add Homebrew casks manager
  ([`a42a3ef`](https://github.com/liskeee/mac-upgrade/commit/a42a3efcaede3a23a49206cafb002789c0e3e972))

- Add Homebrew formulas manager
  ([`6b4fc24`](https://github.com/liskeee/mac-upgrade/commit/6b4fc24338be9459e5ad9dc276c3d2d246767aa0))

- Add main Textual dashboard app
  ([`82cb376`](https://github.com/liskeee/mac-upgrade/commit/82cb3769650c86f3f3a0fb8140aa35794c382583))

- Add manager registry with skip/only filtering
  ([`4d72cfc`](https://github.com/liskeee/mac-upgrade/commit/4d72cfc5b7d472185676f34fe880eeb81979d2d3))

- Add ManagerCard and LiveLogPanel widgets
  ([`449d872`](https://github.com/liskeee/mac-upgrade/commit/449d8720852f5ddf508e61909a0bb409297d877e))

- Add notifier with logging and macOS notifications
  ([`828e462`](https://github.com/liskeee/mac-upgrade/commit/828e462e5f66536db83347473ee55fae13b2b90c))

- Add npm manager
  ([`9ce4ca5`](https://github.com/liskeee/mac-upgrade/commit/9ce4ca5cf710c386adc21f134fbe05b757114c17))

- Add Package and Result data models
  ([`d5b08df`](https://github.com/liskeee/mac-upgrade/commit/d5b08dffdd84096f8abf60ec2a2c30611dba6676))

- Add PackageManager ABC and fake fixture
  ([`06731ba`](https://github.com/liskeee/mac-upgrade/commit/06731ba863005822508bd6441b38ff43f7354957))

- Add pip manager
  ([`bc0fb0f`](https://github.com/liskeee/mac-upgrade/commit/bc0fb0f0b583d049bf8038ff1fb10ee09c545ea8))

- Add shared subprocess helper
  ([`15439f7`](https://github.com/liskeee/mac-upgrade/commit/15439f751568da647e6ab6c8d453b2cb96fa0e8d))

- Add softwareupdate system manager
  ([`af17d19`](https://github.com/liskeee/mac-upgrade/commit/af17d19f563b76fdefb5c665a8e85039f455a237))

- Onboarding wizard + persistent config at ~/.mac-upgrade
  ([`744c586`](https://github.com/liskeee/mac-upgrade/commit/744c586f19b81c70253943c85c7bfbbaf0ad0d03))

- New config module: JSON load/save with atomic writes, version gate, and preservation of unknown
  keys for forward compatibility. - New onboarding Textual screen: 4-step wizard (managers →
  auto-confirm → notifications → logging) with a review panel before save. - CLI gains --onboard
  flag. Launch rules: * --onboard: run wizard and exit * no config file: run wizard on first launch,
  then continue * corrupt/version-mismatch config: warn to stderr, use defaults - resolve_settings()
  merges config with flags; flags always win. - 18 new tests covering config I/O and CLI setting
  resolution.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- Project scaffolding
  ([`f0c3159`](https://github.com/liskeee/mac-upgrade/commit/f0c3159ae105a8158a65abceb98c2cb13f2b5e4d))

- Update repository references and add install.sh plan
  ([`74c1739`](https://github.com/liskeee/mac-upgrade/commit/74c1739b669dc27707755d7fed15e4324a2dd6f0))

* Changed repository URLs from lukaszlis to liskeee in: - mac-upgrade.rb - README.md -
  pyproject.toml * Added a new implementation plan for the install.sh script, detailing the
  installation process and user interface. * Updated the README to include installation instructions
  for the new curl | bash installer.

- **ci**: Add CI workflow with linting and testing
  ([`36f659f`](https://github.com/liskeee/mac-upgrade/commit/36f659fa080342f5292ce7a5782aa8055dc9bda6))

- Introduced a CI workflow in to automate linting and testing processes. - Configured jobs for
  linting with Ruff, type checking with MyPy, and testing with Pytest, supporting multiple Python
  versions. - Enhanced to exclude coverage reports and build artifacts. - Added pre-commit
  configuration for code quality checks. - Updated to include new dependencies for testing and
  linting tools. - Refactored various classes to use a new enum for better state management.

- **install**: Complete venv fallback + MAC_UPGRADE_SOURCE override
  ([`f2430b9`](https://github.com/liskeee/mac-upgrade/commit/f2430b9f4264b3798bee53fdd2881c2f4cae79f4))

- Fix try_pipx swallowing install failures (set -e disabled inside `if !`); explicit `|| return 1`
  so venv fallback actually triggers. - Add MAC_UPGRADE_SOURCE env var to override the pip spec
  entirely, enabling local/dev installs and test harnesses. - Add ERR-trap venv cleanup so partial
  installs don't leak state. - README: lead with curl|bash; add MAC_UPGRADE_REF pin example and
  uninstall instructions for both install paths.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

- **install**: Detect Python 3.12+ (python3.13 → python3.12 → python3)
  ([`09588f9`](https://github.com/liskeee/mac-upgrade/commit/09588f90e7f927d77ab5aaaaa45211347eb8d7d0))

- **install**: Scaffold curl|bash installer with strict mode and platform guard
  ([`1b9e36f`](https://github.com/liskeee/mac-upgrade/commit/1b9e36fd0748a12be7822ec693a26cc933aa745b))
