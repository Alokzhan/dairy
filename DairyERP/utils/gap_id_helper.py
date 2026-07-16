"""
utils/gap_id_helper.py
Finds the lowest available (gap) ID in any table.
Used to reuse deleted IDs instead of always incrementing.
"""

import sqlite3


def get_next_available_id(conn, table_name):
    """
    Returns the lowest missing ID (gap) in the table.
    If no gaps, returns None (let AUTOINCREMENT handle it).

    Example:
      IDs in table: 1, 3, 4  → returns 2
      IDs in table: 1, 2, 3  → returns None (no gap, next = 4)
      IDs in table: []        → returns 1
    """
    try:
        c = conn.cursor()

        # Get all existing IDs sorted
        c.execute(f"SELECT id FROM {table_name} ORDER BY id ASC")
        existing_ids = [row[0] for row in c.fetchall()]

        if not existing_ids:
            return 1  # empty table, start from 1

        # Find first gap
        for expected, actual in enumerate(existing_ids, start=1):
            if expected != actual:
                return expected  # gap found

        # No gap — return next after last
        return existing_ids[-1] + 1

    except sqlite3.Error as e:
        print(f"[get_next_available_id] Error: {e}")
        return None