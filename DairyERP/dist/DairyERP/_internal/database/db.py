import sqlite3
import os

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(BASE_DIR, "dairy.db")



def create_tables():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Database Path: {DB_PATH}")

    # ==========================
    # USERS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'admin'
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'superadmin')
    """)

    # ==========================
    # EMPLOYEES TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            phone        TEXT    NOT NULL UNIQUE,
            address      TEXT,
            role         TEXT,
            salary       REAL    DEFAULT 0,
            joining_date TEXT
        )
    """)

    # ==========================
    # PRODUCTS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            category      TEXT    NOT NULL,
            unit          TEXT    NOT NULL,
            buying_price  REAL    DEFAULT 0,
            selling_price REAL    DEFAULT 0,
            quantity      REAL    DEFAULT 0
        )
    """)

    # ==========================
    # CUSTOMERS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            mobile           TEXT    NOT NULL UNIQUE,
            alt_mobile       TEXT,
            address          TEXT,
            village_city     TEXT,
            gst              TEXT,
            aadhaar          TEXT,
            customer_type    TEXT,
            opening_balance  REAL    DEFAULT 0,
            current_balance  REAL    DEFAULT 0,
            status           TEXT    DEFAULT 'Active'
        )
    """)

    # ==========================
    # INVENTORY TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER,
            quantity    REAL    DEFAULT 0,
            updated_on  TEXT,
            notes       TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ==========================
    # INVENTORY TRANSACTIONS  ← NEW
    # ==========================
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
            unit_cost        REAL    DEFAULT 0,
            total_cost       REAL    DEFAULT 0,
            notes            TEXT,
            transaction_date TEXT    NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ==========================
    # SALES TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            product_id  INTEGER,
            quantity    REAL,
            unit_price  REAL,
            total       REAL,
            sale_date   TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (product_id)  REFERENCES products(id)
        )
    """)

    # ==========================
    # PAYMENTS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id  INTEGER,
            amount       REAL,
            payment_date TEXT,
            method       TEXT,
            notes        TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # ==========================
    # DISTRIBUTORS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distributors (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            phone   TEXT,
            address TEXT,
            area    TEXT,
            balance REAL DEFAULT 0
        )
    """)

    # ==========================
    # CREAM ENTRIES TABLE
    # ==========================
    cursor.execute("""
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

    # ==========================
    # GHEE ENTRIES TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ghee_entries (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date       TEXT    NOT NULL,
            shift            TEXT    DEFAULT 'Morning',
            cream_used_kg    REAL    DEFAULT 0,
            ghee_produced    REAL    DEFAULT 0,
            packaged_qty     REAL    DEFAULT 0,
            packet_size      TEXT,
            ghee_sold        REAL    DEFAULT 0,
            ghee_distributed REAL    DEFAULT 0,
            ghee_wasted      REAL    DEFAULT 0,
            batch_number     TEXT,
            employee_id      INTEGER,
            employee_name    TEXT,
            notes            TEXT,
            created_at       TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # ==========================
    # ATTENDANCE TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date        TEXT,
            status      TEXT DEFAULT 'Present',
            notes       TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    # ==========================
    # BILLS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number  TEXT    NOT NULL UNIQUE,
            customer_id     INTEGER,
            customer_name   TEXT    NOT NULL,
            customer_mobile TEXT,
            bill_date       TEXT    NOT NULL,
            subtotal        REAL    DEFAULT 0,
            discount        REAL    DEFAULT 0,
            discount_type   TEXT    DEFAULT 'flat',
            gst_percent     REAL    DEFAULT 0,
            gst_amount      REAL    DEFAULT 0,
            grand_total     REAL    DEFAULT 0,
            paid_amount     REAL    DEFAULT 0,
            due_amount      REAL    DEFAULT 0,
            payment_mode    TEXT    DEFAULT 'Cash',
            status          TEXT    DEFAULT 'Paid',
            notes           TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # ==========================
    # BILL ITEMS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id      INTEGER NOT NULL,
            product_id   INTEGER,
            product_name TEXT    NOT NULL,
            category     TEXT,
            unit         TEXT,
            quantity     REAL    NOT NULL,
            unit_price   REAL    NOT NULL,
            discount     REAL    DEFAULT 0,
            total        REAL    NOT NULL,
            FOREIGN KEY (bill_id)    REFERENCES bills(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ==========================
    # SALARY PAYMENTS TABLE
    # ==========================
    cursor.execute("""
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

    # ==========================
    # DISTRIBUTOR PAYMENTS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distributor_payments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_id    INTEGER NOT NULL,
            distributor_name  TEXT    NOT NULL,
            amount            REAL    NOT NULL,
            payment_type      TEXT    DEFAULT 'Payment Made',
            payment_date      TEXT    NOT NULL,
            payment_mode      TEXT    DEFAULT 'Cash',
            notes             TEXT,
            FOREIGN KEY (distributor_id) REFERENCES distributors(id)
        )
    """)

    # ==========================
    # REPORTS TABLE
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type  TEXT,
            generated_on TEXT,
            file_path    TEXT,
            notes        TEXT
        )
    """)

    conn.commit()
    conn.close()

    print("✅ All tables created successfully.")

    # DEBUG — confirm all key tables
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Tables: {tables}")

    cursor.execute("PRAGMA table_info(customers)")
    print(f"Customers columns: {[r[1] for r in cursor.fetchall()]}")

    cursor.execute("PRAGMA table_info(inventory_transactions)")
    print(f"Inventory Txn columns: {[r[1] for r in cursor.fetchall()]}")

    conn.close()


if __name__ == "__main__":
    create_tables()