import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "dairy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _reset_autoincrement_if_empty(cursor, table_name):
    """Table poori tarah khali hone par AUTOINCREMENT ko 1 se reset karta hai."""
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    if cursor.fetchone()[0] == 0:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table_name,))


# ==========================
# ENSURE TABLES
# ==========================

def ensure_incentive_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Cream/Ghee ke liye ₹ per Kg rate — single settings row (id=1)
        c.execute("""
            CREATE TABLE IF NOT EXISTS production_rates (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                cream_rate_per_kg REAL   NOT NULL DEFAULT 0,
                ghee_rate_per_kg  REAL   NOT NULL DEFAULT 0,
                updated_at        TEXT
            )
        """)
        c.execute("SELECT id FROM production_rates WHERE id=1")
        if not c.fetchone():
            c.execute("""
                INSERT INTO production_rates (id, cream_rate_per_kg, ghee_rate_per_kg, updated_at)
                VALUES (1, 0, 0, ?)
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

        # Har settlement/payment ka record — production_incentive_payments
        c.execute("""
            CREATE TABLE IF NOT EXISTS production_incentive_payments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id   INTEGER NOT NULL,
                employee_name TEXT    NOT NULL,
                cream_qty     REAL    DEFAULT 0,
                ghee_qty      REAL    DEFAULT 0,
                cream_rate    REAL    DEFAULT 0,
                ghee_rate     REAL    DEFAULT 0,
                amount        REAL    NOT NULL,
                payment_date  TEXT    NOT NULL,
                payment_mode  TEXT    DEFAULT 'Cash',
                notes         TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)

        conn.commit()
        print("✅ Production incentive tables ready.")
    except sqlite3.Error as e:
        print(f"[ensure_incentive_tables] {e}")
    finally:
        if conn: conn.close()


# ==========================
# RATE SETTINGS
# ==========================

def get_production_rates():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT cream_rate_per_kg, ghee_rate_per_kg FROM production_rates WHERE id=1")
        row = c.fetchone()
        if not row:
            return {"cream_rate_per_kg": 0.0, "ghee_rate_per_kg": 0.0}
        return {
            "cream_rate_per_kg": round(float(row["cream_rate_per_kg"]), 2),
            "ghee_rate_per_kg":  round(float(row["ghee_rate_per_kg"]), 2)
        }
    except sqlite3.Error as e:
        print(f"[get_production_rates] {e}")
        return {"cream_rate_per_kg": 0.0, "ghee_rate_per_kg": 0.0}
    finally:
        if conn: conn.close()


def set_production_rates(cream_rate_per_kg, ghee_rate_per_kg):
    try:
        cream_rate_per_kg = float(cream_rate_per_kg)
        ghee_rate_per_kg  = float(ghee_rate_per_kg)
        if cream_rate_per_kg < 0 or ghee_rate_per_kg < 0:
            return False, "Rates cannot be negative."
    except (ValueError, TypeError):
        return False, "Rates must be valid numbers."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            UPDATE production_rates
            SET cream_rate_per_kg=?, ghee_rate_per_kg=?, updated_at=?
            WHERE id=1
        """, (cream_rate_per_kg, ghee_rate_per_kg, now))
        conn.commit()
        return True, "Rates updated successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# EMPLOYEE-WISE PRODUCTION vs PAID (unpaid = produced - already paid)
# ==========================

def _employee_total_produced(cursor, employee_id):
    cursor.execute("""
        SELECT COALESCE(SUM(cream_kg),0) AS total
        FROM cream_entries WHERE employee_id=?
    """, (employee_id,))
    cream_total = float(cursor.fetchone()["total"])

    cursor.execute("""
        SELECT COALESCE(SUM(ghee_produced),0) AS total
        FROM ghee_entries WHERE employee_id=?
    """, (employee_id,))
    ghee_total = float(cursor.fetchone()["total"])

    return cream_total, ghee_total


def _employee_total_paid(cursor, employee_id):
    cursor.execute("""
        SELECT COALESCE(SUM(cream_qty),0) AS cream_paid,
               COALESCE(SUM(ghee_qty),0)  AS ghee_paid
        FROM production_incentive_payments WHERE employee_id=?
    """, (employee_id,))
    row = cursor.fetchone()
    return float(row["cream_paid"]), float(row["ghee_paid"])


def get_employee_incentive_status(employee_id):
    """
    Unpaid Cream = Total Cream Produced (all-time, this employee) - Total Cream already paid
    Unpaid Ghee  = Total Ghee Produced  (all-time, this employee) - Total Ghee already paid
    Amount Payable = Unpaid Cream x cream_rate + Unpaid Ghee x ghee_rate

    Ek baar payment record hone ke baad, agla calculation apne aap sirf
    naye (is se aage ke) production ko count karega — kyunki "paid" total
    bhi is hisaab me shamil ho jaata hai.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        cream_produced, ghee_produced = _employee_total_produced(c, employee_id)
        cream_paid, ghee_paid = _employee_total_paid(c, employee_id)

        unpaid_cream = round(max(0.0, cream_produced - cream_paid), 3)
        unpaid_ghee  = round(max(0.0, ghee_produced - ghee_paid), 3)

        rates = get_production_rates()
        amount_payable = round(
            unpaid_cream * rates["cream_rate_per_kg"] +
            unpaid_ghee  * rates["ghee_rate_per_kg"], 2
        )

        return {
            "cream_produced":   round(cream_produced, 3),
            "ghee_produced":    round(ghee_produced, 3),
            "cream_paid":       round(cream_paid, 3),
            "ghee_paid":        round(ghee_paid, 3),
            "unpaid_cream":     unpaid_cream,
            "unpaid_ghee":      unpaid_ghee,
            "cream_rate":       rates["cream_rate_per_kg"],
            "ghee_rate":        rates["ghee_rate_per_kg"],
            "amount_payable":   amount_payable,
        }
    except sqlite3.Error as e:
        print(f"[get_employee_incentive_status] {e}")
        return {"cream_produced":0,"ghee_produced":0,"cream_paid":0,"ghee_paid":0,
                "unpaid_cream":0,"unpaid_ghee":0,"cream_rate":0,"ghee_rate":0,
                "amount_payable":0}
    finally:
        if conn: conn.close()


def record_incentive_payment(employee_id, employee_name, payment_mode="Cash", notes=""):
    """
    Employee ka pura current 'unpaid' production settle karta hai (jitna
    is waqt due hai utna hi pay hota hai). Agli dafa sirf iske baad ka
    naya production hi unpaid dikhega.
    """
    if not employee_id:
        return False, "Please select an employee."

    status = get_employee_incentive_status(employee_id)
    if status["unpaid_cream"] <= 0 and status["unpaid_ghee"] <= 0:
        return False, "Nothing pending — this employee has no unpaid production."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO production_incentive_payments
                (employee_id, employee_name, cream_qty, ghee_qty,
                 cream_rate, ghee_rate, amount, payment_date, payment_mode, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (employee_id, employee_name,
              status["unpaid_cream"], status["unpaid_ghee"],
              status["cream_rate"], status["ghee_rate"],
              status["amount_payable"], now, payment_mode, notes))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


def get_incentive_payment_history(date_from=None, date_to=None, employee_id=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = "SELECT * FROM production_incentive_payments WHERE 1=1"
        params = []
        if date_from:
            q += " AND DATE(payment_date) >= ?"; params.append(date_from)
        if date_to:
            q += " AND DATE(payment_date) <= ?"; params.append(date_to)
        if employee_id:
            q += " AND employee_id = ?"; params.append(employee_id)
        q += " ORDER BY payment_date DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_incentive_payment_history] {e}"); return []
    finally:
        if conn: conn.close()


def delete_incentive_payment(payment_id):
    """
    Payment delete karne se koi manual balance revert nahi karna padta —
    kyunki unpaid quantity hamesha (Total Produced - Total Paid) se derive
    hoti hai, delete hote hi wo quantity apne aap wapas 'unpaid' dikh jaayegi.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM production_incentive_payments WHERE id=?", (payment_id,))
        if not c.fetchone():
            return False, f"No payment found with ID {payment_id}."
        c.execute("DELETE FROM production_incentive_payments WHERE id=?", (payment_id,))
        _reset_autoincrement_if_empty(c, "production_incentive_payments")
        conn.commit()
        return True, "Incentive payment deleted; that quantity is unpaid again."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# DROPDOWN / OVERVIEW HELPERS
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


def get_all_employees_incentive_overview():
    """
    Sirf un employees ki list jinka cream/ghee production record maujood
    hai, unke unpaid amounts ke saath — ek quick overview ke liye.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT employee_id, employee_name FROM cream_entries
            WHERE employee_id IS NOT NULL
            UNION
            SELECT DISTINCT employee_id, employee_name FROM ghee_entries
            WHERE employee_id IS NOT NULL
        """)
        rows = c.fetchall()
        overview = []
        for r in rows:
            status = get_employee_incentive_status(r["employee_id"])
            overview.append({
                "employee_id": r["employee_id"],
                "employee_name": r["employee_name"],
                **status
            })
        overview.sort(key=lambda x: x["amount_payable"], reverse=True)
        return overview
    except sqlite3.Error as e:
        print(f"[get_all_employees_incentive_overview] {e}"); return []
    finally:
        if conn: conn.close()