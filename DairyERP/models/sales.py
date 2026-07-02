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
# ENSURE SALES TABLES
# ==========================

def ensure_sales_tables():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Main bills table
        c.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT    NOT NULL UNIQUE,
                customer_id    INTEGER,
                customer_name  TEXT    NOT NULL,
                customer_mobile TEXT,
                bill_date      TEXT    NOT NULL,
                subtotal       REAL    DEFAULT 0,
                discount       REAL    DEFAULT 0,
                discount_type  TEXT    DEFAULT 'flat',
                gst_percent    REAL    DEFAULT 0,
                gst_amount     REAL    DEFAULT 0,
                grand_total    REAL    DEFAULT 0,
                paid_amount    REAL    DEFAULT 0,
                due_amount     REAL    DEFAULT 0,
                payment_mode   TEXT    DEFAULT 'Cash',
                status         TEXT    DEFAULT 'Paid',
                notes          TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Bill items table
        c.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id     INTEGER NOT NULL,
                product_id  INTEGER,
                product_name TEXT   NOT NULL,
                category    TEXT,
                unit        TEXT,
                quantity    REAL    NOT NULL,
                unit_price  REAL    NOT NULL,
                discount    REAL    DEFAULT 0,
                total       REAL    NOT NULL,
                FOREIGN KEY (bill_id)    REFERENCES bills(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        conn.commit()
    except sqlite3.Error as e:
        print(f"[ensure_sales_tables] {e}")
    finally:
        if conn: conn.close()


# ==========================
# GENERATE INVOICE NUMBER
# ==========================

def generate_invoice_number():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        today = datetime.now().strftime("%Y%m%d")
        c.execute("""
            SELECT COUNT(*) FROM bills
            WHERE invoice_number LIKE ?
        """, (f"INV-{today}-%",))
        count = c.fetchone()[0] + 1
        return f"INV-{today}-{count:04d}"
    except sqlite3.Error as e:
        print(f"[generate_invoice_number] {e}")
        return f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    finally:
        if conn: conn.close()


# ==========================
# CREATE BILL
# ==========================

def create_bill(customer_id, customer_name, customer_mobile,
                cart_items, discount, discount_type,
                gst_percent, paid_amount, payment_mode, notes=""):
    """
    cart_items: list of dicts:
      {product_id, product_name, category, unit, quantity, unit_price, item_discount}

    Returns (True, bill_id, invoice_number) or (False, error_message).
    """
    if not cart_items:
        return False, "Cart is empty. Add products before creating a bill."

    try:
        discount    = float(discount)    if discount    else 0.0
        gst_percent = float(gst_percent) if gst_percent else 0.0
        paid_amount = float(paid_amount) if paid_amount else 0.0
    except (ValueError, TypeError):
        return False, "Invalid discount, GST, or paid amount."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # calculate subtotal
        subtotal = 0.0
        for item in cart_items:
            qty   = float(item["quantity"])
            price = float(item["unit_price"])
            idc   = float(item.get("item_discount", 0))
            subtotal += round((qty * price) - idc, 2)

        # apply bill-level discount
        if discount_type == "percent":
            discount_amount = round(subtotal * discount / 100, 2)
        else:
            discount_amount = round(discount, 2)

        after_discount = round(subtotal - discount_amount, 2)
        gst_amount     = round(after_discount * gst_percent / 100, 2)
        grand_total    = round(after_discount + gst_amount, 2)
        due_amount     = round(grand_total - paid_amount, 2)

        status = "Paid" if due_amount <= 0 else ("Partial" if paid_amount > 0 else "Due")

        invoice_number = generate_invoice_number()
        bill_date      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
            INSERT INTO bills
                (invoice_number, customer_id, customer_name, customer_mobile,
                 bill_date, subtotal, discount, discount_type, gst_percent,
                 gst_amount, grand_total, paid_amount, due_amount,
                 payment_mode, status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (invoice_number, customer_id, customer_name, customer_mobile,
              bill_date, subtotal, discount_amount, discount_type, gst_percent,
              gst_amount, grand_total, paid_amount, due_amount,
              payment_mode, status, notes))

        bill_id = c.lastrowid

        # insert items + deduct inventory
        for item in cart_items:
            qty   = float(item["quantity"])
            price = float(item["unit_price"])
            idc   = float(item.get("item_discount", 0))
            total = round((qty * price) - idc, 2)

            c.execute("""
                INSERT INTO bill_items
                    (bill_id, product_id, product_name, category,
                     unit, quantity, unit_price, discount, total)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (bill_id, item.get("product_id"), item["product_name"],
                  item.get("category",""), item.get("unit",""),
                  qty, price, idc, total))

            # deduct from product stock
            if item.get("product_id"):
                c.execute("""
                    UPDATE products SET quantity = quantity - ?
                    WHERE id = ? AND quantity >= ?
                """, (qty, item["product_id"], qty))

        # update customer balance if registered
        if customer_id:
            c.execute("""
                UPDATE customers
                SET current_balance = current_balance + ?
                WHERE id = ?
            """, (due_amount, customer_id))

        conn.commit()
        return True, bill_id, invoice_number

    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# GET ALL BILLS
# ==========================

def get_all_bills(date_from=None, date_to=None, status=None, search=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT id, invoice_number, customer_name, customer_mobile,
                   bill_date, subtotal, discount, gst_amount, grand_total,
                   paid_amount, due_amount, payment_mode, status
            FROM bills WHERE 1=1
        """
        params = []
        if date_from:
            q += " AND DATE(bill_date) >= ?"; params.append(date_from)
        if date_to:
            q += " AND DATE(bill_date) <= ?"; params.append(date_to)
        if status and status != "All":
            q += " AND status = ?"; params.append(status)
        if search:
            q += " AND (invoice_number LIKE ? OR customer_name LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY bill_date DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_all_bills] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# GET BILL DETAILS
# ==========================

def get_bill_by_id(bill_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        return c.fetchone()
    except sqlite3.Error as e:
        print(f"[get_bill_by_id] {e}"); return None
    finally:
        if conn: conn.close()


def get_bill_items(bill_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT product_name, category, unit, quantity,
                   unit_price, discount, total
            FROM bill_items WHERE bill_id=?
        """, (bill_id,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_bill_items] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# CANCEL BILL
# ==========================

def cancel_bill(bill_id):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT status, customer_id, due_amount FROM bills WHERE id=?", (bill_id,))
        bill = c.fetchone()
        if not bill:
            return False, f"No bill found with ID {bill_id}."
        if bill["status"] == "Cancelled":
            return False, "Bill is already cancelled."

        # restore product stock
        c.execute("SELECT product_id, quantity FROM bill_items WHERE bill_id=?", (bill_id,))
        for item in c.fetchall():
            if item["product_id"]:
                c.execute("UPDATE products SET quantity=quantity+? WHERE id=?",
                          (item["quantity"], item["product_id"]))

        # fix customer balance
        if bill["customer_id"] and bill["due_amount"] > 0:
            c.execute("""
                UPDATE customers SET current_balance=current_balance-?
                WHERE id=?
            """, (bill["due_amount"], bill["customer_id"]))

        c.execute("UPDATE bills SET status='Cancelled' WHERE id=?", (bill_id,))
        conn.commit()
        return True, "Bill cancelled and stock restored."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# RECORD DUE PAYMENT
# ==========================

def record_due_payment(bill_id, amount):
    try:
        amount = float(amount)
        if amount <= 0: return False, "Amount must be > 0."
    except: return False, "Invalid amount."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT customer_id, due_amount, paid_amount FROM bills WHERE id=?", (bill_id,))
        bill = c.fetchone()
        if not bill: return False, f"No bill with ID {bill_id}."
        if amount > float(bill["due_amount"]):
            return False, f"Amount exceeds due amount ₹{bill['due_amount']:.2f}."

        new_paid = round(float(bill["paid_amount"]) + amount, 2)
        new_due  = round(float(bill["due_amount"])  - amount, 2)
        status   = "Paid" if new_due <= 0 else "Partial"

        c.execute("""
            UPDATE bills SET paid_amount=?, due_amount=?, status=? WHERE id=?
        """, (new_paid, new_due, status, bill_id))

        if bill["customer_id"]:
            c.execute("""
                UPDATE customers SET current_balance=current_balance-? WHERE id=?
            """, (amount, bill["customer_id"]))

        conn.commit()
        return True, f"Payment of ₹{amount:,.2f} recorded. Remaining due: ₹{new_due:,.2f}"
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        if conn: conn.close()


# ==========================
# SALES ANALYTICS
# ==========================

def get_sales_summary(date_from=None, date_to=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        base = "FROM bills WHERE status != 'Cancelled'"
        params = []
        if date_from:
            base += " AND DATE(bill_date)>=?"; params.append(date_from)
        if date_to:
            base += " AND DATE(bill_date)<=?"; params.append(date_to)

        c.execute(f"SELECT COUNT(*), COALESCE(SUM(grand_total),0), COALESCE(SUM(paid_amount),0), COALESCE(SUM(due_amount),0) {base}", params)
        r = c.fetchone()
        return {
            "total_bills":    r[0],
            "total_revenue":  round(float(r[1]), 2),
            "total_collected":round(float(r[2]), 2),
            "total_due":      round(float(r[3]), 2),
        }
    except sqlite3.Error as e:
        print(f"[get_sales_summary] {e}")
        return {"total_bills":0,"total_revenue":0.0,"total_collected":0.0,"total_due":0.0}
    finally:
        if conn: conn.close()


def get_best_selling_products(limit=10):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT bi.product_name,
                   SUM(bi.quantity)  AS total_qty,
                   SUM(bi.total)     AS total_revenue,
                   COUNT(DISTINCT bi.bill_id) AS num_bills
            FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            WHERE b.status != 'Cancelled'
            GROUP BY bi.product_name
            ORDER BY total_qty DESC
            LIMIT ?
        """, (limit,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_best_selling_products] {e}"); return []
    finally:
        if conn: conn.close()


def get_daily_sales(days=30):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT DATE(bill_date) AS day,
                   COUNT(*)        AS num_bills,
                   SUM(grand_total) AS revenue
            FROM bills
            WHERE status != 'Cancelled'
              AND bill_date >= DATE('now', ?)
            GROUP BY day
            ORDER BY day ASC
        """, (f"-{days} days",))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_daily_sales] {e}"); return []
    finally:
        if conn: conn.close()


def get_payment_mode_summary():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT payment_mode,
                   COUNT(*)         AS count,
                   SUM(grand_total) AS total
            FROM bills WHERE status != 'Cancelled'
            GROUP BY payment_mode
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_payment_mode_summary] {e}"); return []
    finally:
        if conn: conn.close()


def get_profit_report(date_from=None, date_to=None):
    """Revenue vs buying cost for sold items."""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT
                bi.product_name,
                SUM(bi.quantity)                       AS qty_sold,
                SUM(bi.total)                          AS revenue,
                SUM(bi.quantity * p.buying_price)      AS cost,
                SUM(bi.total) - SUM(bi.quantity * p.buying_price) AS profit
            FROM bill_items bi
            JOIN bills    b ON bi.bill_id    = b.id
            LEFT JOIN products p ON bi.product_id = p.id
            WHERE b.status != 'Cancelled'
        """
        params = []
        if date_from:
            q += " AND DATE(b.bill_date)>=?"; params.append(date_from)
        if date_to:
            q += " AND DATE(b.bill_date)<=?"; params.append(date_to)
        q += " GROUP BY bi.product_name ORDER BY profit DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_profit_report] {e}"); return []
    finally:
        if conn: conn.close()


# ==========================
# SEARCH HELPERS
# ==========================

def get_active_customers_for_sales():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, name, mobile, current_balance
            FROM customers WHERE status='Active' ORDER BY name
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_active_customers_for_sales] {e}"); return []
    finally:
        if conn: conn.close()


def get_all_products_for_sales():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, name, category, unit, selling_price, quantity
            FROM products WHERE quantity > 0 ORDER BY name
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_all_products_for_sales] {e}"); return []
    finally:
        if conn: conn.close()


def search_products_for_sale(keyword):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, name, category, unit, selling_price, quantity
            FROM products WHERE name LIKE ? ORDER BY name
        """, (f"%{keyword}%",))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[search_products_for_sale] {e}"); return []
    finally:
        if conn: conn.close()