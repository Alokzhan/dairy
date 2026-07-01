import sqlite3
import os

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

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
# ADD PRODUCT
# ==========================

def add_product(name, category, unit, buying_price, selling_price, quantity):
    """
    Returns (True, product_id) on success or (False, error_message) on failure.
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

        # check duplicate name in same category
        cursor.execute(
            "SELECT id FROM products WHERE LOWER(name) = LOWER(?) AND category = ?",
            (name, category)
        )
        if cursor.fetchone():
            return False, f"Product '{name}' already exists in category '{category}'."

        cursor.execute("""
            INSERT INTO products
                (name, category, unit, buying_price, selling_price, quantity)
            VALUES
                (?, ?, ?, ?, ?, ?)
        """, (name, category, unit, buying_price, selling_price, quantity))

        conn.commit()
        return True, cursor.lastrowid

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL PRODUCTS
# ==========================

def get_products():
    """Return all products ordered by category then name."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, category, unit,
                buying_price, selling_price, quantity
            FROM products
            ORDER BY category ASC, name ASC
        """)

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_products] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# GET PRODUCT BY ID
# ==========================

def get_product_by_id(product_id):
    """Return one product row by ID, or None."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, category, unit,
                buying_price, selling_price, quantity
            FROM products
            WHERE id = ?
        """, (product_id,))

        return cursor.fetchone()

    except sqlite3.Error as e:
        print(f"[get_product_by_id] DB error: {e}")
        return None

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH PRODUCT BY NAME
# ==========================

def search_product_by_name(keyword):
    """
    Case-insensitive partial search on product name.
    Returns list of matching rows.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, category, unit,
                buying_price, selling_price, quantity
            FROM products
            WHERE name LIKE ?
            ORDER BY category ASC, name ASC
        """, (f"%{keyword.strip()}%",))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[search_product_by_name] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH BY CATEGORY
# ==========================

def get_products_by_category(category):
    """Return all products in a given category."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, category, unit,
                buying_price, selling_price, quantity
            FROM products
            WHERE LOWER(category) = LOWER(?)
            ORDER BY name ASC
        """, (category.strip(),))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_products_by_category] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# UPDATE PRODUCT
# ==========================

def update_product(product_id, name, category, unit,
                   buying_price, selling_price, quantity):
    """
    Returns (True, "Updated successfully") or (False, error_message).
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

        # check name conflict with another product in same category
        cursor.execute(
            "SELECT id FROM products WHERE LOWER(name)=LOWER(?) AND category=? AND id!=?",
            (name, category, product_id)
        )
        if cursor.fetchone():
            return False, f"Another product named '{name}' already exists in '{category}'."

        cursor.execute("""
            UPDATE products
            SET
                name          = ?,
                category      = ?,
                unit          = ?,
                buying_price  = ?,
                selling_price = ?,
                quantity      = ?
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
    """
    Returns (True, "Deleted successfully") or (False, error_message).
    """
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

        return True, f"Product '{product_name}' deleted successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# PRODUCT COUNT
# ==========================

def product_count():
    """Return total number of products."""
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


# ==========================
# LOW STOCK PRODUCTS
# ==========================

def get_low_stock_products(threshold=10):
    """Return products where quantity is at or below threshold."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, category, unit,
                buying_price, selling_price, quantity
            FROM products
            WHERE quantity <= ?
            ORDER BY quantity ASC
        """, (threshold,))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_low_stock_products] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# TOTAL INVENTORY VALUE
# ==========================

def total_inventory_value():
    """
    Returns total value of all stock (quantity × buying_price).
    Useful for dashboard analytics.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT SUM(quantity * buying_price)
            FROM products
        """)

        result = cursor.fetchone()[0]
        return round(float(result), 2) if result else 0.0

    except sqlite3.Error as e:
        print(f"[total_inventory_value] DB error: {e}")
        return 0.0

    finally:
        if conn:
            conn.close()