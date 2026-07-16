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
    """
    Agar table ke sab records delete ho chuke hain, to sqlite_sequence
    se us table ki entry hata do — taaki agla INSERT ID=1 se shuru ho,
    AUTOINCREMENT ke purane high-water-mark se continue na kare.
    Sirf pura table khali hone par hi reset hota hai; agar beech ke
    kisi ek record ko delete kiya gaya ho (aur baaki records maujood
    hain), to koi reset nahi hota — audit trail ke liye baaki IDs
    stable rehte hain.
    """
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    if cursor.fetchone()[0] == 0:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table_name,))


# ==========================
# ENSURE TABLES
# ==========================

def ensure_payment_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Generic payments ledger — covers salary and misc payments
        # (customer payments already exist via bills/payments tables from Sales module)
        c.execute("""
            CREATE TABLE IF NOT EXISTS salary_payments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id   INTEGER NOT NULL,
                employee_name TEXT    NOT NULL,
                amount        REAL    NOT NULL,
                pay_period    TEXT,
                payment_date  TEXT    NOT NULL,
                payment_mode  TEXT    DEFAULT 'Cash',
                notes         TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        """)

        conn.commit()
        print("✅ Payment tables ready.")
    except sqlite3.Error as e:
        print(f"[ensure_payment_tables] {e}")
    finally:
        if conn: conn.close()


# ==========================
# CUSTOMER PAYMENTS (read from existing payments table — populated by Sales module)
# ==========================

def get_customer_payments(date_from=None, date_to=None, search=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT p.id, p.payment_date, p.amount, p.method, p.notes,
                   c.name AS customer_name, c.mobile AS customer_mobile
            FROM payments p
            LEFT JOIN customers c ON p.customer_id = c.id
            WHERE 1=1
        """
        params = []
        if date_from:
            q += " AND DATE(p.payment_date) >= ?"; params.append(date_from)
        if date_to:
            q += " AND DATE(p.payment_date) <= ?"; params.append(date_to)
        if search:
            q += " AND c.name LIKE ?"; params.append(f"%{search}%")
        q += " ORDER BY p.payment_date DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customer_payments] {e}"); return []
    finally:
        if conn: conn.close()


def get_customer_dues_summary():
    """All customers currently having outstanding balance."""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, name, mobile, current_balance
            FROM customers
            WHERE current_balance > 0
            ORDER BY current_balance DESC
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customer_dues_summary] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# SALARY PAYMENTS
# ==========================

def record_salary_payment(employee_id, employee_name, amount,
                          pay_period, payment_mode, notes=""):
    try:
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be greater than 0."
    except (ValueError, TypeError):
        return False, "Invalid amount."

    if not employee_id:
        return False, "Please select an employee."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO salary_payments
                (employee_id, employee_name, amount, pay_period,
                 payment_date, payment_mode, notes)
            VALUES (?,?,?,?,?,?,?)
        """, (employee_id, employee_name, amount, pay_period,
              now, payment_mode, notes))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


def get_salary_payments(date_from=None, date_to=None, employee_id=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = "SELECT * FROM salary_payments WHERE 1=1"
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
        print(f"[get_salary_payments] {e}"); return []
    finally:
        if conn: conn.close()


def delete_salary_payment(payment_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM salary_payments WHERE id=?", (payment_id,))
        if not c.fetchone():
            return False, f"No payment found with ID {payment_id}."
        c.execute("DELETE FROM salary_payments WHERE id=?", (payment_id,))
        _reset_autoincrement_if_empty(c, "salary_payments")
        conn.commit()
        return True, "Salary payment record deleted."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


def _fetch_monthly_period_totals(cursor, employee_id):
    """
    Employee ke sab salary_payments ko (year-month, pay_period) ke
    hisaab se group karke ek nested dict banata hai:
        { "2026-07": {"This Month": 70000, "Advance": 0, ...}, ... }
    Isi ek query se current-month aur ledger dono banate hain.
    """
    cursor.execute("""
        SELECT strftime('%Y-%m', payment_date) AS ym,
               pay_period, COALESCE(SUM(amount),0) AS total
        FROM salary_payments
        WHERE employee_id=?
        GROUP BY ym, pay_period
        ORDER BY ym
    """, (employee_id,))

    by_month = {}
    for r in cursor.fetchall():
        ym = r["ym"]
        period = r["pay_period"] or "Other"
        if period not in ("This Month", "Advance", "Arrears", "Bonus"):
            period = "Other"
        by_month.setdefault(ym, {"This Month": 0.0, "Advance": 0.0,
                                  "Arrears": 0.0, "Bonus": 0.0, "Other": 0.0})
        by_month[ym][period] += float(r["total"])
    return by_month


def get_employee_salary_status(employee_id):
    """
    Professional payroll logic:

    - Advance us mahine ki salary ko turant reduce karta hai jis mahine
      me wo record kiya gaya ho (This Month + Advance dono current month
      ki salary ko cover karte hain).
    - Arrears kabhi bhi current month ya Bonus se mix nahi hota — wo
      sirf purane (pichhle) mahino ke accumulated unpaid due ko clear
      karta hai.
    - Bonus fully independent hai — Salary Due, Advance ya Arrear pe
      koi asar nahi dalta.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT salary FROM employees WHERE id=?", (employee_id,))
        row = c.fetchone()
        monthly_salary = float(row["salary"]) if row else 0.0

        by_month = _fetch_monthly_period_totals(c, employee_id)
        current_ym = datetime.now().strftime("%Y-%m")
        cur = by_month.get(current_ym, {"This Month": 0.0, "Advance": 0.0,
                                         "Arrears": 0.0, "Bonus": 0.0, "Other": 0.0})

        this_month_paid = cur["This Month"]
        advance_paid    = cur["Advance"]
        bonus_paid      = cur["Bonus"]
        other_paid      = cur["Other"]

        # This month's salary due = monthly salary minus (This Month + Advance)
        # paid in this same month. Can go negative if overpaid.
        remaining_this_month = round(monthly_salary - this_month_paid - advance_paid, 2)

        # Old due accumulated from every earlier month that has payment
        # history (This Month + Advance paid in that month vs that
        # month's salary), clamped at 0 per month so an overpaid month
        # doesn't wipe out dues from other months.
        old_due_accumulated = 0.0
        arrears_paid_total = 0.0
        for ym, totals in by_month.items():
            arrears_paid_total += totals["Arrears"]
            if ym < current_ym:
                month_covered = totals["This Month"] + totals["Advance"]
                month_due = monthly_salary - month_covered
                if month_due > 0:
                    old_due_accumulated += month_due

        old_due_remaining = round(max(0.0, old_due_accumulated - arrears_paid_total), 2)

        # Total outstanding = unresolved old due + this month's unpaid portion
        # (only the positive/unpaid portion counts toward balance; an
        # overpayment this month is not auto-adjusted against old due).
        balance = round(old_due_remaining + max(0.0, remaining_this_month), 2)

        return {
            "monthly_salary":        round(monthly_salary, 2),
            "paid_this_month":       round(this_month_paid, 2),
            "advance_paid":          round(advance_paid, 2),
            "remaining_this_month":  remaining_this_month,
            "bonus_paid":            round(bonus_paid, 2),
            "other_paid":            round(other_paid, 2),
            "old_due_remaining":     old_due_remaining,
            "arrears_paid_total":    round(arrears_paid_total, 2),
            "balance":               balance,
        }
    except sqlite3.Error as e:
        print(f"[get_employee_salary_status] {e}")
        return {"monthly_salary":0,"paid_this_month":0,"advance_paid":0,
                "remaining_this_month":0,"bonus_paid":0,"other_paid":0,
                "old_due_remaining":0,"arrears_paid_total":0,"balance":0}
    finally:
        if conn: conn.close()


def get_employee_salary_ledger(employee_id):
    """
    Month-wise salary ledger — har mahine ke liye salary, paid
    (This Month + Advance), Arrears, Bonus aur us mahine ka balance
    alag-alag dikhata hai. Har mahina independently calculate hota hai
    (requirement #5 — Monthly Salary Ledger).
    Returns a list of dicts ordered oldest → newest.
    """
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT salary FROM employees WHERE id=?", (employee_id,))
        row = c.fetchone()
        monthly_salary = float(row["salary"]) if row else 0.0

        by_month = _fetch_monthly_period_totals(c, employee_id)

        ledger = []
        for ym in sorted(by_month.keys()):
            totals = by_month[ym]
            covered = totals["This Month"] + totals["Advance"]
            ledger.append({
                "month":            ym,
                "monthly_salary":   round(monthly_salary, 2),
                "this_month_paid":  round(totals["This Month"], 2),
                "advance_paid":     round(totals["Advance"], 2),
                "arrears_paid":     round(totals["Arrears"], 2),
                "bonus_paid":       round(totals["Bonus"], 2),
                "balance":          round(monthly_salary - covered, 2),
            })
        return ledger
    except sqlite3.Error as e:
        print(f"[get_employee_salary_ledger] {e}")
        return []
    finally:
        if conn: conn.close()


# ==========================
# DROPDOWN HELPERS
# ==========================

def get_employees_for_payment():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, role, salary FROM employees ORDER BY name")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_employees_for_payment] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# DASHBOARD SUMMARY
# ==========================

def get_payment_dashboard_summary():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # customer collections today
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("""
            SELECT COALESCE(SUM(amount),0) FROM payments
            WHERE DATE(payment_date) = ?
        """, (today,))
        collected_today = float(c.fetchone()[0])

        # total customer dues outstanding
        c.execute("SELECT COALESCE(SUM(current_balance),0) FROM customers WHERE current_balance > 0")
        total_customer_due = float(c.fetchone()[0])

        # salary paid this month
        c.execute("""
            SELECT COALESCE(SUM(amount),0) FROM salary_payments
            WHERE strftime('%Y-%m', payment_date) = strftime('%Y-%m','now')
        """)
        salary_paid_month = float(c.fetchone()[0])

        return {
            "collected_today":     round(collected_today, 2),
            "total_customer_due":  round(total_customer_due, 2),
            "salary_paid_month":   round(salary_paid_month, 2),
        }
    except sqlite3.Error as e:
        print(f"[get_payment_dashboard_summary] {e}")
        return {"collected_today":0,"total_customer_due":0,
                "salary_paid_month":0}
    finally:
        if conn: conn.close()