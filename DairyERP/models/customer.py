import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "dairy.db")




# ==========================
# DB CONNECTION HELPER
# ==========================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================
# ADD CUSTOMER
# ==========================

def add_customer(name, mobile, alt_mobile, address, village_city,
                 gst, aadhaar, customer_type, opening_balance, status):
    """
    Returns (True, customer_id) on success or (False, error_message).
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

        # duplicate mobile check
        cursor.execute(
            "SELECT id FROM customers WHERE mobile = ?",
            (mobile,)
        )
        if cursor.fetchone():
            return False, f"Customer with mobile '{mobile}' already exists."

        cursor.execute("""
            INSERT INTO customers
                (name, mobile, alt_mobile, address, village_city,
                 gst, aadhaar, customer_type, opening_balance,
                 current_balance, status)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            mobile,
            alt_mobile.strip() if alt_mobile else "",
            address.strip(),
            village_city.strip(),
            gst.strip().upper() if gst else "",
            aadhaar.strip() if aadhaar else "",
            customer_type,
            opening_balance,
            opening_balance,   # current_balance starts same as opening
            status
        ))

        conn.commit()
        return True, cursor.lastrowid

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL CUSTOMERS
# ==========================

def get_customers():
    """Return all customers ordered by name."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, mobile, alt_mobile, address,
                village_city, gst, aadhaar, customer_type,
                opening_balance, current_balance, status
            FROM customers
            ORDER BY name ASC
        """)

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_customers] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# GET CUSTOMER BY ID
# ==========================

def get_customer_by_id(customer_id):
    """Return one customer row by ID, or None."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, mobile, alt_mobile, address,
                village_city, gst, aadhaar, customer_type,
                opening_balance, current_balance, status
            FROM customers
            WHERE id = ?
        """, (customer_id,))

        return cursor.fetchone()

    except sqlite3.Error as e:
        print(f"[get_customer_by_id] DB error: {e}")
        return None

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH CUSTOMER BY NAME
# ==========================

def search_customers_by_name(keyword):
    """Case-insensitive partial name search."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, mobile, alt_mobile, address,
                village_city, gst, aadhaar, customer_type,
                opening_balance, current_balance, status
            FROM customers
            WHERE name LIKE ?
            ORDER BY name ASC
        """, (f"%{keyword.strip()}%",))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[search_customers_by_name] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH BY MOBILE
# ==========================

def search_customer_by_mobile(mobile):
    """Exact mobile number search."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, mobile, alt_mobile, address,
                village_city, gst, aadhaar, customer_type,
                opening_balance, current_balance, status
            FROM customers
            WHERE mobile = ?
        """, (mobile.strip(),))

        return cursor.fetchone()

    except sqlite3.Error as e:
        print(f"[search_customer_by_mobile] DB error: {e}")
        return None

    finally:
        if conn:
            conn.close()


# ==========================
# GET BY TYPE
# ==========================

def get_customers_by_type(customer_type):
    """Filter customers by type (Retail, Wholesale, etc.)."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, mobile, alt_mobile, address,
                village_city, gst, aadhaar, customer_type,
                opening_balance, current_balance, status
            FROM customers
            WHERE customer_type = ?
            ORDER BY name ASC
        """, (customer_type,))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_customers_by_type] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# GET ACTIVE CUSTOMERS
# ==========================

def get_active_customers():
    """Return only Active customers (for dropdowns in Sales/Payments)."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, mobile, current_balance
            FROM customers
            WHERE status = 'Active'
            ORDER BY name ASC
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
    """
    Returns (True, "Updated successfully") or (False, error_message).
    """
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

        cursor.execute(
            "SELECT id FROM customers WHERE id = ?",
            (customer_id,)
        )
        if not cursor.fetchone():
            return False, f"No customer found with ID {customer_id}."

        # mobile conflict with another customer
        cursor.execute(
            "SELECT id FROM customers WHERE mobile = ? AND id != ?",
            (mobile, customer_id)
        )
        if cursor.fetchone():
            return False, f"Mobile '{mobile}' is already used by another customer."

        cursor.execute("""
            UPDATE customers
            SET
                name            = ?,
                mobile          = ?,
                alt_mobile      = ?,
                address         = ?,
                village_city    = ?,
                gst             = ?,
                aadhaar         = ?,
                customer_type   = ?,
                opening_balance = ?,
                status          = ?
            WHERE id = ?
        """, (
            name, mobile,
            alt_mobile.strip() if alt_mobile else "",
            address.strip(),
            village_city.strip(),
            gst.strip().upper() if gst else "",
            aadhaar.strip() if aadhaar else "",
            customer_type,
            opening_balance,
            status,
            customer_id
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
    Returns (True, message) or (False, error_message).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM customers WHERE id = ?",
            (customer_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False, f"No customer found with ID {customer_id}."

        cname = row["name"]

        cursor.execute(
            "DELETE FROM customers WHERE id = ?",
            (customer_id,)
        )
        conn.commit()
        return True, f"Customer '{cname}' deleted successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# CUSTOMER PURCHASE HISTORY
# ==========================

def get_customer_purchase_history(customer_id):
    """
    Returns all sales records for a customer,
    joined with product name.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                s.id,
                s.sale_date,
                p.name      AS product_name,
                s.quantity,
                p.unit,
                s.unit_price,
                s.total
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


# ==========================
# CUSTOMER PAYMENT HISTORY
# ==========================

def get_customer_payment_history(customer_id):
    """Returns all payment records for a customer."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                payment_date,
                amount,
                method,
                notes
            FROM payments
            WHERE customer_id = ?
            ORDER BY payment_date DESC
        """, (customer_id,))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_customer_payment_history] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# CUSTOMER DUE AMOUNT
# ==========================

def get_customer_due(customer_id):
    """
    Due = total purchases - total payments.
    Returns float.
    """
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
    """Sum of current_balance across all customers (total receivable)."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(current_balance), 0) FROM customers"
        )
        result = cursor.fetchone()[0]
        return round(float(result), 2)
    except sqlite3.Error as e:
        print(f"[total_due_all] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()