import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "dairy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================
# ENSURE TABLES
# ==========================

def ensure_ghee_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS ghee_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date      TEXT    NOT NULL,
                shift           TEXT    DEFAULT 'Morning',
                cream_used_kg   REAL    DEFAULT 0,
                ghee_produced   REAL    DEFAULT 0,
                packaged_qty    REAL    DEFAULT 0,
                packet_size     TEXT,
                ghee_sold       REAL    DEFAULT 0,
                ghee_distributed REAL   DEFAULT 0,
                ghee_wasted     REAL    DEFAULT 0,
                batch_number    TEXT,
                employee_id     INTEGER,
                employee_name   TEXT,
                notes           TEXT,
                created_at      TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)

        conn.commit()
        print("✅ Ghee tables ready.")
    except sqlite3.Error as e:
        print(f"[ensure_ghee_tables] {e}")
    finally:
        if conn: conn.close()


# ==========================
# GET CREAM STOCK (from cream module)
# ==========================

def get_available_cream_stock():
    """
    Reads cream_entries table directly to get current cream stock.
    Stock = produced - used_in_ghee(from cream module) - sold - wasted
            - already_used_in_ghee_entries(this module)
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # cream produced and already allocated to ghee/sold/wasted (recorded in cream_entries)
        c.execute("""
            SELECT
                COALESCE(SUM(cream_kg),        0) AS produced,
                COALESCE(SUM(cream_used_ghee), 0) AS used_ghee_cream_module,
                COALESCE(SUM(cream_sold),      0) AS sold,
                COALESCE(SUM(cream_wasted),    0) AS wasted
            FROM cream_entries
        """)
        r = c.fetchone()
        produced = float(r["produced"])
        allocated_out = (float(r["used_ghee_cream_module"]) +
                         float(r["sold"]) + float(r["wasted"]))

        # cream actually consumed by ghee_entries (this module's own usage)
        c.execute("SELECT COALESCE(SUM(cream_used_kg), 0) FROM ghee_entries")
        consumed_in_ghee_module = float(c.fetchone()[0])

        # available = produced - (cream module's own allocations) - (ghee module's actual usage)
        # NOTE: cream_used_ghee in cream_entries represents intent/transfer,
        # ghee_entries.cream_used_kg represents actual consumption while making ghee.
        # We treat the cream that was transferred to ghee (cream_used_ghee) as the
        # pool available for this module, minus what's already been used here.
        transferred_to_ghee = float(r["used_ghee_cream_module"])
        available = round(transferred_to_ghee - consumed_in_ghee_module, 3)

        return {
            "cream_produced":   round(produced, 3),
            "transferred_to_ghee": round(transferred_to_ghee, 3),
            "consumed_in_ghee": round(consumed_in_ghee_module, 3),
            "available_cream":  available
        }
    except sqlite3.Error as e:
        print(f"[get_available_cream_stock] {e}")
        return {"cream_produced":0,"transferred_to_ghee":0,
                "consumed_in_ghee":0,"available_cream":0}
    finally:
        if conn: conn.close()


# ==========================
# ADD GHEE ENTRY
# ==========================

def add_ghee_entry(entry_date, shift, cream_used_kg, ghee_produced,
                   packaged_qty, packet_size, ghee_sold,
                   ghee_distributed, ghee_wasted, batch_number,
                   employee_id, employee_name, notes):
    try:
        cream_used_kg    = float(cream_used_kg)    if cream_used_kg    else 0.0
        ghee_produced    = float(ghee_produced)    if ghee_produced    else 0.0
        packaged_qty     = float(packaged_qty)     if packaged_qty     else 0.0
        ghee_sold        = float(ghee_sold)        if ghee_sold        else 0.0
        ghee_distributed = float(ghee_distributed) if ghee_distributed else 0.0
        ghee_wasted      = float(ghee_wasted)      if ghee_wasted      else 0.0
    except (ValueError, TypeError):
        return False, "All numeric fields must be valid numbers."

    if not entry_date:
        return False, "Entry date is required."
    if cream_used_kg < 0 or ghee_produced < 0:
        return False, "Values cannot be negative."

    total_out = ghee_sold + ghee_distributed + ghee_wasted
    if total_out > ghee_produced:
        return False, (f"Total outgoing ghee ({total_out} Kg) exceeds "
                       f"ghee produced ({ghee_produced} Kg).")

    # check available cream stock
    stock = get_available_cream_stock()
    if cream_used_kg > stock["available_cream"]:
        return False, (f"Insufficient cream stock!\\n"
                       f"Available: {stock['available_cream']} Kg, "
                       f"Requested: {cream_used_kg} Kg")

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
            INSERT INTO ghee_entries
                (entry_date, shift, cream_used_kg, ghee_produced,
                 packaged_qty, packet_size, ghee_sold, ghee_distributed,
                 ghee_wasted, batch_number, employee_id, employee_name,
                 notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (entry_date, shift, cream_used_kg, ghee_produced,
              packaged_qty, packet_size, ghee_sold, ghee_distributed,
              ghee_wasted, batch_number, employee_id or None,
              employee_name, notes, now))

        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# GET ALL ENTRIES
# ==========================

def get_ghee_entries(date_from=None, date_to=None, shift=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT id, entry_date, shift, cream_used_kg, ghee_produced,
                   packaged_qty, packet_size, ghee_sold, ghee_distributed,
                   ghee_wasted, batch_number, employee_name, notes
            FROM ghee_entries WHERE 1=1
        """
        params = []
        if date_from:
            q += " AND entry_date >= ?"; params.append(date_from)
        if date_to:
            q += " AND entry_date <= ?"; params.append(date_to)
        if shift and shift != "All":
            q += " AND shift = ?"; params.append(shift)
        q += " ORDER BY entry_date DESC, id DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_ghee_entries] {e}"); return []
    finally:
        if conn: conn.close()


def get_ghee_entry_by_id(entry_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM ghee_entries WHERE id=?", (entry_id,))
        return c.fetchone()
    except sqlite3.Error as e:
        print(f"[get_ghee_entry_by_id] {e}"); return None
    finally:
        if conn: conn.close()


# ==========================
# UPDATE ENTRY
# ==========================

def update_ghee_entry(entry_id, entry_date, shift, cream_used_kg,
                      ghee_produced, packaged_qty, packet_size,
                      ghee_sold, ghee_distributed, ghee_wasted,
                      batch_number, employee_id, employee_name, notes):
    try:
        cream_used_kg    = float(cream_used_kg)    if cream_used_kg    else 0.0
        ghee_produced    = float(ghee_produced)    if ghee_produced    else 0.0
        packaged_qty     = float(packaged_qty)     if packaged_qty     else 0.0
        ghee_sold        = float(ghee_sold)        if ghee_sold        else 0.0
        ghee_distributed = float(ghee_distributed) if ghee_distributed else 0.0
        ghee_wasted      = float(ghee_wasted)      if ghee_wasted      else 0.0
    except:
        return False, "All numeric fields must be valid numbers."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM ghee_entries WHERE id=?", (entry_id,))
        if not c.fetchone():
            return False, f"No entry found with ID {entry_id}."
        c.execute("""
            UPDATE ghee_entries SET
                entry_date=?, shift=?, cream_used_kg=?, ghee_produced=?,
                packaged_qty=?, packet_size=?, ghee_sold=?,
                ghee_distributed=?, ghee_wasted=?, batch_number=?,
                employee_id=?, employee_name=?, notes=?
            WHERE id=?
        """, (entry_date, shift, cream_used_kg, ghee_produced,
              packaged_qty, packet_size, ghee_sold, ghee_distributed,
              ghee_wasted, batch_number, employee_id or None,
              employee_name, notes, entry_id))
        conn.commit()
        return True, "Entry updated successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# DELETE ENTRY
# ==========================

def delete_ghee_entry(entry_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM ghee_entries WHERE id=?", (entry_id,))
        if not c.fetchone():
            return False, f"No entry with ID {entry_id}."
        c.execute("DELETE FROM ghee_entries WHERE id=?", (entry_id,))
        conn.commit()
        return True, "Entry deleted successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# CURRENT GHEE STOCK
# ==========================

def get_current_ghee_stock():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT
                COALESCE(SUM(ghee_produced),    0) AS total_produced,
                COALESCE(SUM(ghee_sold),        0) AS total_sold,
                COALESCE(SUM(ghee_distributed), 0) AS total_distributed,
                COALESCE(SUM(ghee_wasted),      0) AS total_wasted,
                COALESCE(SUM(cream_used_kg),    0) AS total_cream_used
            FROM ghee_entries
        """)
        r = c.fetchone()
        produced = float(r["total_produced"])
        out      = (float(r["total_sold"]) + float(r["total_distributed"])
                    + float(r["total_wasted"]))
        return {
            "total_produced":    round(produced, 3),
            "total_sold":        round(float(r["total_sold"]), 3),
            "total_distributed": round(float(r["total_distributed"]), 3),
            "total_wasted":      round(float(r["total_wasted"]), 3),
            "total_cream_used":  round(float(r["total_cream_used"]), 3),
            "current_stock":     round(produced - out, 3)
        }
    except sqlite3.Error as e:
        print(f"[get_current_ghee_stock] {e}")
        return {"total_produced":0,"total_sold":0,"total_distributed":0,
                "total_wasted":0,"total_cream_used":0,"current_stock":0}
    finally:
        if conn: conn.close()


# ==========================
# SUMMARY STATS
# ==========================

def get_ghee_summary(date_from=None, date_to=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT
                COUNT(*)                            AS entries,
                COALESCE(SUM(cream_used_kg),     0) AS cream,
                COALESCE(SUM(ghee_produced),     0) AS ghee,
                COALESCE(SUM(packaged_qty),      0) AS packaged,
                COALESCE(SUM(ghee_sold),         0) AS sold,
                COALESCE(SUM(ghee_distributed),  0) AS distributed,
                COALESCE(SUM(ghee_wasted),       0) AS wasted
            FROM ghee_entries WHERE 1=1
        """
        params = []
        if date_from:
            q += " AND entry_date>=?"; params.append(date_from)
        if date_to:
            q += " AND entry_date<=?"; params.append(date_to)
        c.execute(q, params)
        r = c.fetchone()
        cream = float(r["cream"])
        ghee  = float(r["ghee"])
        return {
            "entries":     r["entries"],
            "cream":       round(cream, 2),
            "ghee":        round(ghee, 2),
            "packaged":    round(float(r["packaged"]), 2),
            "sold":        round(float(r["sold"]), 2),
            "distributed": round(float(r["distributed"]), 2),
            "wasted":      round(float(r["wasted"]), 2),
            "yield_pct":   round(ghee / cream * 100, 2) if cream > 0 else 0.0
        }
    except sqlite3.Error as e:
        print(f"[get_ghee_summary] {e}")
        return {"entries":0,"cream":0,"ghee":0,"packaged":0,
                "sold":0,"distributed":0,"wasted":0,"yield_pct":0}
    finally:
        if conn: conn.close()


def get_daily_ghee_data(days=30):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT entry_date,
                   SUM(cream_used_kg) AS cream,
                   SUM(ghee_produced) AS ghee
            FROM ghee_entries
            WHERE entry_date >= DATE('now', ?)
            GROUP BY entry_date
            ORDER BY entry_date ASC
        """, (f"-{days} days",))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_daily_ghee_data] {e}"); return []
    finally:
        if conn: conn.close()


def get_employees_list():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, role FROM employees ORDER BY name")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_employees_list] {e}"); return []
    finally:
        if conn: conn.close()