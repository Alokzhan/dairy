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


# ==========================
# ENSURE TABLES
# ==========================

def ensure_payment_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Generic payments ledger — covers salary, distributor, misc payments
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

        c.execute("""
            CREATE TABLE IF NOT EXISTS distributor_payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                distributor_id  INTEGER NOT NULL,
                distributor_name TEXT   NOT NULL,
                amount          REAL    NOT NULL,
                payment_type    TEXT    DEFAULT 'Payment Made',
                payment_date    TEXT    NOT NULL,
                payment_mode    TEXT    DEFAULT 'Cash',
                notes           TEXT,
                FOREIGN KEY (distributor_id) REFERENCES distributors(id)
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
        conn.commit()
        return True, "Salary payment record deleted."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


def get_employee_salary_status(employee_id):
    """Returns total salary, total paid, balance due for this employee."""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT salary FROM employees WHERE id=?", (employee_id,))
        row = c.fetchone()
        monthly_salary = float(row["salary"]) if row else 0.0

        c.execute("""
            SELECT COALESCE(SUM(amount),0) FROM salary_payments
            WHERE employee_id=? AND strftime('%Y-%m', payment_date) = strftime('%Y-%m','now')
        """, (employee_id,))
        paid_this_month = float(c.fetchone()[0])

        return {
            "monthly_salary": round(monthly_salary, 2),
            "paid_this_month": round(paid_this_month, 2),
            "balance": round(monthly_salary - paid_this_month, 2)
        }
    except sqlite3.Error as e:
        print(f"[get_employee_salary_status] {e}")
        return {"monthly_salary":0,"paid_this_month":0,"balance":0}
    finally:
        if conn: conn.close()


# ==========================
# DISTRIBUTOR PAYMENTS
# ==========================

def record_distributor_payment(distributor_id, distributor_name, amount,
                               payment_type, payment_mode, notes=""):
    try:
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be greater than 0."
    except (ValueError, TypeError):
        return False, "Invalid amount."

    if not distributor_id:
        return False, "Please select a distributor."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO distributor_payments
                (distributor_id, distributor_name, amount,
                 payment_type, payment_date, payment_mode, notes)
            VALUES (?,?,?,?,?,?,?)
        """, (distributor_id, distributor_name, amount,
              payment_type, now, payment_mode, notes))

        # update distributor balance:
        # "Payment Made" reduces what we owe them (-),
        # "Payment Received" increases what we owe them (+) [rare, e.g. refund]
        delta = -amount if payment_type == "Payment Made" else amount
        c.execute("""
            UPDATE distributors SET balance = balance + ? WHERE id=?
        """, (delta, distributor_id))

        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


def get_distributor_payments(date_from=None, date_to=None, distributor_id=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = "SELECT * FROM distributor_payments WHERE 1=1"
        params = []
        if date_from:
            q += " AND DATE(payment_date) >= ?"; params.append(date_from)
        if date_to:
            q += " AND DATE(payment_date) <= ?"; params.append(date_to)
        if distributor_id:
            q += " AND distributor_id = ?"; params.append(distributor_id)
        q += " ORDER BY payment_date DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_distributor_payments] {e}"); return []
    finally:
        if conn: conn.close()


def delete_distributor_payment(payment_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT distributor_id, amount, payment_type FROM distributor_payments WHERE id=?",
                  (payment_id,))
        row = c.fetchone()
        if not row:
            return False, f"No payment found with ID {payment_id}."

        # reverse the balance change
        delta = row["amount"] if row["payment_type"] == "Payment Made" else -row["amount"]
        c.execute("UPDATE distributors SET balance = balance + ? WHERE id=?",
                  (delta, row["distributor_id"]))

        c.execute("DELETE FROM distributor_payments WHERE id=?", (payment_id,))
        conn.commit()
        return True, "Distributor payment record deleted and balance reversed."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
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


def get_distributors_for_payment():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, phone, balance FROM distributors ORDER BY name")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_distributors_for_payment] {e}"); return []
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

        # distributor balance owed (positive = we owe them)
        c.execute("SELECT COALESCE(SUM(balance),0) FROM distributors WHERE balance > 0")
        distributor_owed = float(c.fetchone()[0])

        return {
            "collected_today":     round(collected_today, 2),
            "total_customer_due":  round(total_customer_due, 2),
            "salary_paid_month":   round(salary_paid_month, 2),
            "distributor_owed":    round(distributor_owed, 2)
        }
    except sqlite3.Error as e:
        print(f"[get_payment_dashboard_summary] {e}")
        return {"collected_today":0,"total_customer_due":0,
                "salary_paid_month":0,"distributor_owed":0}
    finally:
        if conn: conn.close()