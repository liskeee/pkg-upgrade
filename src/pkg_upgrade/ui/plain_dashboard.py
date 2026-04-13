# src/pkg_upgrade/ui/plain_dashboard.py
from __future__ import annotations

import sys
from typing import Any


class PlainDashboardUI:
    async def run(self, executor: Any, *, auto_yes: bool, dry_run: bool) -> None:
        def say(key: str, msg: str) -> None:
            print(f"[{key}] {msg}", flush=True)

        async def on_update(key: str) -> None:
            s = executor.states[key]
            say(key, s.status.value)

        async def on_result(key: str, pkg: str, ok: bool) -> None:
            marker = "ok" if ok else "FAIL"
            say(key, f"{marker} {pkg}")

        await executor.check_all(on_update=on_update)

        if dry_run:
            for k, s in executor.states.items():
                if s.outdated:
                    say(k, f"dry-run: would upgrade {len(s.outdated)} package(s)")
                    from pkg_upgrade.status import ManagerStatus  # noqa: PLC0415
                    s.status = ManagerStatus.DONE
            return

        for key, s in executor.states.items():
            if not s.outdated:
                continue
            if not auto_yes:
                say(key, "skipped (no TTY and --yes not set)")
                executor.skip_manager(key)
                continue
            await executor.upgrade_manager(key, on_update=on_update, on_result=on_result)
        sys.stdout.flush()
