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


def ensure_tables():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id       INTEGER NOT NULL,
                transaction_type TEXT    NOT NULL,
                quantity         REAL    NOT NULL,
                batch_number     TEXT,
                mfg_date         TEXT,
                expiry_date      TEXT,
                supplier         TEXT,
                unit_cost        REAL DEFAULT 0,
                total_cost       REAL DEFAULT 0,
                notes            TEXT,
                transaction_date TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ensure_tables] {e}")
    finally:
        if conn: conn.close()


def stock_in(product_id, quantity, batch_number="", mfg_date="",
             expiry_date="", supplier="", unit_cost=0, notes=""):
    try:
        quantity  = float(quantity)
        unit_cost = float(unit_cost) if unit_cost else 0.0
        if quantity <= 0: return False, "Quantity must be > 0."
    except: return False, "Invalid quantity or unit cost."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM products WHERE id=?", (product_id,))
        if not c.fetchone(): return False, f"No product ID {product_id}."
        total_cost = round(quantity * unit_cost, 2)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO inventory_transactions
            (product_id,transaction_type,quantity,batch_number,mfg_date,
             expiry_date,supplier,unit_cost,total_cost,notes,transaction_date)
            VALUES (?,'IN',?,?,?,?,?,?,?,?,?)""",
            (product_id,quantity,batch_number,mfg_date,expiry_date,
             supplier,unit_cost,total_cost,notes,now))
        c.execute("UPDATE products SET quantity=quantity+? WHERE id=?", (quantity,product_id))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e: return False, f"DB error: {e}"
    finally:
        if conn: conn.close()


def stock_out(product_id, quantity, notes="", batch_number=""):
    try:
        quantity = float(quantity)
        if quantity <= 0: return False, "Quantity must be > 0."
    except: return False, "Invalid quantity."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id,name,quantity FROM products WHERE id=?", (product_id,))
        p = c.fetchone()
        if not p: return False, f"No product ID {product_id}."
        if quantity > float(p["quantity"]):
            return False, f"Insufficient stock! Available: {p['quantity']}, Requested: {quantity}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO inventory_transactions
            (product_id,transaction_type,quantity,batch_number,notes,transaction_date)
            VALUES (?,'OUT',?,?,?,?)""", (product_id,quantity,batch_number,notes,now))
        c.execute("UPDATE products SET quantity=quantity-? WHERE id=?", (quantity,product_id))
        conn.commit()
        return True, c.lastrowid
    except sqlite3.Error as e: return False, f"DB error: {e}"
    finally:
        if conn: conn.close()


def stock_adjustment(product_id, new_quantity, notes=""):
    try:
        new_quantity = float(new_quantity)
        if new_quantity < 0: return False, "Quantity cannot be negative."
    except: return False, "Invalid quantity."

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id,name,quantity FROM products WHERE id=?", (product_id,))
        p = c.fetchone()
        if not p: return False, f"No product ID {product_id}."
        old = float(p["quantity"])
        diff = round(new_quantity - old, 4)
        now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        adj_notes = f"Adjustment: {old} → {new_quantity}. {notes}".strip()
        c.execute("""INSERT INTO inventory_transactions
            (product_id,transaction_type,quantity,notes,transaction_date)
            VALUES (?,'ADJUSTMENT',?,?,?)""", (product_id,diff,adj_notes,now))
        c.execute("UPDATE products SET quantity=? WHERE id=?", (new_quantity,product_id))
        conn.commit()
        return True, f"Stock adjusted from {old} to {new_quantity}."
    except sqlite3.Error as e: return False, f"DB error: {e}"
    finally:
        if conn: conn.close()


def get_current_stock():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT p.id, p.name, p.category, p.unit,
                   p.quantity AS current_stock,
                   p.buying_price, p.selling_price,
                   ROUND(p.quantity * p.buying_price, 2) AS stock_value
            FROM products p
            ORDER BY p.category ASC, p.name ASC
        """)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_current_stock] {e}"); return []
    finally:
        if conn: conn.close()


def get_low_stock(threshold=10):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""SELECT id,name,category,unit,quantity,buying_price
            FROM products WHERE quantity>0 AND quantity<=?
            ORDER BY quantity ASC""", (threshold,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_low_stock] {e}"); return []
    finally:
        if conn: conn.close()


def get_out_of_stock():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""SELECT id,name,category,unit,quantity
            FROM products WHERE quantity<=0 ORDER BY name""")
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_out_of_stock] {e}"); return []
    finally:
        if conn: conn.close()


def get_transaction_history(product_id=None, transaction_type=None,
                             date_from=None, date_to=None):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        q = """
            SELECT t.id, t.transaction_date, p.name AS product_name,
                   p.category, p.unit, t.transaction_type, t.quantity,
                   t.batch_number, t.mfg_date, t.expiry_date,
                   t.supplier, t.unit_cost, t.total_cost, t.notes
            FROM inventory_transactions t
            LEFT JOIN products p ON t.product_id=p.id WHERE 1=1
        """
        params = []
        if product_id:
            q += " AND t.product_id=?"; params.append(product_id)
        if transaction_type and transaction_type != "ALL":
            q += " AND t.transaction_type=?"; params.append(transaction_type)
        if date_from:
            q += " AND DATE(t.transaction_date)>=?"; params.append(date_from)
        if date_to:
            q += " AND DATE(t.transaction_date)<=?"; params.append(date_to)
        q += " ORDER BY t.transaction_date DESC"
        c.execute(q, params)
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_transaction_history] {e}"); return []
    finally:
        if conn: conn.close()


def search_products_for_inventory(keyword):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""SELECT id,name,category,unit,quantity,buying_price,selling_price
            FROM products WHERE name LIKE ? ORDER BY name""", (f"%{keyword.strip()}%",))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[search_products_for_inventory] {e}"); return []
    finally:
        if conn: conn.close()


def get_products_by_category_inv(category):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        if category == "All":
            c.execute("SELECT id,name,category,unit,quantity,buying_price,selling_price FROM products ORDER BY name")
        else:
            c.execute("""SELECT id,name,category,unit,quantity,buying_price,selling_price
                FROM products WHERE category=? ORDER BY name""", (category,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"[get_products_by_category_inv] {e}"); return []
    finally:
        if conn: conn.close()


def get_inventory_stats():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products")
        total = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(quantity*buying_price),0) FROM products")
        value = round(float(c.fetchone()[0]), 2)
        c.execute("SELECT COUNT(*) FROM products WHERE quantity>0 AND quantity<=10")
        low   = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM products WHERE quantity<=0")
        out   = c.fetchone()[0]
        return {"total_products": total, "total_value": value,
                "low_stock_count": low, "out_of_stock_count": out}
    except sqlite3.Error as e:
        print(f"[get_inventory_stats] {e}")
        return {"total_products":0,"total_value":0.0,"low_stock_count":0,"out_of_stock_count":0}
    finally:
        if conn: conn.close()