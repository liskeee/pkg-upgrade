# mac-upgrade — Onboarding & Persistent Config Design Spec

Add a first-run onboarding wizard and a persistent user config file at `~/.mac-upgrade`, plus a `--onboard` flag to re-run the wizard.

## Goals

- First-time users get a guided setup instead of raw CLI flags.
- Preferred defaults persist across runs.
- Re-configurable at any time via `mac-upgrade --onboard`.
- CLI flags continue to fully override saved settings (flags win).

## Config File

- **Path:** `~/.mac-upgrade` (single JSON file)
- **Format:** JSON (stdlib only)
- **Schema:**

```json
{
  "version": 1,
  "managers": ["brew", "cask", "pip", "npm", "gem", "system"],
  "auto_yes": false,
  "notify": true,
  "log": true,
  "log_dir": "~/"
}
```

- `version` enables future schema migrations.
- Unknown keys present in the on-disk file are preserved when rewriting (forward compatibility).
- `managers` is the set of manager keys the user wants to run by default. Values outside the known set are ignored on load.
- `log_dir` is stored as written by the user; `~` expansion happens at use-time, not save-time.

## New Modules

### `src/mac_upgrade/config.py`

Pure stdlib. No Textual imports.

```python
CONFIG_PATH = Path.home() / ".mac-upgrade"

DEFAULT_CONFIG = {
    "version": 1,
    "managers": ["brew", "cask", "pip", "npm", "gem", "system"],
    "auto_yes": False,
    "notify": True,
    "log": True,
    "log_dir": "~/",
}

def load_config(path: Path = CONFIG_PATH) -> tuple[dict, str | None]:
    """Return (config, warning). warning is None on clean load; a string when
    the file was missing/corrupt/unreadable and defaults were used instead."""

def save_config(cfg: dict, path: Path = CONFIG_PATH) -> None:
    """Atomically write JSON (write temp + rename). Merges unknown keys from
    existing file so we don't clobber forward-compatible additions."""

def config_exists(path: Path = CONFIG_PATH) -> bool: ...
```

### `src/mac_upgrade/onboarding.py`

A Textual `Screen` subclass that walks through 4 steps and returns the resulting config dict via a callback or `dismiss(result)`.

```python
class OnboardingScreen(Screen[dict | None]):
    """Dismisses with the resulting config dict on Save, or None on Cancel."""
```

## Wizard UX

A Textual `Screen` with sequential steps. Header shows `Step N of 4`. Footer shows `[Enter] Next · [B] Back · [Q] Cancel`.

### Step 1 — Package managers

Checkbox list of all six managers. Each row shows icon, name, and live detection:
- `✓ installed` — row is enabled and pre-checked.
- `✗ not found` — row is disabled and cannot be checked.

Detection runs `is_available()` on each manager concurrently before the step renders.

### Step 2 — Auto-confirm

Radio group:
- `● Ask me to confirm each manager before upgrading (recommended)` → `auto_yes: false`
- `○ Upgrade everything automatically (--yes by default)` → `auto_yes: true`

### Step 3 — Notifications

Single checkbox: `[x] Show a macOS notification when upgrades complete` → `notify: bool`

### Step 4 — Logging

Checkbox + path input:
```
[x] Write a log file for each run
Log directory: [ ~/                          ]
```
Path input is disabled when the checkbox is off. Path is not validated (accepted as-is); invalid paths surface later when the log is actually written.

### Review step

Shows the resulting JSON pretty-printed, a `[Save]` button, and `[Back]` to edit. On save:
1. `save_config(cfg)`
2. Flash `Saved ✓` for ~1s
3. Dismiss screen with `cfg`

### Cancel

`Q` at any point dismisses with `None`. Caller decides what to do (see CLI integration).

## CLI Integration

### New flag

```
--onboard    Run the configuration wizard and exit
```

### Launch decision tree in `cli.py`

1. `--version` or `--list` → handled as today; never triggers onboarding.
2. `--onboard` → launch wizard → on save, exit 0; on cancel, exit 0 without changes.
3. No config file and not `--onboard` → launch wizard → if saved, continue into normal flow using saved config; if cancelled, exit 0 (treat as user bailed out of setup).
4. Config file exists → load it (or warn + use defaults on corruption), apply as defaults, run normally.

### Config → defaults mapping

Applied *before* CLI flags, so flags always win.

| Config key | CLI override | Resolution |
|---|---|---|
| `managers` | `--only`, `--skip` | Start from config `managers`. If `--only` passed, intersect. If `--skip` passed, subtract. |
| `auto_yes` | `--yes` | `--yes` forces true. No CLI way to force false when config says true (acceptable; user can re-onboard). |
| `notify` | `--no-notify` | `--no-notify` forces false. |
| `log` | `--no-log` | `--no-log` forces false. |
| `log_dir` | `--log-dir <path>` | Flag overrides. `~` expanded at use. |

### Corrupt / missing-version config

On `json.JSONDecodeError`, unreadable file, or `version` ≠ expected:
- Print to stderr: `warning: ~/.mac-upgrade is unreadable or outdated — using defaults. Run 'mac-upgrade --onboard' to reconfigure.`
- Do NOT auto-launch the wizard (user might be in a non-TTY context like cron).
- Continue with `DEFAULT_CONFIG`.

## Testing

### `tests/test_config.py`

- `load_config` returns defaults + warning when file missing.
- `load_config` returns defaults + warning on malformed JSON.
- `save_config` + `load_config` roundtrip preserves all keys.
- `save_config` preserves unknown keys that were already in the file.
- `save_config` writes atomically (temp file + rename).

### `tests/test_cli.py` (additions)

Each test uses a `tmp_path` as `$HOME` via monkeypatching `Path.home`:

- `--onboard` with no config → launches wizard path (mock the screen to auto-dismiss) → config saved, app exits without upgrading.
- No config, no `--onboard` → wizard launches → saved → app continues.
- Existing config → wizard does not launch → defaults come from config.
- Corrupt config → stderr warning printed → defaults used → no wizard auto-launch.
- `--list` with no config → no wizard; lists managers and exits.
- Flag precedence: `--skip npm` with config `managers: [..., "npm", ...]` → `npm` excluded.

### `tests/test_onboarding.py`

Smoke test using Textual's `Pilot`:
- Launch `OnboardingScreen` in a minimal test app.
- Walk through all 4 steps with key presses, save.
- Assert dismissed dict matches expected shape.

## Out of Scope

- Directory-layout config (`~/.mac-upgrade/` with subfiles) — can migrate later via `version` bump.
- Config migration from v1 → v2 — no v2 yet.
- Scheduled/automated runs (cron, launchd) — separate future feature.
- Per-manager config (e.g., custom `brew upgrade` flags) — not requested.
- Editing config outside the wizard from within the app — users edit `~/.mac-upgrade` by hand if they want.
