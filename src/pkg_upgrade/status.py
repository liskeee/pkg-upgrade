"""Typed status vocabulary for package-manager lifecycle states.

Using ``StrEnum`` keeps string-equality comparisons working at runtime
(values *are* strings) while giving mypy a closed set to check against.
"""

from __future__ import annotations

from enum import StrEnum


class ManagerStatus(StrEnum):
    PENDING = "pending"
    CHECKING = "checking"
    AWAITING_CONFIRM = "awaiting_confirm"
    UPGRADING = "upgrading"
    DONE = "done"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


ACTIVE_STATUSES: frozenset[ManagerStatus] = frozenset(
    {
        ManagerStatus.PENDING,
        ManagerStatus.CHECKING,
        ManagerStatus.AWAITING_CONFIRM,
        ManagerStatus.UPGRADING,
    }
)
