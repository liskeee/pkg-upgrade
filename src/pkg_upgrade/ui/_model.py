from __future__ import annotations

from dataclasses import dataclass, field

from pkg_upgrade.status import ACTIVE_STATUSES, ManagerStatus


@dataclass
class Row:
    key: str
    name: str
    icon: str
    status: ManagerStatus
    done: int
    total: int
    duration_s: int
    log: list[str] = field(default_factory=list)


@dataclass
class UIModel:
    rows: list[Row]
    focus_index: int = 0
    expanded_key: str | None = None
    filter_text: str = ""

    @property
    def focus_key(self) -> str | None:
        vis = self.visible_rows
        if not vis:
            return None
        idx = min(self.focus_index, len(vis) - 1)
        return vis[idx].key

    @property
    def visible_rows(self) -> list[Row]:
        if not self.filter_text:
            return list(self.rows)
        f = self.filter_text.lower()
        return [r for r in self.rows if f in r.key.lower() or f in r.name.lower()]

    def move_focus(self, delta: int) -> None:
        n = len(self.visible_rows)
        if n == 0:
            return
        self.focus_index = max(0, min(self.focus_index + delta, n - 1))

    def focus_top(self) -> None:
        self.focus_index = 0

    def focus_bottom(self) -> None:
        self.focus_index = max(0, len(self.visible_rows) - 1)

    def set_filter(self, text: str) -> None:
        self.filter_text = text
        self.focus_index = 0

    def toggle_expand(self) -> None:
        key = self.focus_key
        if key is None:
            return
        self.expanded_key = None if self.expanded_key == key else key

    def append_log(self, key: str, line: str) -> None:
        for r in self.rows:
            if r.key == key:
                r.log.append(line)
                return

    def all_done(self) -> bool:
        return all(r.status not in ACTIVE_STATUSES for r in self.rows)

    def focused_row(self) -> Row | None:
        key = self.focus_key
        if key is None:
            return None
        for r in self.rows:
            if r.key == key:
                return r
        return None
