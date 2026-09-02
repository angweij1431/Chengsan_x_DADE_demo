"""
Rate limiting for the booth.

Two independent ceilings, because they protect against different things:

  per-session  stops one visitor monopolising the booth.
  daily total  stops the whole day blowing the budget. This is the one that
               matters when a paid video API is behind the button - a stuck
               refresh key can otherwise burn real money in minutes.

Backed by SQLite so a laptop reboot mid-event doesn't reset everyone's quota.
"""

import os
import sqlite3
import threading
import time

DB_PATH = os.path.join(os.getcwd(), "booth_usage.db")

# action -> (per-session limit, daily total limit) with their env overrides.
DEFAULT_LIMITS = {
    "dance_template": ("LIMIT_DANCE_TEMPLATE_SESSION", 3, "LIMIT_DANCE_TEMPLATE_DAILY", 300),
    "dance_custom": ("LIMIT_DANCE_CUSTOM_SESSION", 1, "LIMIT_DANCE_CUSTOM_DAILY", 100),
    "edit_image": ("LIMIT_EDIT_SESSION", 5, "LIMIT_EDIT_DAILY", 400),
    "scene_image": ("LIMIT_SCENE_SESSION", 5, "LIMIT_SCENE_DAILY", 400),
}

# Reentrant on purpose. check_and_consume() and refund() hold this lock across
# a read-then-write, and both call _db() inside it - which takes the same lock
# to create the connection. A plain Lock deadlocks there, but only on the very
# first call after startup, when _conn is still None. That made it a bug that
# hid during testing (any earlier /api/config call warmed the connection) and
# would have surfaced as the first visitor of the day hanging forever.
_lock = threading.RLock()
_conn = None


class RateLimited(Exception):
    def __init__(self, message, scope):
        super().__init__(message)
        self.scope = scope  # "session" or "daily"


def _db():
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                _conn.execute(
                    """CREATE TABLE IF NOT EXISTS usage (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           session_id TEXT NOT NULL,
                           action TEXT NOT NULL,
                           day TEXT NOT NULL,
                           created_at REAL NOT NULL
                       )"""
                )
                _conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lookup ON usage(action, day, session_id)"
                )
                _conn.commit()
    return _conn


def _today():
    return time.strftime("%Y-%m-%d")


def limits_for(action):
    session_key, session_default, daily_key, daily_default = DEFAULT_LIMITS[action]
    return (
        int(os.getenv(session_key, session_default)),
        int(os.getenv(daily_key, daily_default)),
    )


def usage_for(session_id, action):
    db = _db()
    day = _today()
    session_used = db.execute(
        "SELECT COUNT(*) FROM usage WHERE action=? AND day=? AND session_id=?",
        (action, day, session_id),
    ).fetchone()[0]
    daily_used = db.execute(
        "SELECT COUNT(*) FROM usage WHERE action=? AND day=?", (action, day)
    ).fetchone()[0]
    return session_used, daily_used


def check_and_consume(session_id, action):
    """
    Record one use of `action`, or raise RateLimited if either ceiling is hit.
    Call this *before* spending money on a generation.
    """
    if action not in DEFAULT_LIMITS:
        raise ValueError(f"Unknown rate-limited action: {action}")

    if os.getenv("DISABLE_RATE_LIMITS", "").lower() == "true":
        return

    session_limit, daily_limit = limits_for(action)

    with _lock:
        session_used, daily_used = usage_for(session_id, action)

        if daily_used >= daily_limit:
            raise RateLimited(
                "The booth has hit its daily limit for this feature. "
                "Please come back tomorrow, or ask a staff member.",
                "daily",
            )
        if session_used >= session_limit:
            raise RateLimited(
                f"You've used all {session_limit} of your goes at this station. "
                "Let someone else have a turn!",
                "session",
            )

        db = _db()
        db.execute(
            "INSERT INTO usage (session_id, action, day, created_at) VALUES (?,?,?,?)",
            (session_id, action, _today(), time.time()),
        )
        db.commit()


def refund(session_id, action):
    """
    Hand back the most recent use of `action`.

    Call this when a generation fails for a reason that isn't the visitor's
    fault - a provider outage, a safety block, a timeout. Losing your one go at
    the booth because someone's API had a bad minute is a rotten experience.
    """
    with _lock:
        db = _db()
        row = db.execute(
            "SELECT id FROM usage WHERE action=? AND day=? AND session_id=? "
            "ORDER BY id DESC LIMIT 1",
            (action, _today(), session_id),
        ).fetchone()
        if row:
            db.execute("DELETE FROM usage WHERE id=?", (row[0],))
            db.commit()


def remaining(session_id, action):
    session_limit, daily_limit = limits_for(action)
    session_used, daily_used = usage_for(session_id, action)
    return {
        "session_remaining": max(0, session_limit - session_used),
        "session_limit": session_limit,
        "daily_remaining": max(0, daily_limit - daily_used),
        "daily_limit": daily_limit,
    }


def stats_today():
    """Totals per action for the staff dashboard."""
    db = _db()
    rows = db.execute(
        "SELECT action, COUNT(*) FROM usage WHERE day=? GROUP BY action", (_today(),)
    ).fetchall()
    counts = {action: count for action, count in rows}
    visitors = db.execute(
        "SELECT COUNT(DISTINCT session_id) FROM usage WHERE day=?", (_today(),)
    ).fetchone()[0]
    return {"date": _today(), "by_action": counts, "unique_visitors": visitors}
