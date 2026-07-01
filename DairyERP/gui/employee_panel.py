import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk

from models.employee import (
    add_employee,
    get_employees,
    get_employee_by_id,
    search_employees_by_name,
    update_employee,
    delete_employee,
    employee_count,
    total_salary
)


class EmployeePanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Employee Management")
        self.geometry("1150x750")
        self.resizable(True, True)

        # track which employee is selected in table
        self._selected_id = None

        self._build_ui()
        self.load_data()

    # ==========================
    # BUILD UI
    # ==========================

    def _build_ui(self):

        # ── Title ──────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="👨‍💼  EMPLOYEE MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(15, 5))

        # ── Stats bar ──────────────────────────────────────
        stats_frame = ctk.CTkFrame(self, height=40)
        stats_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_count = ctk.CTkLabel(
            stats_frame,
            text="Total Employees: 0",
            font=("Arial", 13)
        )
        self.lbl_count.pack(side="left", padx=20)

        self.lbl_salary = ctk.CTkLabel(
            stats_frame,
            text="Total Salary: ₹0.00",
            font=("Arial", 13)
        )
        self.lbl_salary.pack(side="left", padx=20)

        # ── Main content: form + table side by side ─────────
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=5)

        # LEFT — form
        form_frame = ctk.CTkFrame(content, width=320)
        form_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)
        form_frame.pack_propagate(False)

        ctk.CTkLabel(
            form_frame,
            text="Employee Details",
            font=("Arial", 15, "bold")
        ).pack(pady=(10, 5))

        # fields
        self.entry_id      = self._field(form_frame, "Employee ID  (for search/update/delete)")
        self.entry_name    = self._field(form_frame, "Full Name")
        self.entry_phone   = self._field(form_frame, "Phone Number (10 digits)")
        self.entry_address = self._field(form_frame, "Address")

        # Role dropdown
        ctk.CTkLabel(form_frame, text="Role", anchor="w").pack(fill="x", padx=15)
        self.role_var = ctk.StringVar(value="Select Role")
        self.entry_role = ctk.CTkOptionMenu(
            form_frame,
            variable=self.role_var,
            values=[
                "Manager", "Supervisor", "Operator",
                "Driver", "Helper", "Accountant",
                "Sales Staff", "Security", "Cleaner", "Other"
            ],
            width=270
        )
        self.entry_role.pack(padx=15, pady=(0, 8))

        self.entry_salary  = self._field(form_frame, "Salary (₹)")
        self.entry_joining = self._field(form_frame, "Joining Date (DD-MM-YYYY)")

        # Buttons
        btn_cfg = {"width": 270, "height": 35, "font": ("Arial", 13)}

        ctk.CTkButton(
            form_frame,
            text="➕  Add Employee",
            fg_color="#2196F3",
            hover_color="#1565C0",
            command=self.add_emp,
            **btn_cfg
        ).pack(padx=15, pady=4)

        ctk.CTkButton(
            form_frame,
            text="🔍  Search by Name",
            fg_color="#9C27B0",
            hover_color="#6A1B9A",
            command=self.search_emp,
            **btn_cfg
        ).pack(padx=15, pady=4)

        ctk.CTkButton(
            form_frame,
            text="✏️  Update Employee",
            fg_color="#FF9800",
            hover_color="#E65100",
            command=self.update_emp,
            **btn_cfg
        ).pack(padx=15, pady=4)

        ctk.CTkButton(
            form_frame,
            text="🗑️  Delete Employee",
            fg_color="#F44336",
            hover_color="#B71C1C",
            command=self.delete_emp,
            **btn_cfg
        ).pack(padx=15, pady=4)

        ctk.CTkButton(
            form_frame,
            text="🔄  Refresh / Show All",
            fg_color="#4CAF50",
            hover_color="#1B5E20",
            command=self.load_data,
            **btn_cfg
        ).pack(padx=15, pady=4)

        ctk.CTkButton(
            form_frame,
            text="✖  Clear Fields",
            fg_color="#607D8B",
            hover_color="#37474F",
            command=self.clear_fields,
            **btn_cfg
        ).pack(padx=15, pady=4)

        # RIGHT — table
        table_frame = ctk.CTkFrame(content)
        table_frame.pack(side="left", fill="both", expand=True, pady=5)

        ctk.CTkLabel(
            table_frame,
            text="Employee Records",
            font=("Arial", 15, "bold")
        ).pack(pady=(10, 5))

        # ttk Treeview (scrollable table)
        cols = ("ID", "Name", "Phone", "Address", "Role", "Salary", "Joining Date")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dairy.Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=28,
            fieldbackground="#2b2b2b",
            font=("Arial", 11)
        )
        style.configure(
            "Dairy.Treeview.Heading",
            background="#1565C0",
            foreground="white",
            font=("Arial", 11, "bold")
        )
        style.map(
            "Dairy.Treeview",
            background=[("selected", "#1976D2")]
        )

        tree_container = tk.Frame(table_frame, bg="#2b2b2b")
        tree_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            style="Dairy.Treeview",
            selectmode="browse"
        )

        col_widths = {
            "ID": 50, "Name": 160, "Phone": 110,
            "Address": 160, "Role": 110,
            "Salary": 90, "Joining Date": 110
        }

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col], anchor="center")

        # scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        # clicking a row fills the form
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ==========================
    # HELPER — single field
    # ==========================

    def _field(self, parent, placeholder):
        ctk.CTkLabel(parent, text=placeholder, anchor="w").pack(fill="x", padx=15)
        entry = ctk.CTkEntry(parent, width=270, placeholder_text=placeholder)
        entry.pack(padx=15, pady=(0, 8))
        return entry

    # ==========================
    # ROW CLICK → FILL FORM
    # ==========================

    def _on_row_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        values = self.tree.item(selected, "values")
        # values: (ID, Name, Phone, Address, Role, Salary, JoiningDate)
        self.clear_fields()

        self.entry_id.insert(0, values[0])
        self.entry_name.insert(0, values[1])
        self.entry_phone.insert(0, values[2])
        self.entry_address.insert(0, values[3])
        self.role_var.set(values[4])
        self.entry_salary.insert(0, values[5])
        self.entry_joining.insert(0, values[6])

        self._selected_id = values[0]

    # ==========================
    # ADD EMPLOYEE
    # ==========================

    def add_emp(self):

        success, result = add_employee(
            self.entry_name.get(),
            self.entry_phone.get(),
            self.entry_address.get(),
            self.role_var.get() if self.role_var.get() != "Select Role" else "",
            self.entry_salary.get(),
            self.entry_joining.get()
        )

        if success:
            messagebox.showinfo(
                "✅ Success",
                f"Employee added successfully!\n(ID: {result})"
            )
            self.clear_fields()
            self.load_data()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # SEARCH BY NAME
    # ==========================

    def search_emp(self):

        keyword = self.entry_name.get().strip()

        if not keyword:
            # if no name typed, try ID field
            emp_id = self.entry_id.get().strip()
            if emp_id:
                self._search_by_id(emp_id)
            else:
                messagebox.showwarning(
                    "⚠️ Input Required",
                    "Enter a name in the Name field to search,\n"
                    "or an ID in the ID field."
                )
            return

        rows = search_employees_by_name(keyword)

        if rows:
            self._populate_table(rows)
            # if exactly one result, auto-fill the form
            if len(rows) == 1:
                self._fill_form_from_row(rows[0])
        else:
            messagebox.showwarning(
                "🔍 Not Found",
                f"No employee found with name containing '{keyword}'."
            )

    def _search_by_id(self, emp_id):
        try:
            row = get_employee_by_id(int(emp_id))
        except ValueError:
            messagebox.showerror("❌ Error", "Employee ID must be a number.")
            return

        if row:
            self._fill_form_from_row(row)
            self._populate_table([row])
        else:
            messagebox.showwarning(
                "🔍 Not Found",
                f"No employee found with ID {emp_id}."
            )

    def _fill_form_from_row(self, row):
        self.clear_fields()
        self.entry_id.insert(0, row["id"])
        self.entry_name.insert(0, row["name"])
        self.entry_phone.insert(0, row["phone"])
        self.entry_address.insert(0, row["address"])
        self.role_var.set(row["role"])
        self.entry_salary.insert(0, row["salary"])
        self.entry_joining.insert(0, row["joining_date"])
        self._selected_id = row["id"]

    # ==========================
    # UPDATE EMPLOYEE
    # ==========================

    def update_emp(self):

        emp_id = self.entry_id.get().strip()

        if not emp_id:
            messagebox.showwarning(
                "⚠️ ID Required",
                "Please enter or select an Employee ID to update."
            )
            return

        try:
            emp_id = int(emp_id)
        except ValueError:
            messagebox.showerror("❌ Error", "Employee ID must be a number.")
            return

        confirm = messagebox.askyesno(
            "Confirm Update",
            f"Update details for Employee ID {emp_id}?"
        )
        if not confirm:
            return

        success, msg = update_employee(
            emp_id,
            self.entry_name.get(),
            self.entry_phone.get(),
            self.entry_address.get(),
            self.role_var.get(),
            self.entry_salary.get(),
            self.entry_joining.get()
        )

        if success:
            messagebox.showinfo("✅ Success", msg)
            self.clear_fields()
            self.load_data()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # DELETE EMPLOYEE
    # ==========================

    def delete_emp(self):

        emp_id = self.entry_id.get().strip()

        if not emp_id:
            messagebox.showwarning(
                "⚠️ ID Required",
                "Please enter or select an Employee ID to delete."
            )
            return

        try:
            emp_id = int(emp_id)
        except ValueError:
            messagebox.showerror("❌ Error", "Employee ID must be a number.")
            return

        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete",
            f"Are you sure you want to DELETE Employee ID {emp_id}?\n"
            "This action cannot be undone."
        )
        if not confirm:
            return

        success, msg = delete_employee(emp_id)

        if success:
            messagebox.showinfo("✅ Deleted", msg)
            self.clear_fields()
            self.load_data()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # LOAD ALL DATA → TABLE
    # ==========================

    def load_data(self):
        rows = get_employees()
        self._populate_table(rows)
        self._update_stats()

    def _populate_table(self, rows):
        # clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            self.tree.insert("", "end", values=(
                row["id"],
                row["name"],
                row["phone"],
                row["address"],
                row["role"],
                f"₹{float(row['salary']):,.2f}",
                row["joining_date"]
            ))

    def _update_stats(self):
        self.lbl_count.configure(
            text=f"Total Employees: {employee_count()}"
        )
        self.lbl_salary.configure(
            text=f"Total Salary: ₹{total_salary():,.2f}"
        )

    # ==========================
    # CLEAR FIELDS
    # ==========================

    def clear_fields(self):
        for entry in [
            self.entry_id, self.entry_name, self.entry_phone,
            self.entry_address, self.entry_salary, self.entry_joining
        ]:
            entry.delete(0, "end")

        self.role_var.set("Select Role")
        self._selected_id = None