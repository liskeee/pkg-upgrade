from __future__ import annotations

from dataclasses import dataclass

from pkg_upgrade.status import ManagerStatus

SPINNER_FRAMES_UNICODE: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
SPINNER_FRAMES_ASCII: tuple[str, ...] = ("|", "/", "-", "\\")


@dataclass(frozen=True)
class GlyphTable:
    statuses: dict[ManagerStatus, str]
    spinner_frames: tuple[str, ...]
    use_unicode: bool

    def status(self, s: ManagerStatus) -> str:
        return self.statuses[s]

    def spinner(self, tick: int) -> str:
        return self.spinner_frames[tick % len(self.spinner_frames)]

    @classmethod
    def unicode(cls) -> GlyphTable:
        return cls(
            statuses={
                ManagerStatus.PENDING: "⏳ queued",
                ManagerStatus.CHECKING: "⧗ checking",
                ManagerStatus.AWAITING_CONFIRM: "⏸ awaiting confirm",
                ManagerStatus.UPGRADING: "▶ upgrading",
                ManagerStatus.DONE: "✓ done",
                ManagerStatus.SKIPPED: "⏭ skipped",
                ManagerStatus.UNAVAILABLE: "∅ unavailable",
                ManagerStatus.ERROR: "⚠ error",
            },
            spinner_frames=SPINNER_FRAMES_UNICODE,
            use_unicode=True,
        )

    @classmethod
    def ascii(cls) -> GlyphTable:
        return cls(
            statuses={
                ManagerStatus.PENDING: ". queued",
                ManagerStatus.CHECKING: "- checking",
                ManagerStatus.AWAITING_CONFIRM: "P awaiting confirm",
                ManagerStatus.UPGRADING: "> upgrading",
                ManagerStatus.DONE: "v done",
                ManagerStatus.SKIPPED: "s skipped",
                ManagerStatus.UNAVAILABLE: "x unavailable",
                ManagerStatus.ERROR: "! error",
            },
            spinner_frames=SPINNER_FRAMES_ASCII,
            use_unicode=False,
        )


def pick_glyph_table(encoding: str | None) -> GlyphTable:
    enc = (encoding or "").lower()
    if "utf" in enc:
        return GlyphTable.unicode()
    return GlyphTable.ascii()
