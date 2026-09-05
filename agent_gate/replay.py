from __future__ import annotations

import sqlite3
import threading


class ReplayStore:
    """Atomic single-use ticket store.

    Pass a filesystem path for persistence across processes/restarts. ``:memory:``
    is intentionally available for isolated tests.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS consumed_tickets (ticket_id TEXT PRIMARY KEY, consumed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    def consume_once(self, ticket_id: str) -> bool:
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute("INSERT INTO consumed_tickets(ticket_id) VALUES (?)", (ticket_id,))
                self._db.execute("COMMIT")
                return True
            except sqlite3.IntegrityError:
                self._db.execute("ROLLBACK")
                return False
            except Exception:
                self._db.execute("ROLLBACK")
                raise
