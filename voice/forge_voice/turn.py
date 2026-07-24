"""Turn lifecycle and barge-in cancellation."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field


@dataclass
class TurnController:
    """Tracks active turn; barge-in marks turn abandoned."""

    _lock: threading.Lock = field(default_factory=threading.Lock)
    _active_turn_id: str | None = None
    _cancelled: bool = False

    def begin_turn(self) -> str:
        with self._lock:
            self._active_turn_id = str(uuid.uuid4())
            self._cancelled = False
            return self._active_turn_id

    def cancel_turn(self) -> None:
        with self._lock:
            self._cancelled = True

    def is_cancelled(self, turn_id: str | None = None) -> bool:
        with self._lock:
            if turn_id is not None and turn_id != self._active_turn_id:
                return True
            return self._cancelled

    def is_active(self, turn_id: str) -> bool:
        with self._lock:
            return self._active_turn_id == turn_id and not self._cancelled
