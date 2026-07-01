import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime

from models.sales import (
    ensure_sales_tables,
    create_bill,
    get_all_bills,
    get_bill_by_id,
    get_bill_items,
    cancel_bill,
    record_due_payment,
    get_sales_summary,
    get_best_selling_products,
    get_daily_sales,
    get_payment_mode_summary,
    get_profit_report,
    get_active_customers_for_sales,
    get_all_products_for_sales,
    search_products_for_sale
)

PAYMENT_MODES = ["Cash", "UPI", "Card", "Bank Transfer", "Cheque", "Credit"]


class SalesPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sales & Billing")
        self.geometry("1400x860")
        self.resizable(True, True)

        ensure_sales_tables()

        # cart state
        self._cart       = []          # list of item dicts
        self._customer_id   = None
        self._customer_name = "Walk-in Customer"
        self._customer_mob  = ""

        self._build_ui()
        self._refresh_dashboard()

    # ════════════════════════════════════════
    # BUILD UI
    # ════════════════════════════════════════

    def _build_ui(self):
        # Title
        ctk.CTkLabel(
            self, text="🛒  SALES & BILLING",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        # Dashboard stats bar
        dash = ctk.CTkFrame(self, height=58)
        dash.pack(fill="x", padx=20, pady=(0, 6))
        dash.pack_propagate(False)

        self.s_bills    = self._stat(dash, "🧾 Today's Bills",    "0",   "#1565C0")
        self.s_revenue  = self._stat(dash, "💰 Today's Revenue",  "₹0",  "#2E7D32")
        self.s_collect  = self._stat(dash, "✅ Collected",         "₹0",  "#00695C")
        self.s_due      = self._stat(dash, "⏳ Due",               "₹0",  "#B71C1C")

        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for t in ["🧾 New Bill", "📋 Sales History",
                  "📊 Analytics", "💳 Due Payments"]:
            self.tabs.add(t)

        self._build_new_bill_tab()
        self._build_history_tab()
        self._build_analytics_tab()
        self._build_due_tab()

    def _stat(self, parent, label, val, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=6, pady=6)
        ctk.CTkLabel(f, text=label, font=("Arial", 11), text_color="white").pack(pady=(3,0))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 14, "bold"), text_color="white")
        lbl.pack(pady=(0,3))
        return lbl

    # ════════════════════════════════════════
    # TAB 1 — NEW BILL
    # ════════════════════════════════════════

    def _build_new_bill_tab(self):
        tab = self.tabs.tab("🧾 New Bill")

        # Three columns: customer+product | cart | totals
        tab.columnconfigure(0, weight=2)
        tab.columnconfigure(1, weight=3)
        tab.columnconfigure(2, weight=2)
        tab.rowconfigure(0, weight=1)

        # ── LEFT: Customer + Product search ───────────────
        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,4), pady=4)

        # Customer section
        ctk.CTkLabel(left, text="👤 Customer",
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=(8,2))

        crow = ctk.CTkFrame(left, fg_color="transparent")
        crow.pack(fill="x", padx=10, pady=(0,4))
        self.cust_search = ctk.CTkEntry(crow, placeholder_text="Search customer name/mobile…")
        self.cust_search.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(crow, text="🔍", width=34,
                      command=self._search_customer).pack(side="left", padx=(4,0))

        self.cust_listbox = tk.Listbox(left, height=4, bg="#3a3a3a", fg="white",
                                       font=("Arial", 11), selectbackground="#1976D2")
        self.cust_listbox.pack(fill="x", padx=10, pady=(0,2))
        self.cust_listbox.bind("<<ListboxSelect>>", self._select_customer)

        ctk.CTkButton(
            left, text="🚶 Walk-in Customer", height=30,
            fg_color="#607D8B", hover_color="#37474F",
            command=self._set_walkin
        ).pack(fill="x", padx=10, pady=(0,6))

        self.lbl_customer = ctk.CTkLabel(
            left, text="👤 Walk-in Customer",
            font=("Arial", 12, "bold"), text_color="#1976D2"
        )
        self.lbl_customer.pack(padx=10, pady=(0,8))

        ctk.CTkLabel(left, text="─"*35, text_color="gray").pack()

        # Product search
        ctk.CTkLabel(left, text="🧈 Product",
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=(6,2))

        prow = ctk.CTkFrame(left, fg_color="transparent")
        prow.pack(fill="x", padx=10, pady=(0,4))
        self.prod_search = ctk.CTkEntry(prow, placeholder_text="Search product name…")
        self.prod_search.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(prow, text="🔍", width=34,
                      command=self._search_product).pack(side="left", padx=(4,0))

        self.prod_listbox = tk.Listbox(left, height=6, bg="#3a3a3a", fg="white",
                                       font=("Arial", 11), selectbackground="#2E7D32")
        self.prod_listbox.pack(fill="x", padx=10, pady=(0,4))
        self.prod_listbox.bind("<<ListboxSelect>>", self._select_product)

        # Selected product info
        self.lbl_product = ctk.CTkLabel(
            left, text="No product selected",
            font=("Arial", 11), text_color="gray"
        )
        self.lbl_product.pack(padx=10)

        # Qty + price row
        qrow = ctk.CTkFrame(left, fg_color="transparent")
        qrow.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(qrow, text="Qty:").pack(side="left")
        self.entry_qty = ctk.CTkEntry(qrow, width=70, placeholder_text="1")
        self.entry_qty.pack(side="left", padx=4)

        ctk.CTkLabel(qrow, text="Price:").pack(side="left")
        self.entry_price = ctk.CTkEntry(qrow, width=80, placeholder_text="0.00")
        self.entry_price.pack(side="left", padx=4)

        ctk.CTkLabel(qrow, text="Disc:").pack(side="left")
        self.entry_item_disc = ctk.CTkEntry(qrow, width=65, placeholder_text="0")
        self.entry_item_disc.pack(side="left", padx=4)

        ctk.CTkButton(
            left, text="➕  Add to Cart",
            fg_color="#2E7D32", hover_color="#1B5E20",
            height=36, font=("Arial", 13, "bold"),
            command=self._add_to_cart
        ).pack(fill="x", padx=10, pady=6)

        # ── MIDDLE: Cart ───────────────────────────────────
        mid = ctk.CTkFrame(tab)
        mid.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        ctk.CTkLabel(mid, text="🛒 Cart",
                     font=("Arial", 13, "bold")).pack(pady=(8,4))

        cart_cols = ("Product", "Qty", "Unit", "Price", "Disc", "Total")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cart.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Cart.Treeview.Heading",
            background="#1B5E20", foreground="white", font=("Arial", 11,"bold"))
        style.map("Cart.Treeview", background=[("selected","#388E3C")])

        cart_container = tk.Frame(mid, bg="#2b2b2b")
        cart_container.pack(fill="both", expand=True, padx=8, pady=4)

        self.cart_tree = ttk.Treeview(cart_container, columns=cart_cols,
                                      show="headings", style="Cart.Treeview",
                                      selectmode="browse")
        cw = {"Product":180,"Qty":55,"Unit":55,"Price":80,"Disc":60,"Total":90}
        for col in cart_cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=cw.get(col,80), anchor="center")

        vsb = ttk.Scrollbar(cart_container, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb.set)
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        cart_container.rowconfigure(0, weight=1)
        cart_container.columnconfigure(0, weight=1)

        brow = ctk.CTkFrame(mid, fg_color="transparent")
        brow.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(brow, text="🗑️ Remove Selected", width=160,
                      fg_color="#C62828", hover_color="#B71C1C",
                      command=self._remove_from_cart).pack(side="left", padx=(0,6))
        ctk.CTkButton(brow, text="🧹 Clear Cart", width=120,
                      fg_color="#607D8B", hover_color="#37474F",
                      command=self._clear_cart).pack(side="left")

        # ── RIGHT: Totals + Payment ────────────────────────
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=2, sticky="nsew", padx=(4,0), pady=4)

        scroll = ctk.CTkScrollableFrame(right)
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="💰 Payment",
                     font=("Arial", 13, "bold")).pack(pady=(8,4))

        # Totals display
        self.lbl_subtotal = self._total_row(scroll, "Subtotal:", "₹0.00")
        self.lbl_discount = self._total_row(scroll, "Discount:", "₹0.00")
        self.lbl_gst      = self._total_row(scroll, "GST:",      "₹0.00")

        ctk.CTkLabel(scroll, text="─"*28, text_color="gray").pack()

        self.lbl_grand = ctk.CTkLabel(
            scroll, text="Grand Total: ₹0.00",
            font=("Arial", 15, "bold"), text_color="#1976D2"
        )
        self.lbl_grand.pack(pady=4)

        ctk.CTkLabel(scroll, text="─"*28, text_color="gray").pack()

        # Discount
        ctk.CTkLabel(scroll, text="Discount", anchor="w").pack(fill="x", padx=10)
        drow = ctk.CTkFrame(scroll, fg_color="transparent")
        drow.pack(fill="x", padx=10, pady=(0,6))
        self.entry_discount = ctk.CTkEntry(drow, width=90, placeholder_text="0")
        self.entry_discount.pack(side="left")
        self.disc_type_var = ctk.StringVar(value="flat")
        ctk.CTkOptionMenu(drow, variable=self.disc_type_var,
                          values=["flat","percent"], width=80).pack(side="left", padx=4)

        # GST
        ctk.CTkLabel(scroll, text="GST %", anchor="w").pack(fill="x", padx=10)
        self.entry_gst = ctk.CTkEntry(scroll, width=180, placeholder_text="0")
        self.entry_gst.pack(padx=10, pady=(0,6))

        ctk.CTkButton(scroll, text="🔄 Recalculate", height=30,
                      command=self._recalculate).pack(fill="x", padx=10, pady=(0,8))

        # Payment mode
        ctk.CTkLabel(scroll, text="Payment Mode", anchor="w").pack(fill="x", padx=10)
        self.pay_mode_var = ctk.StringVar(value="Cash")
        ctk.CTkOptionMenu(scroll, variable=self.pay_mode_var,
                          values=PAYMENT_MODES, width=180).pack(padx=10, pady=(0,6))

        # Paid amount
        ctk.CTkLabel(scroll, text="Paid Amount (₹)", anchor="w").pack(fill="x", padx=10)
        self.entry_paid = ctk.CTkEntry(scroll, width=180, placeholder_text="0.00")
        self.entry_paid.pack(padx=10, pady=(0,4))

        self.lbl_due_display = ctk.CTkLabel(
            scroll, text="Due: ₹0.00",
            font=("Arial", 13, "bold"), text_color="#E53935"
        )
        self.lbl_due_display.pack(pady=4)

        self.entry_paid.bind("<KeyRelease>", lambda e: self._update_due_label())

        # Notes
        ctk.CTkLabel(scroll, text="Notes", anchor="w").pack(fill="x", padx=10)
        self.entry_notes = ctk.CTkEntry(scroll, width=180, placeholder_text="Optional notes")
        self.entry_notes.pack(padx=10, pady=(0,8))

        # Create Bill button
        ctk.CTkButton(
            scroll, text="✅  CREATE BILL",
            fg_color="#1565C0", hover_color="#0D47A1",
            height=44, font=("Arial", 15, "bold"),
            command=self._create_bill
        ).pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(
            scroll, text="🖨️  Print Last Bill",
            fg_color="#6A1B9A", hover_color="#4A148C",
            height=36, font=("Arial", 12),
            command=self._print_last_bill
        ).pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(
            scroll, text="🔄  New Bill",
            fg_color="#607D8B", hover_color="#37474F",
            height=34,
            command=self._new_bill
        ).pack(fill="x", padx=10, pady=4)

        # store last bill id
        self._last_bill_id = None

        # load products initially
        self._load_all_products()

    # ════════════════════════════════════════
    # CUSTOMER SEARCH
    # ════════════════════════════════════════

    def _search_customer(self):
        kw = self.cust_search.get().strip()
        customers = get_active_customers_for_sales()
        self.cust_listbox.delete(0, "end")
        self._customers_cache = []
        for c in customers:
            if not kw or kw.lower() in c["name"].lower() or kw in (c["mobile"] or ""):
                self.cust_listbox.insert("end", f"{c['id']} | {c['name']} | {c['mobile']}")
                self._customers_cache.append(c)

    def _select_customer(self, event):
        sel = self.cust_listbox.curselection()
        if not sel: return
        c = self._customers_cache[sel[0]]
        self._customer_id   = c["id"]
        self._customer_name = c["name"]
        self._customer_mob  = c["mobile"] or ""
        bal = float(c["current_balance"])
        self.lbl_customer.configure(
            text=f"👤 {c['name']} | 📱 {c['mobile']} | Due: ₹{bal:,.2f}",
            text_color="#1976D2"
        )

    def _set_walkin(self):
        self._customer_id   = None
        self._customer_name = "Walk-in Customer"
        self._customer_mob  = ""
        self.lbl_customer.configure(text="👤 Walk-in Customer", text_color="#607D8B")
        self.cust_listbox.selection_clear(0, "end")

    # ════════════════════════════════════════
    # PRODUCT SEARCH
    # ════════════════════════════════════════

    def _load_all_products(self):
        products = get_all_products_for_sales()
        self.prod_listbox.delete(0, "end")
        self._products_cache = []
        for p in products:
            self.prod_listbox.insert(
                "end", f"{p['name']} | {p['category']} | ₹{float(p['selling_price']):,.2f} | Stock:{float(p['quantity']):g}"
            )
            self._products_cache.append(p)

    def _search_product(self):
        kw = self.prod_search.get().strip()
        if not kw:
            self._load_all_products(); return
        products = search_products_for_sale(kw)
        self.prod_listbox.delete(0, "end")
        self._products_cache = []
        for p in products:
            self.prod_listbox.insert(
                "end", f"{p['name']} | {p['category']} | ₹{float(p['selling_price']):,.2f} | Stock:{float(p['quantity']):g}"
            )
            self._products_cache.append(p)

    def _select_product(self, event):
        sel = self.prod_listbox.curselection()
        if not sel: return
        p = self._products_cache[sel[0]]
        self._selected_product = p
        self.lbl_product.configure(
            text=f"✅ {p['name']} | Unit: {p['unit']} | Stock: {float(p['quantity']):g}",
            text_color="#2E7D32"
        )
        self.entry_price.delete(0, "end")
        self.entry_price.insert(0, str(float(p["selling_price"])))
        self.entry_qty.delete(0, "end")
        self.entry_qty.insert(0, "1")
        self.entry_item_disc.delete(0, "end")
        self.entry_item_disc.insert(0, "0")

    # ════════════════════════════════════════
    # CART OPERATIONS
    # ════════════════════════════════════════

    def _add_to_cart(self):
        if not hasattr(self, "_selected_product"):
            messagebox.showwarning("⚠️", "Please select a product first.")
            return

        try:
            qty   = float(self.entry_qty.get()   or 1)
            price = float(self.entry_price.get() or 0)
            disc  = float(self.entry_item_disc.get() or 0)
            if qty <= 0:   raise ValueError("qty")
            if price <= 0: raise ValueError("price")
        except ValueError:
            messagebox.showerror("❌", "Enter valid quantity and price.")
            return

        p = self._selected_product
        avail = float(p["quantity"])

        # check if already in cart and total qty
        already = sum(i["quantity"] for i in self._cart
                      if i.get("product_id") == p["id"])
        if already + qty > avail:
            messagebox.showerror(
                "❌ Insufficient Stock",
                f"Only {avail} {p['unit']} available. Already in cart: {already}"
            )
            return

        total = round((qty * price) - disc, 2)
        item  = {
            "product_id":   p["id"],
            "product_name": p["name"],
            "category":     p["category"],
            "unit":         p["unit"],
            "quantity":     qty,
            "unit_price":   price,
            "item_discount":disc,
            "total":        total
        }
        self._cart.append(item)
        self._refresh_cart()

    def _remove_from_cart(self):
        sel = self.cart_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a cart item to remove.")
            return
        idx = self.cart_tree.index(sel)
        self._cart.pop(idx)
        self._refresh_cart()

    def _clear_cart(self):
        if not self._cart: return
        if messagebox.askyesno("Clear Cart", "Remove all items from cart?"):
            self._cart = []
            self._refresh_cart()

    def _refresh_cart(self):
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        for item in self._cart:
            self.cart_tree.insert("", "end", values=(
                item["product_name"],
                f"{item['quantity']:g}",
                item["unit"],
                f"₹{item['unit_price']:,.2f}",
                f"₹{item['item_discount']:,.2f}",
                f"₹{item['total']:,.2f}"
            ))
        self._recalculate()

    def _recalculate(self):
        subtotal = sum(i["total"] for i in self._cart)

        try:
            disc = float(self.entry_discount.get() or 0)
        except: disc = 0.0
        try:
            gst_pct = float(self.entry_gst.get() or 0)
        except: gst_pct = 0.0

        if self.disc_type_var.get() == "percent":
            disc_amt = round(subtotal * disc / 100, 2)
        else:
            disc_amt = round(disc, 2)

        after  = round(subtotal - disc_amt, 2)
        gst_am = round(after * gst_pct / 100, 2)
        grand  = round(after + gst_am, 2)

        self.lbl_subtotal.configure(text=f"₹{subtotal:,.2f}")
        self.lbl_discount.configure(text=f"₹{disc_amt:,.2f}")
        self.lbl_gst.configure(text=f"₹{gst_am:,.2f}")
        self.lbl_grand.configure(text=f"Grand Total: ₹{grand:,.2f}")

        self._grand_total = grand
        self._update_due_label()

    def _update_due_label(self):
        try:
            paid = float(self.entry_paid.get() or 0)
        except: paid = 0.0
        due = round(getattr(self, "_grand_total", 0) - paid, 2)
        color = "#E53935" if due > 0 else "#43A047"
        self.lbl_due_display.configure(
            text=f"Due: ₹{due:,.2f}", text_color=color
        )

    # ════════════════════════════════════════
    # CREATE BILL
    # ════════════════════════════════════════

    def _create_bill(self):
        if not self._cart:
            messagebox.showwarning("⚠️ Empty Cart", "Add products to cart first.")
            return

        try:
            paid = float(self.entry_paid.get() or 0)
        except:
            messagebox.showerror("❌", "Enter valid paid amount."); return

        result = create_bill(
            self._customer_id,
            self._customer_name,
            self._customer_mob,
            self._cart,
            self.entry_discount.get() or 0,
            self.disc_type_var.get(),
            self.entry_gst.get() or 0,
            paid,
            self.pay_mode_var.get(),
            self.entry_notes.get()
        )

        if result[0]:
            _, bill_id, inv_no = result
            self._last_bill_id = bill_id
            due = round(getattr(self, "_grand_total", 0) - paid, 2)
            msg = (f"✅ Bill Created!\n\n"
                   f"Invoice: {inv_no}\n"
                   f"Customer: {self._customer_name}\n"
                   f"Grand Total: ₹{getattr(self,'_grand_total',0):,.2f}\n"
                   f"Paid: ₹{paid:,.2f}\n"
                   f"Due: ₹{due:,.2f}")
            messagebox.showinfo("✅ Bill Created", msg)
            self._refresh_dashboard()
            self._load_history()
            self._new_bill()
        else:
            messagebox.showerror("❌ Error", result[1])

    def _new_bill(self):
        self._cart = []
        self._customer_id   = None
        self._customer_name = "Walk-in Customer"
        self._customer_mob  = ""
        self._grand_total   = 0.0
        self.lbl_customer.configure(text="👤 Walk-in Customer", text_color="#607D8B")
        for e in [self.entry_discount, self.entry_gst,
                  self.entry_paid, self.entry_notes]:
            e.delete(0, "end")
        self.disc_type_var.set("flat")
        self.pay_mode_var.set("Cash")
        self._refresh_cart()
        self.lbl_product.configure(text="No product selected", text_color="gray")
        self.cust_listbox.selection_clear(0, "end")
        self.lbl_due_display.configure(text="Due: ₹0.00", text_color="#E53935")
        self._load_all_products()
        if hasattr(self, "_selected_product"):
            del self._selected_product

    def _print_last_bill(self):
        if not self._last_bill_id:
            messagebox.showinfo("ℹ️", "No bill created yet in this session.")
            return
        self._show_bill_preview(self._last_bill_id)

    # ════════════════════════════════════════
    # TAB 2 — SALES HISTORY
    # ════════════════════════════════════════

    def _build_history_tab(self):
        tab = self.tabs.tab("📋 Sales History")

        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frow, text="Search:").pack(side="left", padx=(0,4))
        self.hist_search = ctk.CTkEntry(frow, width=180, placeholder_text="Invoice/Customer…")
        self.hist_search.pack(side="left", padx=(0,8))

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.hist_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.hist_from.pack(side="left", padx=(0,8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.hist_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.hist_to.pack(side="left", padx=(0,8))

        self.hist_status_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(frow, variable=self.hist_status_var,
                          values=["All","Paid","Partial","Due","Cancelled"],
                          width=110).pack(side="left", padx=(0,8))

        ctk.CTkButton(frow, text="🔍 Search", width=90,
                      command=self._load_history).pack(side="left", padx=(0,6))
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_history(clear=True)).pack(side="left")

        hist_cols = ("ID","Invoice","Customer","Mobile","Date",
                     "Subtotal","Discount","GST","Total","Paid","Due","Mode","Status")
        cw = {"ID":40,"Invoice":130,"Customer":140,"Mobile":100,"Date":130,
              "Subtotal":90,"Discount":80,"GST":70,"Total":90,
              "Paid":80,"Due":80,"Mode":90,"Status":80}

        style = ttk.Style()
        style.configure("Hist.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Hist.Treeview.Heading",
            background="#1565C0", foreground="white", font=("Arial", 11,"bold"))
        style.map("Hist.Treeview", background=[("selected","#1976D2")])

        hc = tk.Frame(tab, bg="#2b2b2b")
        hc.pack(fill="both", expand=True, padx=10, pady=4)

        self.hist_tree = ttk.Treeview(hc, columns=hist_cols, show="headings",
                                      style="Hist.Treeview", selectmode="browse")
        for col in hist_cols:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=cw.get(col,90), anchor="center")

        vsb = ttk.Scrollbar(hc, orient="vertical",   command=self.hist_tree.yview)
        hsb = ttk.Scrollbar(hc, orient="horizontal", command=self.hist_tree.xview)
        self.hist_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.hist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        hc.rowconfigure(0, weight=1); hc.columnconfigure(0, weight=1)

        self.hist_tree.tag_configure("Paid",      foreground="#81C784")
        self.hist_tree.tag_configure("Partial",   foreground="#FFD54F")
        self.hist_tree.tag_configure("Due",       foreground="#EF9A9A")
        self.hist_tree.tag_configure("Cancelled", foreground="#757575")

        # action buttons
        arow = ctk.CTkFrame(tab, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(arow, text="👁️ View Bill", width=120,
                      command=self._view_selected_bill).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="🖨️ Print Bill", width=120,
                      fg_color="#6A1B9A", hover_color="#4A148C",
                      command=self._print_selected_bill).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="❌ Cancel Bill", width=120,
                      fg_color="#C62828", hover_color="#B71C1C",
                      command=self._cancel_selected_bill).pack(side="left", padx=4)

        self._load_history()

    def _load_history(self, clear=False):
        if clear:
            self.hist_from.delete(0,"end")
            self.hist_to.delete(0,"end")
            self.hist_search.delete(0,"end")
            self.hist_status_var.set("All")

        rows = get_all_bills(
            date_from=self.hist_from.get().strip() or None,
            date_to=self.hist_to.get().strip() or None,
            status=self.hist_status_var.get(),
            search=self.hist_search.get().strip() or None
        )
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
        for r in rows:
            status = r["status"]
            self.hist_tree.insert("", "end", tags=(status,), values=(
                r["id"], r["invoice_number"], r["customer_name"],
                r["customer_mobile"] or "", r["bill_date"],
                f"₹{float(r['subtotal']):,.2f}",
                f"₹{float(r['discount']):,.2f}",
                f"₹{float(r['gst_amount']):,.2f}",
                f"₹{float(r['grand_total']):,.2f}",
                f"₹{float(r['paid_amount']):,.2f}",
                f"₹{float(r['due_amount']):,.2f}",
                r["payment_mode"], status
            ))

    def _get_selected_bill_id(self):
        sel = self.hist_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a bill first.")
            return None
        return int(self.hist_tree.item(sel, "values")[0])

    def _view_selected_bill(self):
        bid = self._get_selected_bill_id()
        if bid: self._show_bill_preview(bid)

    def _print_selected_bill(self):
        bid = self._get_selected_bill_id()
        if bid: self._show_bill_preview(bid)

    def _cancel_selected_bill(self):
        bid = self._get_selected_bill_id()
        if not bid: return
        if not messagebox.askyesno("⚠️ Cancel Bill",
                                   f"Cancel bill ID {bid}?\nStock will be restored."):
            return
        success, msg = cancel_bill(bid)
        if success:
            messagebox.showinfo("✅", msg)
            self._load_history()
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌", msg)

    def _show_bill_preview(self, bill_id):
        bill  = get_bill_by_id(bill_id)
        items = get_bill_items(bill_id)
        if not bill: return

        win = ctk.CTkToplevel(self)
        win.title(f"Invoice — {bill['invoice_number']}")
        win.geometry("560x700")
        win.resizable(False, False)

        txt = ctk.CTkTextbox(win, font=("Courier", 12))
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        lines = [
            "=" * 52,
            "          🐄  DAIRY ERP SYSTEM",
            "=" * 52,
            f"Invoice No : {bill['invoice_number']}",
            f"Date       : {bill['bill_date']}",
            f"Customer   : {bill['customer_name']}",
            f"Mobile     : {bill['customer_mobile'] or 'N/A'}",
            "-" * 52,
            f"{'Product':<22} {'Qty':>5} {'Price':>8} {'Disc':>6} {'Total':>8}",
            "-" * 52,
        ]
        for item in items:
            lines.append(
                f"{item['product_name'][:22]:<22} "
                f"{float(item['quantity']):>5.2f} "
                f"{float(item['unit_price']):>8.2f} "
                f"{float(item['discount']):>6.2f} "
                f"{float(item['total']):>8.2f}"
            )
        lines += [
            "-" * 52,
            f"{'Subtotal':>42} : ₹{float(bill['subtotal']):>8.2f}",
            f"{'Discount':>42} : ₹{float(bill['discount']):>8.2f}",
            f"{'GST':>42} : ₹{float(bill['gst_amount']):>8.2f}",
            "=" * 52,
            f"{'GRAND TOTAL':>42} : ₹{float(bill['grand_total']):>8.2f}",
            f"{'Paid':>42} : ₹{float(bill['paid_amount']):>8.2f}",
            f"{'Due':>42} : ₹{float(bill['due_amount']):>8.2f}",
            "=" * 52,
            f"Payment Mode : {bill['payment_mode']}",
            f"Status       : {bill['status']}",
            "=" * 52,
            "      Thank you for your business! 🙏",
            "=" * 52,
        ]
        txt.insert("end", "\n".join(lines))
        txt.configure(state="disabled")

        ctk.CTkButton(
            win, text="🖨️ Print (Copy to Clipboard)",
            command=lambda: [win.clipboard_clear(),
                             win.clipboard_append("\n".join(lines)),
                             messagebox.showinfo("📋 Copied", "Bill copied to clipboard!")]
        ).pack(pady=6)

    # ════════════════════════════════════════
    # TAB 3 — ANALYTICS
    # ════════════════════════════════════════

    def _build_analytics_tab(self):
        tab = self.tabs.tab("📊 Analytics")

        arow = ctk.CTkFrame(tab, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(arow, text="From:").pack(side="left")
        self.an_from = ctk.CTkEntry(arow, width=120, placeholder_text="YYYY-MM-DD")
        self.an_from.pack(side="left", padx=4)
        ctk.CTkLabel(arow, text="To:").pack(side="left")
        self.an_to = ctk.CTkEntry(arow, width=120, placeholder_text="YYYY-MM-DD")
        self.an_to.pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📊 Load Analytics", width=140,
                      command=self._load_analytics).pack(side="left", padx=8)

        self.an_tabs = ctk.CTkTabview(tab)
        self.an_tabs.pack(fill="both", expand=True, padx=10, pady=4)
        for t in ["🏆 Best Sellers", "💹 Profit Report", "💳 Payment Modes"]:
            self.an_tabs.add(t)

        # Best sellers table
        bs_cols = ("Product","Qty Sold","Revenue","Bills")
        self.bs_tree = self._make_small_tree(
            self.an_tabs.tab("🏆 Best Sellers"), bs_cols,
            {"Product":220,"Qty Sold":90,"Revenue":110,"Bills":70})

        # Profit table
        pr_cols = ("Product","Qty Sold","Revenue","Cost","Profit","Margin %")
        self.pr_tree = self._make_small_tree(
            self.an_tabs.tab("💹 Profit Report"), pr_cols,
            {"Product":200,"Qty Sold":90,"Revenue":100,"Cost":100,"Profit":100,"Margin %":90})
        self.pr_tree.tag_configure("profit",  foreground="#81C784")
        self.pr_tree.tag_configure("loss",    foreground="#EF9A9A")

        # Payment mode table
        pm_cols = ("Payment Mode","Count","Total")
        self.pm_tree = self._make_small_tree(
            self.an_tabs.tab("💳 Payment Modes"), pm_cols,
            {"Payment Mode":200,"Count":100,"Total":150})

        self._load_analytics()

    def _load_analytics(self):
        df = self.an_from.get().strip() or None
        dt = self.an_to.get().strip() or None

        # best sellers
        for i in self.bs_tree.get_children(): self.bs_tree.delete(i)
        for r in get_best_selling_products():
            self.bs_tree.insert("", "end", values=(
                r["product_name"],
                f"{float(r['total_qty']):g}",
                f"₹{float(r['total_revenue']):,.2f}",
                r["num_bills"]
            ))

        # profit
        for i in self.pr_tree.get_children(): self.pr_tree.delete(i)
        for r in get_profit_report(df, dt):
            rev    = float(r["revenue"])
            cost   = float(r["cost"]) if r["cost"] else 0.0
            profit = float(r["profit"]) if r["profit"] else 0.0
            margin = round(profit / rev * 100, 1) if rev > 0 else 0.0
            tag    = "profit" if profit >= 0 else "loss"
            self.pr_tree.insert("", "end", tags=(tag,), values=(
                r["product_name"],
                f"{float(r['qty_sold']):g}",
                f"₹{rev:,.2f}",
                f"₹{cost:,.2f}",
                f"₹{profit:,.2f}",
                f"{margin}%"
            ))

        # payment modes
        for i in self.pm_tree.get_children(): self.pm_tree.delete(i)
        for r in get_payment_mode_summary():
            self.pm_tree.insert("", "end", values=(
                r["payment_mode"], r["count"],
                f"₹{float(r['total']):,.2f}"
            ))

    # ════════════════════════════════════════
    # TAB 4 — DUE PAYMENTS
    # ════════════════════════════════════════

    def _build_due_tab(self):
        tab = self.tabs.tab("💳 Due Payments")

        ctk.CTkLabel(tab, text="💳  Collect Due Payments",
                     font=("Arial", 15, "bold")).pack(pady=(10,4))

        ctk.CTkButton(tab, text="🔄 Load Due Bills",
                      command=self._load_due_bills,
                      fg_color="#C62828").pack(pady=(0,6))

        due_cols = ("Bill ID","Invoice","Customer","Date","Total","Paid","Due","Status")
        self.due_tree = self._make_small_tree(tab, due_cols,
            {"Bill ID":55,"Invoice":130,"Customer":160,"Date":120,
             "Total":90,"Paid":80,"Due":90,"Status":80})
        self.due_tree.tag_configure("Partial", foreground="#FFD54F")
        self.due_tree.tag_configure("Due",     foreground="#EF9A9A")

        prow = ctk.CTkFrame(tab, fg_color="transparent")
        prow.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(prow, text="Amount to Collect (₹):").pack(side="left")
        self.due_amount_entry = ctk.CTkEntry(prow, width=150, placeholder_text="Enter amount")
        self.due_amount_entry.pack(side="left", padx=8)
        ctk.CTkButton(prow, text="✅ Record Payment", width=160,
                      fg_color="#2E7D32", hover_color="#1B5E20",
                      command=self._record_due_payment).pack(side="left")

        self._load_due_bills()

    def _load_due_bills(self):
        rows = get_all_bills(status="Due") + get_all_bills(status="Partial")
        for i in self.due_tree.get_children(): self.due_tree.delete(i)
        for r in rows:
            self.due_tree.insert("", "end", tags=(r["status"],), values=(
                r["id"], r["invoice_number"], r["customer_name"],
                r["bill_date"][:10],
                f"₹{float(r['grand_total']):,.2f}",
                f"₹{float(r['paid_amount']):,.2f}",
                f"₹{float(r['due_amount']):,.2f}",
                r["status"]
            ))

    def _record_due_payment(self):
        sel = self.due_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a due bill first.")
            return
        bid = int(self.due_tree.item(sel, "values")[0])
        amt = self.due_amount_entry.get().strip()
        if not amt:
            messagebox.showwarning("⚠️", "Enter amount to collect.")
            return
        success, msg = record_due_payment(bid, amt)
        if success:
            messagebox.showinfo("✅ Payment Recorded", msg)
            self.due_amount_entry.delete(0, "end")
            self._load_due_bills()
            self._load_history()
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌ Error", msg)

    # ════════════════════════════════════════
    # DASHBOARD REFRESH
    # ════════════════════════════════════════

    def _refresh_dashboard(self):
        today = datetime.now().strftime("%Y-%m-%d")
        s = get_sales_summary(date_from=today, date_to=today)
        self.s_bills.configure(text=str(s["total_bills"]))
        self.s_revenue.configure(text=f"₹{s['total_revenue']:,.2f}")
        self.s_collect.configure(text=f"₹{s['total_collected']:,.2f}")
        self.s_due.configure(text=f"₹{s['total_due']:,.2f}")

    # ════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════

    def _total_row(self, parent, label, val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=1)
        ctk.CTkLabel(row, text=label, font=("Arial", 12), width=100, anchor="w").pack(side="left")
        lbl = ctk.CTkLabel(row, text=val, font=("Arial", 12, "bold"), anchor="e")
        lbl.pack(side="right")
        return lbl

    def _make_small_tree(self, parent, cols, col_widths):
        style = ttk.Style()
        style.configure("An.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("An.Treeview.Heading",
            background="#1565C0", foreground="white", font=("Arial", 11,"bold"))
        style.map("An.Treeview", background=[("selected","#1976D2")])

        c = tk.Frame(parent, bg="#2b2b2b")
        c.pack(fill="both", expand=True, padx=8, pady=6)
        tree = ttk.Treeview(c, columns=cols, show="headings",
                            style="An.Treeview", selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col,100), anchor="center")
        vsb = ttk.Scrollbar(c, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(c, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        c.rowconfigure(0, weight=1); c.columnconfigure(0, weight=1)
        return tree