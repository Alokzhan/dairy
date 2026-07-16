import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk

from models.customer import (
    add_customer,
    get_customers,
    get_customer_by_id,
    search_customers_by_name,
    search_customer_by_mobile,
    get_customers_by_type,
    update_customer,
    delete_customer,
    get_customer_purchase_history,
    get_customer_payment_history,
    get_customer_due,
    customer_count,
    total_due_all
)

CUSTOMER_TYPES = [
    "Retail Customer",
    "Wholesale Customer",
    "Distributor",
    "Hotel",
    "Sweet Shop"
]

STATUS_OPTIONS = ["Active", "Inactive"]


class CustomerPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Customer Management")
        self.geometry("1300x800")
        self.resizable(True, True)

        self._selected_id = None

        self._build_ui()
        self.load_customers()

    # ==========================
    # BUILD UI
    # ==========================

    def _build_ui(self):

        # Title
        ctk.CTkLabel(
            self,
            text="👥  CUSTOMER MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(15, 5))

        # Stats bar
        stats = ctk.CTkFrame(self, height=40)
        stats.pack(fill="x", padx=20, pady=(0, 8))

        self.lbl_count = ctk.CTkLabel(
            stats, text="Total Customers: 0", font=("Arial", 13)
        )
        self.lbl_count.pack(side="left", padx=20)

        self.lbl_due = ctk.CTkLabel(
            stats, text="Total Receivable: ₹0.00",
            font=("Arial", 13), text_color="#E53935"
        )
        self.lbl_due.pack(side="left", padx=20)

        # Main area
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=5)

        # ── LEFT: scrollable form ──────────────────────────
        form_outer = ctk.CTkFrame(main, width=340)
        form_outer.pack(side="left", fill="y", padx=(0, 8), pady=5)
        form_outer.pack_propagate(False)

        ctk.CTkLabel(
            form_outer,
            text="Customer Details",
            font=("Arial", 15, "bold")
        ).pack(pady=(10, 4))

        # scrollable container for all fields + buttons
        scroll = ctk.CTkScrollableFrame(form_outer, width=320)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Fields
        self.e_id      = self._field(scroll, "Customer ID  (auto / select row)")
        self._search_row(scroll)
        self.e_name    = self._field(scroll, "Customer Name *")
        self.e_mobile  = self._field(scroll, "Mobile Number * (10 digits)")
        self.e_alt     = self._field(scroll, "Alternate Mobile (optional)")
        self.e_address = self._field(scroll, "Address")
        self.e_village = self._field(scroll, "Village / City")
        self.e_gst     = self._field(scroll, "GST Number (optional)")
        self.e_aadhaar = self._field(scroll, "Aadhaar Number (optional)")

        # Customer Type
        ctk.CTkLabel(scroll, text="Customer Type *", anchor="w").pack(fill="x", padx=8)
        self.type_var = ctk.StringVar(value="Select Type")
        ctk.CTkOptionMenu(
            scroll, variable=self.type_var,
            values=CUSTOMER_TYPES, width=295
        ).pack(padx=8, pady=(0, 8))

        self.e_balance = self._field(scroll, "Opening Balance (₹)")

        # Status
        ctk.CTkLabel(scroll, text="Status", anchor="w").pack(fill="x", padx=8)
        self.status_var = ctk.StringVar(value="Active")
        ctk.CTkOptionMenu(
            scroll, variable=self.status_var,
            values=STATUS_OPTIONS, width=295
        ).pack(padx=8, pady=(0, 12))

        # ── Action Buttons (inside scroll) ─────────────────
        bw = {"width": 295, "height": 36, "font": ("Arial", 12)}

        ctk.CTkButton(
            scroll, text="➕  Add Customer",
            fg_color="#2196F3", hover_color="#1565C0",
            command=self.add_customer_gui, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="✏️  Update Customer",
            fg_color="#FF9800", hover_color="#E65100",
            command=self.update_customer_gui, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="🗑️  Delete Customer",
            fg_color="#F44336", hover_color="#B71C1C",
            command=self.delete_customer_gui, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="📋  Purchase History",
            fg_color="#9C27B0", hover_color="#6A1B9A",
            command=self.show_purchase_history, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="💳  Payment History",
            fg_color="#00897B", hover_color="#004D40",
            command=self.show_payment_history, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="🔄  Refresh / Show All",
            fg_color="#4CAF50", hover_color="#1B5E20",
            command=self.load_customers, **bw
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="✖  Clear Fields",
            fg_color="#607D8B", hover_color="#37474F",
            command=self.clear_fields, **bw
        ).pack(padx=8, pady=(4, 12))

        # ── RIGHT: tabview ─────────────────────────────────
        right = ctk.CTkFrame(main)
        right.pack(side="left", fill="both", expand=True, pady=5)

        self.tabview = ctk.CTkTabview(right)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)

        self.tabview.add("All Customers")
        self.tabview.add("Filter by Type")

        # Tab 1 — All Customers
        self.tree = self._build_table(
            self.tabview.tab("All Customers"),
            ("No", "ID", "Name", "Mobile", "Village/City",
             "Type", "Balance", "Due (₹)", "Status")
        )
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        # Tab 2 — Filter by Type
        filter_tab = self.tabview.tab("Filter by Type")

        frow = ctk.CTkFrame(filter_tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        self.filter_type_var = ctk.StringVar(value=CUSTOMER_TYPES[0])
        ctk.CTkOptionMenu(
            frow, variable=self.filter_type_var,
            values=CUSTOMER_TYPES, width=220
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            frow, text="Filter",
            command=self.filter_by_type, width=100
        ).pack(side="left")

        self.tree_filter = self._build_table(
            filter_tab,
            ("No", "ID", "Name", "Mobile", "Village/City",
             "Type", "Balance", "Due (₹)", "Status")
        )

    # ==========================
    # SEARCH ROW HELPER
    # ==========================

    def _search_row(self, parent):
        ctk.CTkLabel(parent, text="Search by Name / Mobile", anchor="w").pack(fill="x", padx=8)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(0, 8))
        self.e_search = ctk.CTkEntry(row, placeholder_text="Name or mobile…")
        self.e_search.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(
            row, text="🔍", width=36,
            command=self.search_customer
        ).pack(side="left", padx=(4, 0))

    # ==========================
    # FIELD HELPER
    # ==========================

    def _field(self, parent, placeholder):
        ctk.CTkLabel(parent, text=placeholder, anchor="w").pack(fill="x", padx=8)
        e = ctk.CTkEntry(parent, width=295, placeholder_text=placeholder)
        e.pack(padx=8, pady=(0, 8))
        return e

    # ==========================
    # BUILD TREEVIEW
    # ==========================

    def _build_table(self, parent, cols):

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Cust.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=27, fieldbackground="#2b2b2b",
            font=("Arial", 11)
        )
        style.configure(
            "Cust.Treeview.Heading",
            background="#1565C0", foreground="white",
            font=("Arial", 11, "bold")
        )
        style.map("Cust.Treeview", background=[("selected", "#1976D2")])

        container = tk.Frame(parent, bg="#2b2b2b")
        container.pack(fill="both", expand=True, padx=8, pady=5)

        col_widths = {
            "No": 35, "ID": 45, "Name": 170, "Mobile": 110,
            "Village/City": 120, "Type": 130,
            "Balance": 90, "Due (₹)": 90, "Status": 75
        }

        tree = ttk.Treeview(
            container, columns=cols,
            show="headings", style="Cust.Treeview",
            selectmode="browse"
        )

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        tree.tag_configure("inactive", foreground="#888888")
        tree.tag_configure("due",      foreground="#FF5722")

        return tree

    # ==========================
    # ROW CLICK → FILL FORM
    # ==========================

    def _on_row_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, "values")
        row = get_customer_by_id(int(values[1]))
        if row:
            self._fill_form(row)

    def _fill_form(self, row):
        self.clear_fields()
        self.e_id.insert(0,      row["id"])
        self.e_name.insert(0,    row["name"])
        self.e_mobile.insert(0,  row["mobile"])
        self.e_alt.insert(0,     row["alt_mobile"]  or "")
        self.e_address.insert(0, row["address"]      or "")
        self.e_village.insert(0, row["village_city"] or "")
        self.e_gst.insert(0,     row["gst"]          or "")
        self.e_aadhaar.insert(0, row["aadhaar"]      or "")
        self.type_var.set(       row["customer_type"])
        self.e_balance.insert(0, row["opening_balance"])
        self.status_var.set(     row["status"])
        self._selected_id = row["id"]

    # ==========================
    # ADD CUSTOMER
    # ==========================

    def add_customer_gui(self):
        success, result = add_customer(
            self.e_name.get(),
            self.e_mobile.get(),
            self.e_alt.get(),
            self.e_address.get(),
            self.e_village.get(),
            self.e_gst.get(),
            self.e_aadhaar.get(),
            self.type_var.get(),
            self.e_balance.get(),
            self.status_var.get()
        )
        if success:
            messagebox.showinfo("✅ Success", f"Customer added!\n(ID: {result})")
            self.clear_fields()
            self.load_customers()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # SEARCH
    # ==========================

    def search_customer(self):
        keyword = self.e_search.get().strip()
        if not keyword:
            messagebox.showwarning("⚠️ Input Required", "Enter a name or mobile to search.")
            return

        if keyword.isdigit():
            row = search_customer_by_mobile(keyword)
            if row:
                self._fill_form(row)
                self._populate_table(self.tree, [row])
                return

        rows = search_customers_by_name(keyword)
        if rows:
            self._populate_table(self.tree, rows)
            if len(rows) == 1:
                self._fill_form(rows[0])
        else:
            messagebox.showwarning("🔍 Not Found", f"No customer found matching '{keyword}'.")

    # ==========================
    # FILTER BY TYPE
    # ==========================

    def filter_by_type(self):
        rows = get_customers_by_type(self.filter_type_var.get())
        self._populate_table(self.tree_filter, rows)

    # ==========================
    # UPDATE CUSTOMER
    # ==========================

    def update_customer_gui(self):
        cid = self.e_id.get().strip()
        if not cid:
            messagebox.showwarning("⚠️ ID Required", "Select or enter a Customer ID.")
            return
        try:
            cid = int(cid)
        except ValueError:
            messagebox.showerror("❌ Error", "Customer ID must be a number.")
            return

        if not messagebox.askyesno("Confirm Update", f"Update Customer ID {cid}?"):
            return

        success, msg = update_customer(
            cid,
            self.e_name.get(), self.e_mobile.get(),
            self.e_alt.get(), self.e_address.get(),
            self.e_village.get(), self.e_gst.get(),
            self.e_aadhaar.get(), self.type_var.get(),
            self.e_balance.get(), self.status_var.get()
        )
        if success:
            messagebox.showinfo("✅ Success", msg)
            self.clear_fields()
            self.load_customers()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # DELETE CUSTOMER
    # ==========================

    def delete_customer_gui(self):
        cid = self.e_id.get().strip()
        if not cid:
            messagebox.showwarning("⚠️ ID Required", "Select or enter a Customer ID.")
            return
        try:
            cid = int(cid)
        except ValueError:
            messagebox.showerror("❌ Error", "Customer ID must be a number.")
            return

        if not messagebox.askyesno("⚠️ Confirm Delete",
                                   f"Delete Customer ID {cid}?\nThis cannot be undone."):
            return

        success, msg = delete_customer(cid)
        if success:
            messagebox.showinfo("✅ Deleted", msg)
            self.clear_fields()
            self.load_customers()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # PURCHASE HISTORY
    # ==========================

    def show_purchase_history(self):
        cid = self.e_id.get().strip()
        if not cid:
            messagebox.showwarning("⚠️ ID Required", "Select a customer first.")
            return

        rows  = get_customer_purchase_history(int(cid))
        cname = self.e_name.get() or f"ID {cid}"

        win = ctk.CTkToplevel(self)
        win.title(f"Purchase History — {cname}")
        win.geometry("850x450")

        ctk.CTkLabel(win, text=f"📋 Purchase History: {cname}",
                     font=("Arial", 16, "bold")).pack(pady=10)

        cols = ("Sale ID", "Date", "Product", "Qty", "Unit", "Unit Price", "Total")
        container = tk.Frame(win, bg="#2b2b2b")
        container.pack(fill="both", expand=True, padx=15, pady=10)

        tree = ttk.Treeview(container, columns=cols, show="headings", style="Cust.Treeview")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        total = 0.0
        if rows:
            for r in rows:
                tree.insert("", "end", values=(
                    r["id"], r["sale_date"], r["product_name"],
                    r["quantity"], r["unit"],
                    f"₹{float(r['unit_price']):,.2f}",
                    f"₹{float(r['total']):,.2f}"
                ))
                total += float(r["total"])
        else:
            tree.insert("", "end", values=("—", "No purchases found", "", "", "", "", ""))

        ctk.CTkLabel(
            win,
            text=f"Total Purchases: ₹{total:,.2f}     |     Due: ₹{get_customer_due(int(cid)):,.2f}",
            font=("Arial", 13, "bold"), text_color="#E53935"
        ).pack(pady=8)

    # ==========================
    # PAYMENT HISTORY
    # ==========================

    def show_payment_history(self):
        cid = self.e_id.get().strip()
        if not cid:
            messagebox.showwarning("⚠️ ID Required", "Select a customer first.")
            return

        rows  = get_customer_payment_history(int(cid))
        cname = self.e_name.get() or f"ID {cid}"

        win = ctk.CTkToplevel(self)
        win.title(f"Payment History — {cname}")
        win.geometry("700x400")

        ctk.CTkLabel(win, text=f"💳 Payment History: {cname}",
                     font=("Arial", 16, "bold")).pack(pady=10)

        cols = ("Pay ID", "Date", "Amount", "Method", "Notes")
        container = tk.Frame(win, bg="#2b2b2b")
        container.pack(fill="both", expand=True, padx=15, pady=10)

        tree = ttk.Treeview(container, columns=cols, show="headings", style="Cust.Treeview")
        widths = {"Pay ID": 60, "Date": 110, "Amount": 100, "Method": 110, "Notes": 250}
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 100), anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        total_paid = 0.0
        if rows:
            for r in rows:
                tree.insert("", "end", values=(
                    r["id"], r["payment_date"],
                    f"₹{float(r['amount']):,.2f}",
                    r["method"], r["notes"] or ""
                ))
                total_paid += float(r["amount"])
        else:
            tree.insert("", "end", values=("—", "No payments found", "", "", ""))

        ctk.CTkLabel(
            win, text=f"Total Paid: ₹{total_paid:,.2f}",
            font=("Arial", 13, "bold"), text_color="#43A047"
        ).pack(pady=8)

    # ==========================
    # LOAD ALL
    # ==========================

    def load_customers(self):
        rows = get_customers()
        self._populate_table(self.tree, rows)
        self._update_stats()

    def _populate_table(self, tree, rows):
        for item in tree.get_children():
            tree.delete(item)

        for idx, row in enumerate(rows, start=1):
            due    = get_customer_due(row["id"])
            bal    = float(row["current_balance"])
            status = row["status"]
            tag    = "inactive" if status == "Inactive" else ("due" if due > 0 else "")

            tree.insert("", "end", tags=(tag,), values=(
                idx,
                row["id"],
                row["name"],
                row["mobile"],
                row["village_city"] or "—",
                row["customer_type"],
                f"₹{bal:,.2f}",
                f"₹{due:,.2f}",
                status
            ))

    def _update_stats(self):
        self.lbl_count.configure(text=f"Total Customers: {customer_count()}")
        self.lbl_due.configure(text=f"Total Receivable: ₹{total_due_all():,.2f}")

    # ==========================
    # CLEAR FIELDS
    # ==========================

    def clear_fields(self):
        for e in [
            self.e_id, self.e_name, self.e_mobile, self.e_alt,
            self.e_address, self.e_village, self.e_gst,
            self.e_aadhaar, self.e_balance, self.e_search
        ]:
            e.delete(0, "end")
        self.type_var.set("Select Type")
        self.status_var.set("Active")
        self._selected_id = None