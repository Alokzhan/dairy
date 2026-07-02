import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "dairy.db")


# ==========================
# DB CONNECTION HELPER
# ==========================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row        # lets you access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==========================
# ADD EMPLOYEE
# ==========================

def add_employee(name, phone, address, role, salary, joining_date):
    """
    Insert a new employee record.
    Returns (True, employee_id) on success or (False, error_message) on failure.
    """

    # --- basic validation ---
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

        # check duplicate phone
        cursor.execute(
            "SELECT id FROM employees WHERE phone = ?",
            (phone,)
        )
        if cursor.fetchone():
            return False, f"An employee with phone '{phone}' already exists."

        cursor.execute("""
            INSERT INTO employees
                (name, phone, address, role, salary, joining_date)
            VALUES
                (?, ?, ?, ?, ?, ?)
        """, (name, phone, address.strip(), role.strip(), salary, joining_date))

        conn.commit()
        return True, cursor.lastrowid

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# GET ALL EMPLOYEES
# ==========================

def get_employees():
    """
    Return all employee rows ordered by most recent first.
    Each row is a sqlite3.Row (access by column name or index).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                phone,
                address,
                role,
                salary,
                joining_date
            FROM employees
            ORDER BY id DESC
        """)

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_employees] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# GET SINGLE EMPLOYEE BY ID
# ==========================

def get_employee_by_id(emp_id):
    """
    Return one employee row by primary key, or None if not found.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, phone, address,
                role, salary, joining_date
            FROM employees
            WHERE id = ?
        """, (emp_id,))

        return cursor.fetchone()

    except sqlite3.Error as e:
        print(f"[get_employee_by_id] DB error: {e}")
        return None

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH EMPLOYEES BY NAME
# ==========================

def search_employees_by_name(keyword):
    """
    Case-insensitive partial search on employee name.
    Returns a list of matching rows.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, phone, address,
                role, salary, joining_date
            FROM employees
            WHERE name LIKE ?
            ORDER BY name ASC
        """, (f"%{keyword.strip()}%",))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[search_employees_by_name] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# SEARCH BY PHONE
# ==========================

def search_employee_by_phone(phone):
    """
    Exact match search by phone number.
    Returns one row or None.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, phone, address,
                role, salary, joining_date
            FROM employees
            WHERE phone = ?
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
    """
    Update an existing employee's details.
    Returns (True, "Updated successfully") or (False, error_message).
    """
    name  = name.strip()
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

        # make sure the employee exists
        cursor.execute("SELECT id FROM employees WHERE id = ?", (emp_id,))
        if not cursor.fetchone():
            return False, f"No employee found with ID {emp_id}."

        # check phone conflict with another employee
        cursor.execute(
            "SELECT id FROM employees WHERE phone = ? AND id != ?",
            (phone, emp_id)
        )
        if cursor.fetchone():
            return False, f"Phone '{phone}' is already used by another employee."

        cursor.execute("""
            UPDATE employees
            SET
                name         = ?,
                phone        = ?,
                address      = ?,
                role         = ?,
                salary       = ?,
                joining_date = ?
            WHERE id = ?
        """, (name, phone, address.strip(), role.strip(), salary, joining_date, emp_id))

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
    Delete an employee by ID.
    Returns (True, "Deleted successfully") or (False, error_message).
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

        return True, f"Employee '{emp_name}' deleted successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    finally:
        if conn:
            conn.close()


# ==========================
# EMPLOYEE COUNT
# ==========================

def employee_count():
    """Return total number of employees, or 0 on error."""
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


# ==========================
# TOTAL SALARY EXPENSE
# ==========================

def total_salary():
    """Return sum of all employee salaries, or 0.0 on error / empty table."""
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


# ==========================
# EMPLOYEES BY ROLE
# ==========================

def get_employees_by_role(role):
    """
    Filter employees by role (case-insensitive exact match).
    Useful for listing all 'Drivers', 'Managers', etc.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, name, phone, address,
                role, salary, joining_date
            FROM employees
            WHERE LOWER(role) = LOWER(?)
            ORDER BY name ASC
        """, (role.strip(),))

        return cursor.fetchall()

    except sqlite3.Error as e:
        print(f"[get_employees_by_role] DB error: {e}")
        return []

    finally:
        if conn:
            conn.close()


# ==========================
# AVERAGE SALARY
# ==========================

def average_salary():
    """Return average employee salary rounded to 2 decimal places."""
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