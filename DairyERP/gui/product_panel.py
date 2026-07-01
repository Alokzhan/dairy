import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk

from models.product import (
    add_product,
    get_products,
    get_product_by_id,
    search_product_by_name,
    get_products_by_category,
    update_product,
    delete_product,
    product_count,
    total_inventory_value,
    get_low_stock_products
)

CATEGORIES = [
    "Ghee", "Cream", "Paneer", "Butter",
    "Khoya", "Milk", "Dahi", "Lassi", "Other"
]

UNITS = ["Kg", "Gram", "Litre", "ML", "Packet", "Piece", "Box"]


class ProductPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Product Management")
        self.geometry("1200x780")
        self.resizable(True, True)

        self._selected_id = None

        self._build_ui()
        self.load_products()

    # ==========================
    # BUILD UI
    # ==========================

    def _build_ui(self):

        # ── Title ──────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="🧈  PRODUCT MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(15, 5))

        # ── Stats bar ──────────────────────────────────────
        stats_frame = ctk.CTkFrame(self, height=40)
        stats_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_count = ctk.CTkLabel(
            stats_frame,
            text="Total Products: 0",
            font=("Arial", 13)
        )
        self.lbl_count.pack(side="left", padx=20)

        self.lbl_value = ctk.CTkLabel(
            stats_frame,
            text="Inventory Value: ₹0.00",
            font=("Arial", 13)
        )
        self.lbl_value.pack(side="left", padx=20)

        self.lbl_lowstock = ctk.CTkLabel(
            stats_frame,
            text="⚠️ Low Stock: 0",
            font=("Arial", 13),
            text_color="#FF5722"
        )
        self.lbl_lowstock.pack(side="left", padx=20)

        # ── Main content ───────────────────────────────────
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=5)

        # LEFT — Form
        form_frame = ctk.CTkFrame(content, width=330)
        form_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)
        form_frame.pack_propagate(False)

        ctk.CTkLabel(
            form_frame,
            text="Product Details",
            font=("Arial", 15, "bold")
        ).pack(pady=(10, 5))

        # Product ID (read-only helper)
        self.entry_id = self._field(form_frame, "Product ID  (for update/delete)")

        # Search bar inside form
        ctk.CTkLabel(form_frame, text="Search by Name", anchor="w").pack(fill="x", padx=15)
        search_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        search_row.pack(fill="x", padx=15, pady=(0, 8))
        self.entry_search = ctk.CTkEntry(search_row, placeholder_text="Type product name…")
        self.entry_search.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(
            search_row,
            text="🔍",
            width=36,
            command=self.search_product_gui
        ).pack(side="left", padx=(4, 0))

        # Name
        self.entry_name = self._field(form_frame, "Product Name")

        # Category dropdown
        ctk.CTkLabel(form_frame, text="Category", anchor="w").pack(fill="x", padx=15)
        self.category_var = ctk.StringVar(value="Select Category")
        self.entry_category = ctk.CTkOptionMenu(
            form_frame,
            variable=self.category_var,
            values=CATEGORIES,
            width=280,
            command=self._on_category_filter
        )
        self.entry_category.pack(padx=15, pady=(0, 8))

        # Unit dropdown
        ctk.CTkLabel(form_frame, text="Unit", anchor="w").pack(fill="x", padx=15)
        self.unit_var = ctk.StringVar(value="Select Unit")
        self.entry_unit = ctk.CTkOptionMenu(
            form_frame,
            variable=self.unit_var,
            values=UNITS,
            width=280
        )
        self.entry_unit.pack(padx=15, pady=(0, 8))

        self.entry_buying  = self._field(form_frame, "Buying Price  (₹)")
        self.entry_selling = self._field(form_frame, "Selling Price (₹)")
        self.entry_qty     = self._field(form_frame, "Quantity")

        # Buttons
        btn_cfg = {"width": 280, "height": 34, "font": ("Arial", 12)}

        ctk.CTkButton(
            form_frame, text="➕  Add Product",
            fg_color="#2196F3", hover_color="#1565C0",
            command=self.add_product_gui, **btn_cfg
        ).pack(padx=15, pady=3)

        ctk.CTkButton(
            form_frame, text="✏️  Update Product",
            fg_color="#FF9800", hover_color="#E65100",
            command=self.update_product_gui, **btn_cfg
        ).pack(padx=15, pady=3)

        ctk.CTkButton(
            form_frame, text="🗑️  Delete Product",
            fg_color="#F44336", hover_color="#B71C1C",
            command=self.delete_product_gui, **btn_cfg
        ).pack(padx=15, pady=3)

        ctk.CTkButton(
            form_frame, text="⚠️  Show Low Stock",
            fg_color="#FF5722", hover_color="#BF360C",
            command=self.show_low_stock, **btn_cfg
        ).pack(padx=15, pady=3)

        ctk.CTkButton(
            form_frame, text="🔄  Refresh / Show All",
            fg_color="#4CAF50", hover_color="#1B5E20",
            command=self.load_products, **btn_cfg
        ).pack(padx=15, pady=3)

        ctk.CTkButton(
            form_frame, text="✖  Clear Fields",
            fg_color="#607D8B", hover_color="#37474F",
            command=self.clear_fields, **btn_cfg
        ).pack(padx=15, pady=3)

        # RIGHT — Table
        table_frame = ctk.CTkFrame(content)
        table_frame.pack(side="left", fill="both", expand=True, pady=5)

        ctk.CTkLabel(
            table_frame,
            text="Product Records",
            font=("Arial", 15, "bold")
        ).pack(pady=(10, 5))

        cols = ("ID", "Product Name", "Category", "Unit",
                "Buy Price", "Sell Price", "Qty", "Profit/Unit")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Product.Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=28,
            fieldbackground="#2b2b2b",
            font=("Arial", 11)
        )
        style.configure(
            "Product.Treeview.Heading",
            background="#1B5E20",
            foreground="white",
            font=("Arial", 11, "bold")
        )
        style.map(
            "Product.Treeview",
            background=[("selected", "#388E3C")]
        )

        tree_container = tk.Frame(table_frame, bg="#2b2b2b")
        tree_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            style="Product.Treeview",
            selectmode="browse"
        )

        col_widths = {
            "ID": 45, "Product Name": 160, "Category": 90,
            "Unit": 65, "Buy Price": 90, "Sell Price": 90,
            "Qty": 70, "Profit/Unit": 90
        }

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_container, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        # tag for low-stock rows
        self.tree.tag_configure("low_stock", foreground="#FF5722")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ==========================
    # HELPER — single field
    # ==========================

    def _field(self, parent, placeholder):
        ctk.CTkLabel(parent, text=placeholder, anchor="w").pack(fill="x", padx=15)
        entry = ctk.CTkEntry(parent, width=280, placeholder_text=placeholder)
        entry.pack(padx=15, pady=(0, 8))
        return entry

    # ==========================
    # CATEGORY FILTER (dropdown)
    # ==========================

    def _on_category_filter(self, value):
        """When category is selected from dropdown, filter table."""
        if value and value != "Select Category":
            rows = get_products_by_category(value)
            self._populate_table(rows)

    # ==========================
    # ROW CLICK → FILL FORM
    # ==========================

    def _on_row_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        values = self.tree.item(selected, "values")
        # (ID, Name, Category, Unit, BuyPrice, SellPrice, Qty, Profit)
        self.clear_fields()

        self.entry_id.insert(0, values[0])
        self.entry_name.insert(0, values[1])
        self.category_var.set(values[2])
        self.unit_var.set(values[3])

        # strip ₹ and commas before inserting
        self.entry_buying.insert(0,  str(values[4]).replace("₹", "").replace(",", ""))
        self.entry_selling.insert(0, str(values[5]).replace("₹", "").replace(",", ""))
        self.entry_qty.insert(0,     str(values[6]))

        self._selected_id = values[0]

    # ==========================
    # ADD PRODUCT
    # ==========================

    def add_product_gui(self):

        success, result = add_product(
            self.entry_name.get(),
            self.category_var.get(),
            self.unit_var.get(),
            self.entry_buying.get(),
            self.entry_selling.get(),
            self.entry_qty.get()
        )

        if success:
            messagebox.showinfo(
                "✅ Success",
                f"Product added successfully!\n(ID: {result})"
            )
            self.clear_fields()
            self.load_products()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # SEARCH PRODUCT
    # ==========================

    def search_product_gui(self):

        keyword = self.entry_search.get().strip()

        if not keyword:
            messagebox.showwarning(
                "⚠️ Input Required",
                "Please type a product name to search."
            )
            return

        rows = search_product_by_name(keyword)

        if rows:
            self._populate_table(rows)
            if len(rows) == 1:
                self._fill_form_from_row(rows[0])
        else:
            messagebox.showwarning(
                "🔍 Not Found",
                f"No product found with name containing '{keyword}'."
            )

    def _fill_form_from_row(self, row):
        self.clear_fields()
        self.entry_id.insert(0, row["id"])
        self.entry_name.insert(0, row["name"])
        self.category_var.set(row["category"])
        self.unit_var.set(row["unit"])
        self.entry_buying.insert(0, row["buying_price"])
        self.entry_selling.insert(0, row["selling_price"])
        self.entry_qty.insert(0, row["quantity"])
        self._selected_id = row["id"]

    # ==========================
    # UPDATE PRODUCT
    # ==========================

    def update_product_gui(self):

        pid = self.entry_id.get().strip()

        if not pid:
            messagebox.showwarning(
                "⚠️ ID Required",
                "Please enter or select a Product ID to update."
            )
            return

        try:
            pid = int(pid)
        except ValueError:
            messagebox.showerror("❌ Error", "Product ID must be a number.")
            return

        confirm = messagebox.askyesno(
            "Confirm Update",
            f"Update details for Product ID {pid}?"
        )
        if not confirm:
            return

        success, msg = update_product(
            pid,
            self.entry_name.get(),
            self.category_var.get(),
            self.unit_var.get(),
            self.entry_buying.get(),
            self.entry_selling.get(),
            self.entry_qty.get()
        )

        if success:
            messagebox.showinfo("✅ Success", msg)
            self.clear_fields()
            self.load_products()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # DELETE PRODUCT
    # ==========================

    def delete_product_gui(self):

        pid = self.entry_id.get().strip()

        if not pid:
            messagebox.showwarning(
                "⚠️ ID Required",
                "Please enter or select a Product ID to delete."
            )
            return

        try:
            pid = int(pid)
        except ValueError:
            messagebox.showerror("❌ Error", "Product ID must be a number.")
            return

        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete",
            f"Are you sure you want to DELETE Product ID {pid}?\n"
            "This cannot be undone."
        )
        if not confirm:
            return

        success, msg = delete_product(pid)

        if success:
            messagebox.showinfo("✅ Deleted", msg)
            self.clear_fields()
            self.load_products()
        else:
            messagebox.showerror("❌ Error", msg)

    # ==========================
    # LOW STOCK VIEW
    # ==========================

    def show_low_stock(self):
        rows = get_low_stock_products(threshold=10)
        if rows:
            self._populate_table(rows)
            messagebox.showwarning(
                "⚠️ Low Stock Alert",
                f"{len(rows)} product(s) have stock ≤ 10 units.\n"
                "They are highlighted in the table."
            )
        else:
            messagebox.showinfo(
                "✅ Stock OK",
                "All products have sufficient stock (> 10 units)."
            )

    # ==========================
    # LOAD ALL PRODUCTS
    # ==========================

    def load_products(self):
        rows = get_products()
        self._populate_table(rows)
        self._update_stats()

    def _populate_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:
            buy  = float(row["buying_price"])
            sell = float(row["selling_price"])
            qty  = float(row["quantity"])
            profit = round(sell - buy, 2)

            # highlight low stock rows
            tag = "low_stock" if qty <= 10 else ""

            self.tree.insert("", "end", tags=(tag,), values=(
                row["id"],
                row["name"],
                row["category"],
                row["unit"],
                f"₹{buy:,.2f}",
                f"₹{sell:,.2f}",
                f"{qty:g}",
                f"₹{profit:,.2f}"
            ))

    def _update_stats(self):
        low = get_low_stock_products(threshold=10)

        self.lbl_count.configure(
            text=f"Total Products: {product_count()}"
        )
        self.lbl_value.configure(
            text=f"Inventory Value: ₹{total_inventory_value():,.2f}"
        )
        self.lbl_lowstock.configure(
            text=f"⚠️ Low Stock: {len(low)}"
        )

    # ==========================
    # CLEAR FIELDS
    # ==========================

    def clear_fields(self):
        for entry in [
            self.entry_id, self.entry_name,
            self.entry_buying, self.entry_selling,
            self.entry_qty, self.entry_search
        ]:
            entry.delete(0, "end")

        self.category_var.set("Select Category")
        self.unit_var.set("Select Unit")
        self._selected_id = None