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
    """
    Returns the lowest missing (gap) ID in the table.
    Reuses deleted IDs instead of always incrementing.
    """
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
# ADD EMPLOYEE
# ==========================

def add_employee(name, phone, address, role, salary, joining_date):
    """
    Returns (True, employee_id) on success or (False, error_message).
    Reuses deleted IDs (gap-fill) instead of always using max+1.
    """
    name = name.strip()
    phone = phone.strip()

    if not name:
        return False, "Employee name cannot be empty."
    if not phone.isdigit() or len(phone) < 10:
        return False, "Phone number must be at least 10 digits."
    try:
        salary = float(salary)
        if salary < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Salary must be a valid positive number."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM employees WHERE phone = ?",
            (phone,)
        )
        if cursor.fetchone():
            return False, f"An employee with phone '{phone}' already exists."

        # ── Find gap ID to reuse deleted IDs ──
        new_id = get_next_available_id(conn, "employees")

        if new_id is not None:
            cursor.execute("""
                INSERT INTO employees
                    (id, name, phone, address, role, salary, joining_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_id, name, phone, address.strip(), role.strip(),
                  salary, joining_date))
        else:
            # fallback to autoincrement if gap detection fails
            cursor.execute("""
                INSERT INTO employees
                    (name, phone, address, role, salary, joining_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, phone, address.strip(), role.strip(),
                  salary, joining_date))
            new_id = cursor.lastrowid

        conn.commit()
        return True, new_id

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL EMPLOYEES
# ==========================

def get_employees():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, address, role, salary, joining_date
            FROM employees ORDER BY id ASC
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_employees] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_employee_by_id(emp_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, address, role, salary, joining_date
            FROM employees WHERE id = ?
        """, (emp_id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[get_employee_by_id] DB error: {e}")
        return None
    finally:
        if conn:
            conn.close()


def search_employees_by_name(keyword):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, address, role, salary, joining_date
            FROM employees WHERE name LIKE ? ORDER BY name ASC
        """, (f"%{keyword.strip()}%",))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[search_employees_by_name] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def search_employee_by_phone(phone):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, address, role, salary, joining_date
            FROM employees WHERE phone = ?
        """, (phone.strip(),))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[search_employee_by_phone] DB error: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ==========================
# UPDATE EMPLOYEE
# ==========================

def update_employee(emp_id, name, phone, address, role, salary, joining_date):
    name = name.strip()
    phone = phone.strip()

    if not name:
        return False, "Employee name cannot be empty."
    if not phone.isdigit() or len(phone) < 10:
        return False, "Phone number must be at least 10 digits."
    try:
        salary = float(salary)
        if salary < 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, "Salary must be a valid positive number."

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM employees WHERE id = ?", (emp_id,))
        if not cursor.fetchone():
            return False, f"No employee found with ID {emp_id}."

        cursor.execute(
            "SELECT id FROM employees WHERE phone = ? AND id != ?",
            (phone, emp_id)
        )
        if cursor.fetchone():
            return False, f"Phone '{phone}' is already used by another employee."

        cursor.execute("""
            UPDATE employees
            SET name=?, phone=?, address=?, role=?, salary=?, joining_date=?
            WHERE id=?
        """, (name, phone, address.strip(), role.strip(),
              salary, joining_date, emp_id))

        conn.commit()
        return True, "Employee updated successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# DELETE EMPLOYEE
# ==========================

def delete_employee(emp_id):
    """
    Deletes employee. The ID becomes a 'gap' and will be
    reused by the next add_employee() call.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM employees WHERE id = ?", (emp_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"No employee found with ID {emp_id}."

        emp_name = row["name"]

        cursor.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        conn.commit()

        return True, f"Employee '{emp_name}' deleted. ID {emp_id} will be reused for the next new employee."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# STATS
# ==========================

def employee_count():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"[employee_count] DB error: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def total_salary():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(salary) FROM employees")
        result = cursor.fetchone()[0]
        return float(result) if result else 0.0
    except sqlite3.Error as e:
        print(f"[total_salary] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()


def get_employees_by_role(role):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, phone, address, role, salary, joining_date
            FROM employees WHERE LOWER(role) = LOWER(?) ORDER BY name ASC
        """, (role.strip(),))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"[get_employees_by_role] DB error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def average_salary():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(salary) FROM employees")
        result = cursor.fetchone()[0]
        return round(float(result), 2) if result else 0.0
    except sqlite3.Error as e:
        print(f"[average_salary] DB error: {e}")
        return 0.0
    finally:
        if conn:
            conn.close()