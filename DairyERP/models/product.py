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
# ADD PRODUCT
# ==========================

def add_product(name, category, unit, buying_price, selling_price, quantity):
    """
    Returns (True, product_id) on success or (False, error_message).
    Reuses deleted IDs (gap-fill).
    """
    name = name.strip()
    category = category.strip()
    unit = unit.strip()

    if not name:
        return False, "Product name cannot be empty."
    if not category or category == "Select Category":
        return False, "Please select a valid category."
    if not unit or unit == "Select Unit":
        return False, "Please select a valid unit."

    try:
        buying_price = float(buying_price)
        if buying_price < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Buying price must be a valid positive number."

    try:
        selling_price = float(selling_price)
        if selling_price < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Selling price must be a valid positive number."

    try:
        quantity = float(quantity)
        if quantity < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Quantity must be a valid positive number."

    if selling_price < buying_price:
        return False, "Selling price cannot be less than buying price."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM products WHERE LOWER(name) = LOWER(?) AND category = ?",
            (name, category)
        )
        if cursor.fetchone():
            return False, f"Product '{name}' already exists in category '{category}'."

        new_id = get_next_available_id(conn, "products")

        if new_id is not None:
            cursor.execute("""
                INSERT INTO products
                    (id, name, category, unit, buying_price, selling_price, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_id, name, category, unit, buying_price, selling_price, quantity))
        else:
            cursor.execute("""
                INSERT INTO products
                    (name, category, unit, buying_price, selling_price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category, unit, buying_price, selling_price, quantity))
            new_id = cursor.lastrowid

        conn.commit()
        return True, new_id

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL PRODUCTS
# ==========================

def get_products():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, unit, buying_price, selling_price, quantity
            FROM products ORDER BY id ASC
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_products] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_product_by_id(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, unit, buying_price, selling_price, quantity
            FROM products WHERE id = ?
        """, (product_id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[get_product_by_id] DB error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def search_product_by_name(keyword):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, unit, buying_price, selling_price, quantity
            FROM products WHERE name LIKE ? ORDER BY category ASC, name ASC
        """, (f"%{keyword.strip()}%",))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[search_product_by_name] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_products_by_category(category):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, unit, buying_price, selling_price, quantity
            FROM products WHERE LOWER(category) = LOWER(?) ORDER BY id ASC
        """, (category.strip(),))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_products_by_category] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


# ==========================
# UPDATE PRODUCT  (✅ now supports changing the ID itself)
# ==========================

def update_product(product_id, name, category, unit,
                   buying_price, selling_price, quantity,
                   new_id=None):
    """
    Updates a product. Optionally also changes its ID to `new_id`
    (e.g. move product from ID 3 to the now-vacant ID 2).

    Returns (True, "message") or (False, error_message).
    """
    name = name.strip()

    if not name:
        return False, "Product name cannot be empty."

    try:
        buying_price = float(buying_price)
        if buying_price < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Buying price must be a valid positive number."

    try:
        selling_price = float(selling_price)
        if selling_price < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Selling price must be a valid positive number."

    try:
        quantity = float(quantity)
        if quantity < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Quantity must be a valid positive number."

    if selling_price < buying_price:
        return False, "Selling price cannot be less than buying price."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            return False, f"No product found with ID {product_id}."

        cursor.execute(
            "SELECT id FROM products WHERE LOWER(name)=LOWER(?) AND category=? AND id!=?",
            (name, category, product_id)
        )
        if cursor.fetchone():
            return False, f"Another product named '{name}' already exists in '{category}'."

        # ── Handle ID change request ──
        target_id = product_id
        if new_id is not None and str(new_id).strip() != "":
            try:
                new_id = int(new_id)
            except (ValueError, TypeError):
                return False, "New ID must be a valid whole number."

            if new_id != product_id:
                # check the target ID is actually free
                cursor.execute("SELECT id FROM products WHERE id = ?", (new_id,))
                if cursor.fetchone():
                    return False, f"ID {new_id} is already in use by another product."
                target_id = new_id

        if target_id != product_id:
            # SQLite allows updating the PRIMARY KEY column directly.
            # Any foreign keys referencing products.id (e.g. bill_items,
            # inventory_transactions) are updated too if defined with
            # ON UPDATE CASCADE; otherwise those old links stay pointed
            # at the old numeric id and should be checked separately.
            cursor.execute("""
                UPDATE products
                SET id = ?, name = ?, category = ?, unit = ?,
                    buying_price = ?, selling_price = ?, quantity = ?
                WHERE id = ?
            """, (target_id, name, category, unit,
                  buying_price, selling_price, quantity, product_id))
            conn.commit()
            return True, f"Product updated and moved from ID {product_id} to ID {target_id}."

        cursor.execute("""
            UPDATE products
            SET name = ?, category = ?, unit = ?,
                buying_price = ?, selling_price = ?, quantity = ?
            WHERE id = ?
        """, (name, category, unit, buying_price, selling_price, quantity, product_id))

        conn.commit()
        return True, "Product updated successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# DELETE PRODUCT
# ==========================

def delete_product(product_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"No product found with ID {product_id}."

        product_name = row["name"]

        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()

        return True, f"Product '{product_name}' deleted. ID {product_id} is now free and can be reused."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# STATS
# ==========================

def product_count():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"[product_count] DB error: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def get_low_stock_products(threshold=10):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, unit, buying_price, selling_price, quantity
            FROM products WHERE quantity <= ? ORDER BY quantity ASC
        """, (threshold,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_low_stock_products] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def total_inventory_value():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(quantity * buying_price) FROM products")
        result = cursor.fetchone()[0]
        return round(float(result), 2) if result else 0.0
    except sqlite3.Error as e:
        print(f"[total_inventory_value] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()