from __future__ import annotations

from dataclasses import dataclass

from pkg_upgrade.status import ManagerStatus


@dataclass(frozen=True)
class GlyphTable:
    statuses: dict[ManagerStatus, str]

    def status(self, s: ManagerStatus) -> str:
        return self.statuses[s]

    @classmethod
    def unicode(cls) -> GlyphTable:
        return cls(
            {
                ManagerStatus.PENDING: "⏳ queued",
                ManagerStatus.CHECKING: "⧗ checking",
                ManagerStatus.AWAITING_CONFIRM: "⏸ awaiting confirm",
                ManagerStatus.UPGRADING: "▶ upgrading",
                ManagerStatus.DONE: "✓ done",
                ManagerStatus.SKIPPED: "⏭ skipped",
                ManagerStatus.UNAVAILABLE: "∅ unavailable",
                ManagerStatus.ERROR: "⚠ error",
            }
        )

    @classmethod
    def ascii(cls) -> GlyphTable:
        return cls(
            {
                ManagerStatus.PENDING: ". queued",
                ManagerStatus.CHECKING: "- checking",
                ManagerStatus.AWAITING_CONFIRM: "P awaiting confirm",
                ManagerStatus.UPGRADING: "> upgrading",
                ManagerStatus.DONE: "v done",
                ManagerStatus.SKIPPED: "s skipped",
                ManagerStatus.UNAVAILABLE: "x unavailable",
                ManagerStatus.ERROR: "! error",
            }
        )


def pick_glyph_table(encoding: str | None) -> GlyphTable:
    enc = (encoding or "").lower()
    if "utf" in enc:
        return GlyphTable.unicode()
    return GlyphTable.ascii()
