import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime

from models.inventory import (
    ensure_tables,
    stock_in,
    stock_out,
    stock_adjustment,
    get_current_stock,
    get_low_stock,
    get_out_of_stock,
    get_transaction_history,
    search_products_for_inventory,
    get_products_by_category_inv,
    get_inventory_stats
)

CATEGORIES = ["All", "Ghee", "Cream", "Paneer", "Butter",
              "Khoya", "Milk", "Dahi", "Lassi", "Other"]


class InventoryPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventory Management")
        self.geometry("1350x820")
        self.resizable(True, True)

        ensure_tables()   # create inventory_transactions if missing

        self._selected_product_id   = None
        self._selected_product_name = ""

        self._build_ui()
        self.refresh_dashboard()

    # ==========================
    # BUILD UI
    # ==========================

    def _build_ui(self):

        # ── Title ──────────────────────────────────────────
        ctk.CTkLabel(
            self, text="📦  INVENTORY MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        # ── Dashboard Stats ────────────────────────────────
        dash = ctk.CTkFrame(self, height=60)
        dash.pack(fill="x", padx=20, pady=(0, 8))
        dash.pack_propagate(False)

        self.stat_total   = self._stat_card(dash, "📦 Total Products", "0",   "#1565C0")
        self.stat_value   = self._stat_card(dash, "💰 Stock Value",    "₹0",  "#2E7D32")
        self.stat_low     = self._stat_card(dash, "⚠️ Low Stock",      "0",   "#E65100")
        self.stat_out     = self._stat_card(dash, "🚫 Out of Stock",   "0",   "#B71C1C")

        # ── Tab View ───────────────────────────────────────
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for tab in ["📊 Current Stock", "📥 Stock In",
                    "📤 Stock Out", "🔧 Adjustment",
                    "📋 Transactions", "⚠️ Alerts"]:
            self.tabs.add(tab)

        self._build_current_stock_tab()
        self._build_stock_in_tab()
        self._build_stock_out_tab()
        self._build_adjustment_tab()
        self._build_transactions_tab()
        self._build_alerts_tab()

    # ==========================
    # STAT CARD HELPER
    # ==========================

    def _stat_card(self, parent, label, value, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=6, pady=6)
        ctk.CTkLabel(f, text=label, font=("Arial", 11), text_color="white").pack(pady=(4,0))
        lbl = ctk.CTkLabel(f, text=value, font=("Arial", 15, "bold"), text_color="white")
        lbl.pack(pady=(0,4))
        return lbl

    # ==========================
    # TAB 1 — CURRENT STOCK
    # ==========================

    def _build_current_stock_tab(self):
        tab = self.tabs.tab("📊 Current Stock")

        # filter row
        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        # search
        ctk.CTkLabel(frow, text="Search:").pack(side="left", padx=(0,4))
        self.cs_search = ctk.CTkEntry(frow, width=200, placeholder_text="Product name…")
        self.cs_search.pack(side="left", padx=(0,8))
        ctk.CTkButton(frow, text="🔍 Search", width=90,
                      command=self._cs_search).pack(side="left", padx=(0,12))

        # category filter
        ctk.CTkLabel(frow, text="Category:").pack(side="left", padx=(0,4))
        self.cs_cat_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(frow, variable=self.cs_cat_var,
                          values=CATEGORIES, width=150,
                          command=self._cs_filter_category).pack(side="left", padx=(0,12))

        ctk.CTkButton(frow, text="🔄 Refresh", width=90,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=self._cs_load_all).pack(side="left")

        # table
        cols = ("No", "ID", "Product Name", "Category", "Unit",
                "Stock", "Buy Price", "Sell Price", "Stock Value")
        self.cs_tree = self._make_tree(tab, cols,
            {"No":35,"ID":45,"Product Name":180,"Category":100,"Unit":65,
             "Stock":80,"Buy Price":90,"Sell Price":90,"Stock Value":100})

        self.cs_tree.bind("<<TreeviewSelect>>", self._cs_on_select)
        self.cs_tree.tag_configure("out",    foreground="#F44336")
        self.cs_tree.tag_configure("low",    foreground="#FF9800")
        self.cs_tree.tag_configure("normal", foreground="#81C784")

        # selected product label
        self.cs_selected_lbl = ctk.CTkLabel(
            tab, text="Click a row to select product for Stock In / Out / Adjustment",
            font=("Arial", 12), text_color="gray"
        )
        self.cs_selected_lbl.pack(pady=4)

    def _cs_load_all(self):
        rows = get_current_stock()
        self._fill_cs_tree(rows)

    def _cs_search(self):
        kw = self.cs_search.get().strip()
        if not kw:
            self._cs_load_all(); return
        rows = search_products_for_inventory(kw)
        self._fill_cs_tree(rows)

    def _cs_filter_category(self, val):
        rows = get_products_by_category_inv(val)
        self._fill_cs_tree(rows)

    def _fill_cs_tree(self, rows):
        for i in self.cs_tree.get_children():
            self.cs_tree.delete(i)
        for idx, r in enumerate(rows, start=1):
            qty = float(r["current_stock"]) if "current_stock" in r.keys() else float(r["quantity"])
            tag = "out" if qty <= 0 else ("low" if qty <= 10 else "normal")
            bp  = float(r["buying_price"])
            sp  = float(r["selling_price"])
            sv  = round(qty * bp, 2)
            self.cs_tree.insert("", "end", tags=(tag,), values=(
                idx, r["id"], r["name"], r["category"], r["unit"],
                f"{qty:g}", f"₹{bp:,.2f}", f"₹{sp:,.2f}", f"₹{sv:,.2f}"
            ))

    def _cs_on_select(self, event):
        sel = self.cs_tree.focus()
        if not sel: return
        vals = self.cs_tree.item(sel, "values")
        self._selected_product_id   = int(vals[1])
        self._selected_product_name = vals[2]
        txt = f"✅ Selected: [{vals[1]}] {vals[2]}  |  Current Stock: {vals[5]} {vals[4]}"
        self.cs_selected_lbl.configure(text=txt, text_color="#1976D2")
        # auto-fill product in Stock In / Out / Adjustment tabs
        self._autofill_product(vals[1], vals[2], vals[5], vals[4])

    def _autofill_product(self, pid, name, stock, unit):
        for entry, val in [
            (self.si_pid,  pid),  (self.si_name, f"{name} (Stock: {stock} {unit})"),
            (self.so_pid,  pid),  (self.so_name, f"{name} (Stock: {stock} {unit})"),
            (self.adj_pid, pid),  (self.adj_name,f"{name} (Stock: {stock} {unit})")
        ]:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, val)
            entry.configure(state="readonly")

    # ==========================
    # TAB 2 — STOCK IN
    # ==========================

    def _build_stock_in_tab(self):
        tab  = self.tabs.tab("📥 Stock In")
        form = ctk.CTkScrollableFrame(tab)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(form, text="📥 Record Stock In",
                     font=("Arial", 16, "bold")).pack(pady=(0,10))

        ctk.CTkLabel(form, text="💡 Select a product from 'Current Stock' tab first, or enter Product ID below.",
                     font=("Arial", 11), text_color="gray").pack(pady=(0,8))

        self.si_pid  = self._ro_field(form, "Product ID")
        self.si_name = self._ro_field(form, "Product Name")

        self.si_qty      = self._form_field(form, "Quantity *")
        self.si_cost     = self._form_field(form, "Unit Cost (₹)")
        self.si_batch    = self._form_field(form, "Batch Number")
        self.si_mfg      = self._form_field(form, "Mfg Date (DD-MM-YYYY)")
        self.si_expiry   = self._form_field(form, "Expiry Date (DD-MM-YYYY)")
        self.si_supplier = self._form_field(form, "Supplier Name")
        self.si_notes    = self._form_field(form, "Notes")

        ctk.CTkButton(
            form, text="📥  Confirm Stock In",
            fg_color="#2E7D32", hover_color="#1B5E20",
            width=300, height=40, font=("Arial", 14, "bold"),
            command=self._do_stock_in
        ).pack(pady=12)

    def _do_stock_in(self):
        pid = self.si_pid.get().strip()
        if not pid:
            messagebox.showwarning("⚠️", "Select a product from Current Stock tab first.")
            return
        try: pid = int(pid)
        except: messagebox.showerror("❌", "Invalid Product ID."); return

        success, result = stock_in(
            pid,
            self.si_qty.get(),
            self.si_batch.get(),
            self.si_mfg.get(),
            self.si_expiry.get(),
            self.si_supplier.get(),
            self.si_cost.get() or 0,
            self.si_notes.get()
        )
        if success:
            messagebox.showinfo("✅ Stock In", f"Stock added successfully! (Txn ID: {result})")
            self._clear_form([self.si_qty, self.si_cost, self.si_batch,
                              self.si_mfg, self.si_expiry, self.si_supplier, self.si_notes])
            self.refresh_dashboard()
            self._cs_load_all()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # TAB 3 — STOCK OUT
    # ==========================

    def _build_stock_out_tab(self):
        tab  = self.tabs.tab("📤 Stock Out")
        form = ctk.CTkScrollableFrame(tab)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(form, text="📤 Record Stock Out",
                     font=("Arial", 16, "bold")).pack(pady=(0,10))

        ctk.CTkLabel(form, text="💡 Select a product from 'Current Stock' tab first.",
                     font=("Arial", 11), text_color="gray").pack(pady=(0,8))

        self.so_pid   = self._ro_field(form, "Product ID")
        self.so_name  = self._ro_field(form, "Product Name")
        self.so_qty   = self._form_field(form, "Quantity to Remove *")
        self.so_batch = self._form_field(form, "Batch Number (optional)")
        self.so_notes = self._form_field(form, "Reason / Notes")

        ctk.CTkButton(
            form, text="📤  Confirm Stock Out",
            fg_color="#C62828", hover_color="#B71C1C",
            width=300, height=40, font=("Arial", 14, "bold"),
            command=self._do_stock_out
        ).pack(pady=12)

    def _do_stock_out(self):
        pid = self.so_pid.get().strip()
        if not pid:
            messagebox.showwarning("⚠️", "Select a product from Current Stock tab first.")
            return
        try: pid = int(pid)
        except: messagebox.showerror("❌", "Invalid Product ID."); return

        if not messagebox.askyesno("Confirm Stock Out",
                                   f"Remove stock for Product ID {pid}?"):
            return

        success, result = stock_out(pid, self.so_qty.get(),
                                    self.so_notes.get(), self.so_batch.get())
        if success:
            messagebox.showinfo("✅ Stock Out", "Stock removed successfully!")
            self._clear_form([self.so_qty, self.so_batch, self.so_notes])
            self.refresh_dashboard()
            self._cs_load_all()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # TAB 4 — ADJUSTMENT
    # ==========================

    def _build_adjustment_tab(self):
        tab  = self.tabs.tab("🔧 Adjustment")
        form = ctk.CTkScrollableFrame(tab)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(form, text="🔧 Stock Adjustment (Physical Count)",
                     font=("Arial", 16, "bold")).pack(pady=(0,10))

        ctk.CTkLabel(form, text="💡 Enter the actual physical quantity counted. System will auto-calculate the difference.",
                     font=("Arial", 11), text_color="gray").pack(pady=(0,8))

        self.adj_pid   = self._ro_field(form, "Product ID")
        self.adj_name  = self._ro_field(form, "Product Name")
        self.adj_qty   = self._form_field(form, "Actual Physical Count *")
        self.adj_notes = self._form_field(form, "Reason for Adjustment")

        ctk.CTkButton(
            form, text="🔧  Apply Adjustment",
            fg_color="#E65100", hover_color="#BF360C",
            width=300, height=40, font=("Arial", 14, "bold"),
            command=self._do_adjustment
        ).pack(pady=12)

    def _do_adjustment(self):
        pid = self.adj_pid.get().strip()
        if not pid:
            messagebox.showwarning("⚠️", "Select a product from Current Stock tab first.")
            return
        try: pid = int(pid)
        except: messagebox.showerror("❌", "Invalid Product ID."); return

        if not messagebox.askyesno("Confirm Adjustment",
                                   "Apply stock adjustment? This will overwrite current quantity."):
            return

        success, result = stock_adjustment(pid, self.adj_qty.get(), self.adj_notes.get())
        if success:
            messagebox.showinfo("✅ Adjusted", result)
            self._clear_form([self.adj_qty, self.adj_notes])
            self.refresh_dashboard()
            self._cs_load_all()
        else:
            messagebox.showerror("❌ Error", result)

    # ==========================
    # TAB 5 — TRANSACTIONS
    # ==========================

    def _build_transactions_tab(self):
        tab = self.tabs.tab("📋 Transactions")

        # filter row
        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frow, text="Type:").pack(side="left", padx=(0,4))
        self.txn_type_var = ctk.StringVar(value="ALL")
        ctk.CTkOptionMenu(frow, variable=self.txn_type_var,
                          values=["ALL","IN","OUT","ADJUSTMENT"],
                          width=130).pack(side="left", padx=(0,10))

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.txn_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.txn_from.pack(side="left", padx=(0,10))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.txn_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.txn_to.pack(side="left", padx=(0,10))

        ctk.CTkButton(frow, text="🔍 Load", width=80,
                      command=self._load_transactions).pack(side="left", padx=(0,8))
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_transactions(clear=True)).pack(side="left")

        cols = ("Txn ID", "Date", "Product", "Category", "Unit",
                "Type", "Qty", "Batch", "Mfg Date", "Expiry",
                "Supplier", "Unit Cost", "Total Cost", "Notes")
        col_w = {
            "Txn ID":60, "Date":140, "Product":160, "Category":90,
            "Unit":55, "Type":90, "Qty":70, "Batch":90,
            "Mfg Date":90, "Expiry":90, "Supplier":120,
            "Unit Cost":90, "Total Cost":90, "Notes":160
        }
        self.txn_tree = self._make_tree(tab, cols, col_w)
        self.txn_tree.tag_configure("IN",         foreground="#81C784")
        self.txn_tree.tag_configure("OUT",        foreground="#EF9A9A")
        self.txn_tree.tag_configure("ADJUSTMENT", foreground="#FFD54F")

        self._load_transactions(clear=True)

    def _load_transactions(self, clear=False):
        if clear:
            self.txn_from.delete(0, "end")
            self.txn_to.delete(0, "end")
            self.txn_type_var.set("ALL")

        rows = get_transaction_history(
            transaction_type=self.txn_type_var.get(),
            date_from=self.txn_from.get().strip() or None,
            date_to=self.txn_to.get().strip() or None
        )
        for i in self.txn_tree.get_children():
            self.txn_tree.delete(i)

        for r in rows:
            ttype = r["transaction_type"]
            uc = float(r["unit_cost"])  if r["unit_cost"]  else 0.0
            tc = float(r["total_cost"]) if r["total_cost"] else 0.0
            self.txn_tree.insert("", "end", tags=(ttype,), values=(
                r["id"], r["transaction_date"], r["product_name"],
                r["category"] or "", r["unit"] or "",
                ttype, f"{float(r['quantity']):g}",
                r["batch_number"] or "", r["mfg_date"] or "",
                r["expiry_date"] or "", r["supplier"] or "",
                f"₹{uc:,.2f}", f"₹{tc:,.2f}", r["notes"] or ""
            ))

    # ==========================
    # TAB 6 — ALERTS
    # ==========================

    def _build_alerts_tab(self):
        tab = self.tabs.tab("⚠️ Alerts")

        ctk.CTkLabel(tab, text="⚠️  Stock Alerts",
                     font=("Arial", 16, "bold")).pack(pady=(10,4))

        ctk.CTkButton(tab, text="🔄 Refresh Alerts",
                      command=self._load_alerts,
                      fg_color="#E65100").pack(pady=(0,8))

        # Low Stock
        ctk.CTkLabel(tab, text="🟡 Low Stock (≤ 10 units)",
                     font=("Arial", 13, "bold"), text_color="#FF9800").pack(anchor="w", padx=15)

        low_cols = ("ID","Product","Category","Unit","Stock","Buy Price")
        self.low_tree = self._make_tree(tab, low_cols,
            {"ID":45,"Product":200,"Category":120,"Unit":70,"Stock":80,"Buy Price":100},
            height=6)
        self.low_tree.tag_configure("low", foreground="#FF9800")

        # Out of Stock
        ctk.CTkLabel(tab, text="🔴 Out of Stock (0 units)",
                     font=("Arial", 13, "bold"), text_color="#F44336").pack(anchor="w", padx=15, pady=(10,0))

        out_cols = ("ID","Product","Category","Unit","Stock")
        self.out_tree = self._make_tree(tab, out_cols,
            {"ID":45,"Product":200,"Category":120,"Unit":70,"Stock":80},
            height=6)
        self.out_tree.tag_configure("out", foreground="#F44336")

        self._load_alerts()

    def _load_alerts(self):
        # low stock
        for i in self.low_tree.get_children(): self.low_tree.delete(i)
        for r in get_low_stock(threshold=10):
            self.low_tree.insert("", "end", tags=("low",), values=(
                r["id"], r["name"], r["category"], r["unit"],
                f"{float(r['quantity']):g}", f"₹{float(r['buying_price']):,.2f}"
            ))

        # out of stock
        for i in self.out_tree.get_children(): self.out_tree.delete(i)
        for r in get_out_of_stock():
            self.out_tree.insert("", "end", tags=("out",), values=(
                r["id"], r["name"], r["category"], r["unit"],
                f"{float(r['quantity']):g}"
            ))

    # ==========================
    # REFRESH DASHBOARD STATS
    # ==========================

    def refresh_dashboard(self):
        stats = get_inventory_stats()
        self.stat_total.configure(text=str(stats["total_products"]))
        self.stat_value.configure(text=f"₹{stats['total_value']:,.2f}")
        self.stat_low.configure(text=str(stats["low_stock_count"]))
        self.stat_out.configure(text=str(stats["out_of_stock_count"]))
        self._cs_load_all()

    # ==========================
    # HELPERS
    # ==========================

    def _make_tree(self, parent, cols, col_widths, height=10):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Inv.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Inv.Treeview.Heading",
            background="#1B5E20", foreground="white", font=("Arial", 11,"bold"))
        style.map("Inv.Treeview", background=[("selected","#388E3C")])

        container = tk.Frame(parent, bg="#2b2b2b")
        container.pack(fill="both", expand=True, padx=10, pady=5)

        tree = ttk.Treeview(container, columns=cols, show="headings",
                            style="Inv.Treeview", selectmode="browse", height=height)
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
        return tree

    def _form_field(self, parent, label):
        ctk.CTkLabel(parent, text=label, anchor="w").pack(fill="x", padx=8)
        e = ctk.CTkEntry(parent, width=400, placeholder_text=label)
        e.pack(padx=8, pady=(0,8))
        return e

    def _ro_field(self, parent, label):
        ctk.CTkLabel(parent, text=label, anchor="w").pack(fill="x", padx=8)
        e = ctk.CTkEntry(parent, width=400, placeholder_text=label, state="readonly")
        e.pack(padx=8, pady=(0,8))
        return e

    def _clear_form(self, fields):
        for f in fields:
            f.delete(0, "end")