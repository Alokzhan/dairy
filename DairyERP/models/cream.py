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

def ensure_cream_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS cream_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date      TEXT    NOT NULL,
                shift           TEXT    DEFAULT 'Morning',
                milk_litres     REAL    DEFAULT 0,
                fat_percent     REAL    DEFAULT 0,
                cream_kg        REAL    DEFAULT 0,
                cream_used_ghee REAL    DEFAULT 0,
                cream_sold      REAL    DEFAULT 0,
                cream_wasted    REAL    DEFAULT 0,
                supplier_name   TEXT,
                employee_id     INTEGER,
                employee_name   TEXT,
                notes           TEXT,
                created_at      TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS cream_stock (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT    NOT NULL,
                opening_kg   REAL    DEFAULT 0,
                received_kg  REAL    DEFAULT 0,
                used_ghee_kg REAL    DEFAULT 0,
                sold_kg      REAL    DEFAULT 0,
                wasted_kg    REAL    DEFAULT 0,
                closing_kg   REAL    DEFAULT 0,
                notes        TEXT
            )
        """)

        conn.commit()
        print("✅ Cream tables ready.")
    except sqlite3.Error as e:
        print(f"[ensure_cream_tables] {e}")
    finally:
        if conn: conn.close()


# ==========================
# ADD CREAM ENTRY
# ==========================

def add_cream_entry(entry_date, shift, milk_litres, fat_percent,
                    cream_kg, cream_used_ghee, cream_sold,
                    cream_wasted, supplier_name, employee_id,
                    employee_name, notes):
    try:
        milk_litres     = float(milk_litres)     if milk_litres     else 0.0
        fat_percent     = float(fat_percent)     if fat_percent     else 0.0
        cream_kg        = float(cream_kg)        if cream_kg        else 0.0
        cream_used_ghee = float(cream_used_ghee) if cream_used_ghee else 0.0
        cream_sold      = float(cream_sold)      if cream_sold      else 0.0
        cream_wasted    = float(cream_wasted)    if cream_wasted    else 0.0
    except (ValueError, TypeError):
        return False, "All numeric fields must be valid numbers."

    if not entry_date:
        return False, "Entry date is required."
    if cream_kg < 0 or milk_litres < 0:
        return False, "Values cannot be negative."
    total_out = cream_used_ghee + cream_sold + cream_wasted
    if total_out > cream_kg:
        return False, (f"Total outgoing cream ({total_out} Kg) exceeds "
                       f"cream produced ({cream_kg} Kg).")

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
            INSERT INTO cream_entries
                (entry_date, shift, milk_litres, fat_percent, cream_kg,
                 cream_used_ghee, cream_sold, cream_wasted,
                 supplier_name, employee_id, employee_name, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (entry_date, shift, milk_litres, fat_percent, cream_kg,
              cream_used_ghee, cream_sold, cream_wasted,
              supplier_name, employee_id or None, employee_name, notes, now))

        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# GET ALL ENTRIES
# ==========================

def get_cream_entries(date_from=None, date_to=None, shift=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT id, entry_date, shift, milk_litres, fat_percent,
                   cream_kg, cream_used_ghee, cream_sold, cream_wasted,
                   supplier_name, employee_name, notes
            FROM cream_entries WHERE 1=1
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
        print(f"[get_cream_entries] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# GET ENTRY BY ID
# ==========================

def get_cream_entry_by_id(entry_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM cream_entries WHERE id=?", (entry_id,))
        return c.fetchone()
    except sqlite3.Error as e:
        print(f"[get_cream_entry_by_id] {e}"); return None
    finally:
        if conn: conn.close()


# ==========================
# UPDATE ENTRY
# ==========================

def update_cream_entry(entry_id, entry_date, shift, milk_litres,
                       fat_percent, cream_kg, cream_used_ghee,
                       cream_sold, cream_wasted, supplier_name,
                       employee_id, employee_name, notes):
    try:
        milk_litres     = float(milk_litres)     if milk_litres     else 0.0
        fat_percent     = float(fat_percent)     if fat_percent     else 0.0
        cream_kg        = float(cream_kg)        if cream_kg        else 0.0
        cream_used_ghee = float(cream_used_ghee) if cream_used_ghee else 0.0
        cream_sold      = float(cream_sold)      if cream_sold      else 0.0
        cream_wasted    = float(cream_wasted)    if cream_wasted    else 0.0
    except:
        return False, "All numeric fields must be valid numbers."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM cream_entries WHERE id=?", (entry_id,))
        if not c.fetchone():
            return False, f"No entry found with ID {entry_id}."
        c.execute("""
            UPDATE cream_entries SET
                entry_date=?, shift=?, milk_litres=?, fat_percent=?,
                cream_kg=?, cream_used_ghee=?, cream_sold=?, cream_wasted=?,
                supplier_name=?, employee_id=?, employee_name=?, notes=?
            WHERE id=?
        """, (entry_date, shift, milk_litres, fat_percent, cream_kg,
              cream_used_ghee, cream_sold, cream_wasted,
              supplier_name, employee_id or None, employee_name,
              notes, entry_id))
        conn.commit()
        return True, "Entry updated successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# DELETE ENTRY
# ==========================

def delete_cream_entry(entry_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM cream_entries WHERE id=?", (entry_id,))
        if not c.fetchone():
            return False, f"No entry with ID {entry_id}."
        c.execute("DELETE FROM cream_entries WHERE id=?", (entry_id,))
        conn.commit()
        return True, "Entry deleted successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# CURRENT CREAM STOCK
# ==========================

def get_current_cream_stock():
    """
    Stock = total cream produced
            - total used for ghee
            - total sold
            - total wasted
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT
                COALESCE(SUM(cream_kg),        0) AS total_produced,
                COALESCE(SUM(cream_used_ghee), 0) AS total_ghee,
                COALESCE(SUM(cream_sold),      0) AS total_sold,
                COALESCE(SUM(cream_wasted),    0) AS total_wasted
            FROM cream_entries
        """)
        r = c.fetchone()
        produced = float(r["total_produced"])
        used_out = float(r["total_ghee"]) + float(r["total_sold"]) + float(r["total_wasted"])
        return {
            "total_produced": round(produced, 3),
            "total_ghee":     round(float(r["total_ghee"]), 3),
            "total_sold":     round(float(r["total_sold"]), 3),
            "total_wasted":   round(float(r["total_wasted"]), 3),
            "current_stock":  round(produced - used_out, 3)
        }
    except sqlite3.Error as e:
        print(f"[get_current_cream_stock] {e}")
        return {"total_produced":0,"total_ghee":0,"total_sold":0,
                "total_wasted":0,"current_stock":0}
    finally:
        if conn: conn.close()


# ==========================
# SUMMARY STATS
# ==========================

def get_cream_summary(date_from=None, date_to=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT
                COUNT(*)                       AS entries,
                COALESCE(SUM(milk_litres),  0) AS milk,
                COALESCE(SUM(cream_kg),     0) AS cream,
                COALESCE(SUM(cream_used_ghee),0) AS ghee,
                COALESCE(SUM(cream_sold),   0) AS sold,
                COALESCE(SUM(cream_wasted), 0) AS wasted,
                COALESCE(AVG(fat_percent),  0) AS avg_fat
            FROM cream_entries WHERE 1=1
        """
        params = []
        if date_from:
            q += " AND entry_date>=?"; params.append(date_from)
        if date_to:
            q += " AND entry_date<=?"; params.append(date_to)
        c.execute(q, params)
        r = c.fetchone()
        return {
            "entries":   r["entries"],
            "milk":      round(float(r["milk"]),  2),
            "cream":     round(float(r["cream"]), 2),
            "ghee":      round(float(r["ghee"]),  2),
            "sold":      round(float(r["sold"]),   2),
            "wasted":    round(float(r["wasted"]), 2),
            "avg_fat":   round(float(r["avg_fat"]), 2),
            "yield_pct": round(float(r["cream"]) / float(r["milk"]) * 100, 2)
                         if float(r["milk"]) > 0 else 0.0
        }
    except sqlite3.Error as e:
        print(f"[get_cream_summary] {e}")
        return {"entries":0,"milk":0,"cream":0,"ghee":0,
                "sold":0,"wasted":0,"avg_fat":0,"yield_pct":0}
    finally:
        if conn: conn.close()


# ==========================
# DAILY PRODUCTION CHART DATA
# ==========================

def get_daily_cream_data(days=30):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT entry_date,
                   SUM(milk_litres) AS milk,
                   SUM(cream_kg)    AS cream
            FROM cream_entries
            WHERE entry_date >= DATE('now', ?)
            GROUP BY entry_date
            ORDER BY entry_date ASC
        """, (f"-{days} days",))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_daily_cream_data] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# GET EMPLOYEES FOR DROPDOWN
# ==========================

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