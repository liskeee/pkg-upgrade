from __future__ import annotations

import asyncio
import json
from typing import Any

from rich.console import Console

from pkg_upgrade.ui._input import KeyInput, RealInput

_BACK = object()
_QUIT = object()


class RichOnboardingUI:
    def __init__(self, input: KeyInput | None = None, quiet: bool = False) -> None:
        self._input: KeyInput = input if input is not None else RealInput()
        self._console = Console(quiet=quiet)

    def _read(self) -> str:
        try:
            return self._input.read_key()
        except StopIteration:
            return "q"

    def _render(self, title: str, body: str) -> None:
        self._console.clear()
        self._console.print(f"[bold]{title}[/bold]")
        self._console.print(body)

    def _step_managers(self, cfg: dict[str, Any]) -> object:  # noqa: PLR0912
        from pkg_upgrade.registry import discover_managers  # noqa: PLC0415

        mgrs = discover_managers()
        available: dict[str, bool] = {}
        try:
            loop = asyncio.new_event_loop()
            try:
                async def _probe() -> dict[str, bool]:
                    return {m.key: bool(await m.is_available()) for m in mgrs}

                available = loop.run_until_complete(_probe())
            finally:
                loop.close()
        except Exception:
            available = {m.key: True for m in mgrs}

        selected = {m.key for m in mgrs if available.get(m.key, False) and m.key in set(cfg.get("managers") or [])}
        if not selected:
            selected = {m.key for m in mgrs if available.get(m.key, False)}
        idx = 0
        while True:
            lines = [
                "Which package managers do you want to upgrade? "
                "(space toggles, a=all, n=none, enter=next, b=back, q=quit)"
            ]
            for i, m in enumerate(mgrs):
                mark = "[x]" if m.key in selected else "[ ]"
                avail = "" if available.get(m.key, False) else " (not found)"
                cursor = ">" if i == idx else " "
                lines.append(f"{cursor} {mark} {m.icon} {m.key} - {m.name}{avail}")
            self._render("Step 1/5: Managers", "\n".join(lines))
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k in {"j", "down"}:
                idx = min(idx + 1, len(mgrs) - 1)
            elif k in {"k", "up"}:
                idx = max(idx - 1, 0)
            elif k == "space":
                m = mgrs[idx]
                if available.get(m.key, False):
                    if m.key in selected:
                        selected.discard(m.key)
                    else:
                        selected.add(m.key)
            elif k == "a":
                selected = {m.key for m in mgrs if available.get(m.key, False)}
            elif k == "n":
                selected = set()
            elif k == "enter":
                cfg["managers"] = sorted(selected)
                return None

    def _step_confirm(self, cfg: dict[str, Any]) -> object:
        idx = 1 if cfg.get("auto_yes") else 0
        while True:
            options = [
                ("Ask before each manager (recommended)", False),
                ("Upgrade everything automatically (--yes)", True),
            ]
            lines = ["How should upgrades be confirmed? (j/k move, enter select, b back, q quit)"]
            for i, (label, _) in enumerate(options):
                cursor = ">" if i == idx else " "
                lines.append(f"{cursor} ( ) {label}" if i != idx else f"{cursor} (*) {label}")
            self._render("Step 2/5: Confirmation", "\n".join(lines))
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k in {"j", "down"}:
                idx = min(idx + 1, 1)
            elif k in {"k", "up"}:
                idx = max(idx - 1, 0)
            elif k == "enter":
                cfg["auto_yes"] = options[idx][1]
                return None

    def _step_notify(self, cfg: dict[str, Any]) -> object:
        val = bool(cfg.get("notify", True))
        while True:
            mark = "[x]" if val else "[ ]"
            self._render(
                "Step 3/5: Notifications",
                f"{mark} Show a notification when upgrades complete\n"
                "(space toggles, enter next, b back, q quit)",
            )
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k == "space":
                val = not val
            elif k == "enter":
                cfg["notify"] = val
                return None

    def _step_log(self, cfg: dict[str, Any]) -> object:  # noqa: PLR0912
        log_on = bool(cfg.get("log", True))
        log_dir = str(cfg.get("log_dir", "~/"))
        phase = "toggle"
        buf = log_dir
        while True:
            if phase == "toggle":
                mark = "[x]" if log_on else "[ ]"
                self._render(
                    "Step 4/5: Logging",
                    f"{mark} Write a log file for each run\n"
                    "(space toggles, enter next, b back, q quit)",
                )
                k = self._read()
                if k in {"q", "ctrl-c"}:
                    return _QUIT
                if k == "b":
                    return _BACK
                if k == "space":
                    log_on = not log_on
                elif k == "enter":
                    if log_on:
                        phase = "path"
                    else:
                        cfg["log"] = False
                        cfg["log_dir"] = log_dir
                        return None
            else:
                self._render(
                    "Step 4/5: Log directory",
                    f"Path: {buf}_\n"
                    "(type to edit, backspace to delete, enter to accept, b back, q quit)",
                )
                k = self._read()
                if k in {"q", "ctrl-c"}:
                    return _QUIT
                if k == "b":
                    phase = "toggle"
                    continue
                if k == "backspace":
                    buf = buf[:-1]
                elif k == "enter":
                    cfg["log"] = True
                    cfg["log_dir"] = buf or "~/"
                    return None
                elif len(k) == 1 and k.isprintable():
                    buf += k

    def _step_review(self, cfg: dict[str, Any]) -> object:
        self._render(
            "Step 5/5: Review",
            json.dumps(cfg, indent=2, sort_keys=True) + "\n\n(enter=save, b=back, q=cancel)",
        )
        while True:
            k = self._read()
            if k in {"q", "ctrl-c"}:
                return _QUIT
            if k == "b":
                return _BACK
            if k == "enter":
                return None

    def run(self, initial: dict[str, Any]) -> dict[str, Any] | None:
        cfg = dict(initial)
        steps = [
            self._step_managers,
            self._step_confirm,
            self._step_notify,
            self._step_log,
            self._step_review,
        ]
        i = 0
        while i < len(steps):
            outcome = steps[i](cfg)
            if outcome is _QUIT:
                return None
            if outcome is _BACK:
                i = max(0, i - 1)
            else:
                i += 1
        return cfg
