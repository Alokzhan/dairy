import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "dairy.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_next_available_id(conn, table_name):
    """Returns the lowest missing (gap) ID — reuses deleted IDs."""
    try:
        c = conn.cursor()
        c.execute(f"SELECT id FROM {table_name} ORDER BY id ASC")
        existing_ids = [row[0] for row in c.fetchall()]

        if not existing_ids:
            return 1

        for expected, actual in enumerate(existing_ids, start=1):
            if expected != actual:
                return expected

        return existing_ids[-1] + 1
    except sqlite3.Error as e:
        print(f"[get_next_available_id] {e}")
        return None


# ==========================
# ADD CUSTOMER
# ==========================

def add_customer(name, mobile, alt_mobile, address, village_city,
                 gst, aadhaar, customer_type, opening_balance, status):
    """
    Returns (True, customer_id) on success or (False, error_message).
    Reuses deleted IDs (gap-fill).
    """
    name   = name.strip()
    mobile = mobile.strip()

    if not name:
        return False, "Customer name cannot be empty."
    if not mobile.isdigit() or len(mobile) < 10:
        return False, "Mobile number must be at least 10 digits."
    if alt_mobile and (not alt_mobile.isdigit() or len(alt_mobile) < 10):
        return False, "Alternate mobile must be at least 10 digits."
    if not customer_type or customer_type == "Select Type":
        return False, "Please select a customer type."

    try:
        opening_balance = float(opening_balance) if opening_balance else 0.0
    except (ValueError, TypeError):
        return False, "Opening balance must be a valid number."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM customers WHERE mobile = ?",
            (mobile,)
        )
        if cursor.fetchone():
            return False, f"Customer with mobile '{mobile}' already exists."

        # ── Find gap ID to reuse deleted IDs ──
        new_id = get_next_available_id(conn, "customers")

        if new_id is not None:
            cursor.execute("""
                INSERT INTO customers
                    (id, name, mobile, alt_mobile, address, village_city,
                     gst, aadhaar, customer_type, opening_balance,
                     current_balance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id, name, mobile,
                alt_mobile.strip() if alt_mobile else "",
                address.strip(), village_city.strip(),
                gst.strip().upper() if gst else "",
                aadhaar.strip() if aadhaar else "",
                customer_type, opening_balance, opening_balance, status
            ))
        else:
            cursor.execute("""
                INSERT INTO customers
                    (name, mobile, alt_mobile, address, village_city,
                     gst, aadhaar, customer_type, opening_balance,
                     current_balance, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, mobile,
                alt_mobile.strip() if alt_mobile else "",
                address.strip(), village_city.strip(),
                gst.strip().upper() if gst else "",
                aadhaar.strip() if aadhaar else "",
                customer_type, opening_balance, opening_balance, status
            ))
            new_id = cursor.lastrowid

        conn.commit()
        return True, new_id

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL CUSTOMERS
# ==========================

def get_customers():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, alt_mobile, address,
                   village_city, gst, aadhaar, customer_type,
                   opening_balance, current_balance, status
            FROM customers ORDER BY id ASC
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customers] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_customer_by_id(customer_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, alt_mobile, address,
                   village_city, gst, aadhaar, customer_type,
                   opening_balance, current_balance, status
            FROM customers WHERE id = ?
        """, (customer_id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[get_customer_by_id] DB error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def search_customers_by_name(keyword):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, alt_mobile, address,
                   village_city, gst, aadhaar, customer_type,
                   opening_balance, current_balance, status
            FROM customers WHERE name LIKE ? ORDER BY name ASC
        """, (f"%{keyword.strip()}%",))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[search_customers_by_name] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def search_customer_by_mobile(mobile):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, alt_mobile, address,
                   village_city, gst, aadhaar, customer_type,
                   opening_balance, current_balance, status
            FROM customers WHERE mobile = ?
        """, (mobile.strip(),))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[search_customer_by_mobile] DB error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_customers_by_type(customer_type):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, alt_mobile, address,
                   village_city, gst, aadhaar, customer_type,
                   opening_balance, current_balance, status
            FROM customers WHERE customer_type = ? ORDER BY id ASC
        """, (customer_type,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customers_by_type] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_active_customers():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, mobile, current_balance
            FROM customers WHERE status = 'Active' ORDER BY name ASC
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_active_customers] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


# ==========================
# UPDATE CUSTOMER
# ==========================

def update_customer(customer_id, name, mobile, alt_mobile, address,
                    village_city, gst, aadhaar, customer_type,
                    opening_balance, status):
    name   = name.strip()
    mobile = mobile.strip()

    if not name:
        return False, "Customer name cannot be empty."
    if not mobile.isdigit() or len(mobile) < 10:
        return False, "Mobile number must be at least 10 digits."
    if alt_mobile and (not alt_mobile.isdigit() or len(alt_mobile) < 10):
        return False, "Alternate mobile must be at least 10 digits."

    try:
        opening_balance = float(opening_balance) if opening_balance else 0.0
    except (ValueError, TypeError):
        return False, "Opening balance must be a valid number."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
        if not cursor.fetchone():
            return False, f"No customer found with ID {customer_id}."

        cursor.execute(
            "SELECT id FROM customers WHERE mobile = ? AND id != ?",
            (mobile, customer_id)
        )
        if cursor.fetchone():
            return False, f"Mobile '{mobile}' is already used by another customer."

        cursor.execute("""
            UPDATE customers
            SET name=?, mobile=?, alt_mobile=?, address=?, village_city=?,
                gst=?, aadhaar=?, customer_type=?, opening_balance=?, status=?
            WHERE id = ?
        """, (
            name, mobile,
            alt_mobile.strip() if alt_mobile else "",
            address.strip(), village_city.strip(),
            gst.strip().upper() if gst else "",
            aadhaar.strip() if aadhaar else "",
            customer_type, opening_balance, status, customer_id
        ))

        conn.commit()
        return True, "Customer updated successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# DELETE CUSTOMER
# ==========================

def delete_customer(customer_id):
    """
    Deletes customer. The ID becomes a 'gap' and will be
    reused by the next add_customer() call.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"No customer found with ID {customer_id}."

        cname = row["name"]

        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return True, f"Customer '{cname}' deleted. ID {customer_id} will be reused for the next new customer."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# PURCHASE / PAYMENT HISTORY
# ==========================

def get_customer_purchase_history(customer_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.sale_date, p.name AS product_name,
                   s.quantity, p.unit, s.unit_price, s.total
            FROM sales s
            LEFT JOIN products p ON s.product_id = p.id
            WHERE s.customer_id = ?
            ORDER BY s.sale_date DESC
        """, (customer_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customer_purchase_history] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_customer_payment_history(customer_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, payment_date, amount, method, notes
            FROM payments WHERE customer_id = ?
            ORDER BY payment_date DESC
        """, (customer_id,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_customer_payment_history] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_customer_due(customer_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COALESCE(SUM(total), 0) FROM sales WHERE customer_id = ?",
            (customer_id,)
        )
        total_purchases = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?",
            (customer_id,)
        )
        total_paid = cursor.fetchone()[0]

        row = get_customer_by_id(customer_id)
        opening = float(row["opening_balance"]) if row else 0.0

        due = opening + float(total_purchases) - float(total_paid)
        return round(due, 2)

    except sqlite3.Error as e:
        print(f"[get_customer_due] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()


# ==========================
# STATS
# ==========================

def customer_count():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"[customer_count] DB error: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def total_due_all():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(current_balance), 0) FROM customers")
        result = cursor.fetchone()[0]
        return round(float(result), 2)
    except sqlite3.Error as e:
        print(f"[total_due_all] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()