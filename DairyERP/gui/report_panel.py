import customtkinter as ctk
from tkinter import ttk
import tkinter as tk

from DairyERP.utils.report_exporter import export_to_excel, export_to_pdf

from models.employee import get_employees
from models.product import get_products
from models.customer import get_customers
from models.inventory import get_current_stock
from models.sales import get_all_bills, get_sales_summary
from models.cream import get_cream_entries
from models.ghee import get_ghee_entries


class ReportPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reports Center")
        self.geometry("1250x780")
        self.resizable(True, True)

        self._build_ui()

    # ════════════════════════════════════════
    # BUILD UI
    # ════════════════════════════════════════

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="📊  REPORTS CENTER",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            self, text="Generate, preview, and download reports in Excel or PDF",
            font=("Arial", 12), text_color="gray"
        ).pack(pady=(0, 10))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        report_names = [
            "👨‍💼 Employee", "🧈 Product", "👥 Customer",
            "📦 Inventory", "🛒 Sales", "🥛 Cream", "🫙 Ghee"
        ]
        for name in report_names:
            self.tabs.add(name)

        self._build_employee_tab()
        self._build_product_tab()
        self._build_customer_tab()
        self._build_inventory_tab()
        self._build_sales_tab()
        self._build_cream_tab()
        self._build_ghee_tab()

    # ════════════════════════════════════════
    # SHARED TREE BUILDER
    # ════════════════════════════════════════

    def _make_tree(self, parent, cols, col_widths, height=16):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rpt.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Rpt.Treeview.Heading",
            background="#1565C0", foreground="white", font=("Arial", 11, "bold"))
        style.map("Rpt.Treeview", background=[("selected", "#1976D2")])

        c = tk.Frame(parent, bg="#2b2b2b")
        c.pack(fill="both", expand=True, padx=15, pady=8)

        tree = ttk.Treeview(c, columns=cols, show="headings",
                            style="Rpt.Treeview", selectmode="browse", height=height)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 100), anchor="center")

        vsb = ttk.Scrollbar(c, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(c, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        c.rowconfigure(0, weight=1)
        c.columnconfigure(0, weight=1)
        return tree

    def _export_row(self, parent):
        """Returns a frame with Excel/PDF buttons — caller packs it."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        return row

    def _date_filter_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(10, 0))
        ctk.CTkLabel(row, text="From:").pack(side="left", padx=(0, 4))
        e_from = ctk.CTkEntry(row, width=120, placeholder_text="YYYY-MM-DD")
        e_from.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row, text="To:").pack(side="left", padx=(0, 4))
        e_to = ctk.CTkEntry(row, width=120, placeholder_text="YYYY-MM-DD")
        e_to.pack(side="left", padx=(0, 10))
        return row, e_from, e_to

    # ════════════════════════════════════════
    # 1) EMPLOYEE REPORT
    # ════════════════════════════════════════

    def _build_employee_tab(self):
        tab = self.tabs.tab("👨‍💼 Employee")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Employee Report",
                     font=("Arial", 15, "bold")).pack(side="left")

        ctk.CTkButton(top, text="🔄 Load / Preview", width=140,
                      command=self._load_employee_report).pack(side="right", padx=4)

        cols = ("ID","Name","Phone","Address","Role","Salary","Joining Date")
        cw = {"ID":40,"Name":150,"Phone":110,"Address":160,
              "Role":110,"Salary":90,"Joining Date":110}
        self.emp_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_employee_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_employee_pdf).pack(side="left", padx=4)

        self._load_employee_report()

    def _load_employee_report(self):
        self._emp_rows = get_employees()
        for i in self.emp_tree.get_children(): self.emp_tree.delete(i)
        for r in self._emp_rows:
            self.emp_tree.insert("", "end", values=(
                r["id"], r["name"], r["phone"], r["address"],
                r["role"], f"₹{float(r['salary']):,.2f}", r["joining_date"]
            ))

    def _export_employee_excel(self):
        export_to_excel(
            data=self._emp_rows,
            columns=["ID","Name","Phone","Address","Role","Salary","Joining Date"],
            keys=["id","name","phone","address","role","salary","joining_date"],
            filename="Employee_Report", title="Employee Report"
        )

    def _export_employee_pdf(self):
        export_to_pdf(
            data=self._emp_rows,
            columns=["ID","Name","Phone","Role","Salary","Joining Date"],
            keys=["id","name","phone","role","salary","joining_date"],
            filename="Employee_Report", title="Employee Report"
        )

    # ════════════════════════════════════════
    # 2) PRODUCT REPORT
    # ════════════════════════════════════════

    def _build_product_tab(self):
        tab = self.tabs.tab("🧈 Product")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Product Report",
                     font=("Arial", 15, "bold")).pack(side="left")
        ctk.CTkButton(top, text="🔄 Load / Preview", width=140,
                      command=self._load_product_report).pack(side="right", padx=4)

        cols = ("ID","Name","Category","Unit","Buy Price","Sell Price","Qty")
        cw = {"ID":40,"Name":160,"Category":100,"Unit":70,
              "Buy Price":90,"Sell Price":90,"Qty":70}
        self.prod_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_product_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_product_pdf).pack(side="left", padx=4)

        self._load_product_report()

    def _load_product_report(self):
        self._prod_rows = get_products()
        for i in self.prod_tree.get_children(): self.prod_tree.delete(i)
        for r in self._prod_rows:
            self.prod_tree.insert("", "end", values=(
                r["id"], r["name"], r["category"], r["unit"],
                f"₹{float(r['buying_price']):,.2f}",
                f"₹{float(r['selling_price']):,.2f}",
                f"{float(r['quantity']):g}"
            ))

    def _export_product_excel(self):
        export_to_excel(
            data=self._prod_rows,
            columns=["ID","Name","Category","Unit","Buying Price","Selling Price","Quantity"],
            keys=["id","name","category","unit","buying_price","selling_price","quantity"],
            filename="Product_Report", title="Product Report"
        )

    def _export_product_pdf(self):
        export_to_pdf(
            data=self._prod_rows,
            columns=["ID","Name","Category","Unit","Buying Price","Selling Price","Quantity"],
            keys=["id","name","category","unit","buying_price","selling_price","quantity"],
            filename="Product_Report", title="Product Report"
        )

    # ════════════════════════════════════════
    # 3) CUSTOMER REPORT
    # ════════════════════════════════════════

    def _build_customer_tab(self):
        tab = self.tabs.tab("👥 Customer")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Customer Report",
                     font=("Arial", 15, "bold")).pack(side="left")
        ctk.CTkButton(top, text="🔄 Load / Preview", width=140,
                      command=self._load_customer_report).pack(side="right", padx=4)

        cols = ("ID","Name","Mobile","Village/City","Type","Balance","Status")
        cw = {"ID":40,"Name":160,"Mobile":110,"Village/City":130,
              "Type":130,"Balance":90,"Status":80}
        self.cust_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_customer_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_customer_pdf).pack(side="left", padx=4)

        self._load_customer_report()

    def _load_customer_report(self):
        self._cust_rows = get_customers()
        for i in self.cust_tree.get_children(): self.cust_tree.delete(i)
        for r in self._cust_rows:
            self.cust_tree.insert("", "end", values=(
                r["id"], r["name"], r["mobile"], r["village_city"] or "—",
                r["customer_type"], f"₹{float(r['current_balance']):,.2f}", r["status"]
            ))

    def _export_customer_excel(self):
        export_to_excel(
            data=self._cust_rows,
            columns=["ID","Name","Mobile","Village/City","Type","Balance","Status"],
            keys=["id","name","mobile","village_city","customer_type","current_balance","status"],
            filename="Customer_Report", title="Customer Report"
        )

    def _export_customer_pdf(self):
        export_to_pdf(
            data=self._cust_rows,
            columns=["ID","Name","Mobile","Type","Balance","Status"],
            keys=["id","name","mobile","customer_type","current_balance","status"],
            filename="Customer_Report", title="Customer Report"
        )

    # ════════════════════════════════════════
    # 4) INVENTORY REPORT
    # ════════════════════════════════════════

    def _build_inventory_tab(self):
        tab = self.tabs.tab("📦 Inventory")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Inventory / Stock Report",
                     font=("Arial", 15, "bold")).pack(side="left")
        ctk.CTkButton(top, text="🔄 Load / Preview", width=140,
                      command=self._load_inventory_report).pack(side="right", padx=4)

        cols = ("ID","Name","Category","Unit","Stock","Buy Price","Sell Price","Stock Value")
        cw = {"ID":40,"Name":150,"Category":100,"Unit":65,"Stock":80,
              "Buy Price":90,"Sell Price":90,"Stock Value":100}
        self.inv_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_inventory_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_inventory_pdf).pack(side="left", padx=4)

        self._load_inventory_report()

    def _load_inventory_report(self):
        self._inv_rows = get_current_stock()
        for i in self.inv_tree.get_children(): self.inv_tree.delete(i)
        for r in self._inv_rows:
            qty = float(r["current_stock"])
            bp  = float(r["buying_price"])
            sv  = float(r["stock_value"])
            self.inv_tree.insert("", "end", values=(
                r["id"], r["name"], r["category"], r["unit"],
                f"{qty:g}", f"₹{bp:,.2f}",
                f"₹{float(r['selling_price']):,.2f}", f"₹{sv:,.2f}"
            ))

    def _export_inventory_excel(self):
        export_to_excel(
            data=self._inv_rows,
            columns=["ID","Name","Category","Unit","Stock","Buy Price","Sell Price","Stock Value"],
            keys=["id","name","category","unit","current_stock","buying_price","selling_price","stock_value"],
            filename="Inventory_Report", title="Inventory Report"
        )

    def _export_inventory_pdf(self):
        export_to_pdf(
            data=self._inv_rows,
            columns=["ID","Name","Category","Stock","Buy Price","Stock Value"],
            keys=["id","name","category","current_stock","buying_price","stock_value"],
            filename="Inventory_Report", title="Inventory Report"
        )

    # ════════════════════════════════════════
    # 5) SALES REPORT
    # ════════════════════════════════════════

    def _build_sales_tab(self):
        tab = self.tabs.tab("🛒 Sales")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Sales Report",
                     font=("Arial", 15, "bold")).pack(side="left")

        _, self.sales_from, self.sales_to = self._date_filter_row(tab)
        ctk.CTkButton(self.sales_from.master, text="🔄 Load / Preview", width=140,
                      command=self._load_sales_report).pack(side="left", padx=8)

        # summary cards
        cards = ctk.CTkFrame(tab)
        cards.pack(fill="x", padx=15, pady=8)
        self.s_bills   = self._stat(cards, "Total Bills",   "0",  "#1565C0")
        self.s_revenue = self._stat(cards, "Revenue",       "₹0", "#2E7D32")
        self.s_collect = self._stat(cards, "Collected",     "₹0", "#00695C")
        self.s_due     = self._stat(cards, "Due",           "₹0", "#B71C1C")

        cols = ("ID","Invoice","Customer","Date","Total","Paid","Due","Status")
        cw = {"ID":40,"Invoice":120,"Customer":140,"Date":120,
              "Total":90,"Paid":80,"Due":80,"Status":80}
        self.sales_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_sales_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_sales_pdf).pack(side="left", padx=4)

        self._load_sales_report()

    def _stat(self, parent, label, val, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=4, pady=4)
        ctk.CTkLabel(f, text=label, font=("Arial", 10), text_color="white").pack(pady=(4,0))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 13, "bold"), text_color="white")
        lbl.pack(pady=(0,4))
        return lbl

    def _load_sales_report(self):
        df = self.sales_from.get().strip() or None
        dt = self.sales_to.get().strip() or None

        self._sales_rows = get_all_bills(date_from=df, date_to=dt)
        s = get_sales_summary(date_from=df, date_to=dt)

        self.s_bills.configure(text=str(s["total_bills"]))
        self.s_revenue.configure(text=f"₹{s['total_revenue']:,.2f}")
        self.s_collect.configure(text=f"₹{s['total_collected']:,.2f}")
        self.s_due.configure(text=f"₹{s['total_due']:,.2f}")

        for i in self.sales_tree.get_children(): self.sales_tree.delete(i)
        for r in self._sales_rows:
            self.sales_tree.insert("", "end", values=(
                r["id"], r["invoice_number"], r["customer_name"],
                r["bill_date"][:16],
                f"₹{float(r['grand_total']):,.2f}",
                f"₹{float(r['paid_amount']):,.2f}",
                f"₹{float(r['due_amount']):,.2f}",
                r["status"]
            ))

    def _export_sales_excel(self):
        export_to_excel(
            data=self._sales_rows,
            columns=["ID","Invoice","Customer","Mobile","Date","Subtotal",
                     "Discount","GST","Total","Paid","Due","Mode","Status"],
            keys=["id","invoice_number","customer_name","customer_mobile","bill_date",
                  "subtotal","discount","gst_amount","grand_total","paid_amount",
                  "due_amount","payment_mode","status"],
            filename="Sales_Report", title="Sales Report"
        )

    def _export_sales_pdf(self):
        export_to_pdf(
            data=self._sales_rows,
            columns=["Invoice","Customer","Date","Total","Paid","Due","Status"],
            keys=["invoice_number","customer_name","bill_date",
                  "grand_total","paid_amount","due_amount","status"],
            filename="Sales_Report", title="Sales Report"
        )

    # ════════════════════════════════════════
    # 6) CREAM REPORT
    # ════════════════════════════════════════

    def _build_cream_tab(self):
        tab = self.tabs.tab("🥛 Cream")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Cream Production Report",
                     font=("Arial", 15, "bold")).pack(side="left")

        _, self.cream_from, self.cream_to = self._date_filter_row(tab)
        ctk.CTkButton(self.cream_from.master, text="🔄 Load / Preview", width=140,
                      command=self._load_cream_report).pack(side="left", padx=8)

        cols = ("ID","Date","Shift","Milk (L)","Cream (Kg)","→Ghee","→Sold","→Wasted","Supplier")
        cw = {"ID":40,"Date":100,"Shift":75,"Milk (L)":85,"Cream (Kg)":90,
              "→Ghee":75,"→Sold":75,"→Wasted":75,"Supplier":120}
        self.cream_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_cream_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_cream_pdf).pack(side="left", padx=4)

        self._load_cream_report()

    def _load_cream_report(self):
        df = self.cream_from.get().strip() or None
        dt = self.cream_to.get().strip() or None
        self._cream_rows = get_cream_entries(date_from=df, date_to=dt)

        for i in self.cream_tree.get_children(): self.cream_tree.delete(i)
        for r in self._cream_rows:
            self.cream_tree.insert("", "end", values=(
                r["id"], r["entry_date"], r["shift"],
                f"{float(r['milk_litres']):g}",
                f"{float(r['cream_kg']):g}",
                f"{float(r['cream_used_ghee']):g}",
                f"{float(r['cream_sold']):g}",
                f"{float(r['cream_wasted']):g}",
                r["supplier_name"] or "—"
            ))

    def _export_cream_excel(self):
        export_to_excel(
            data=self._cream_rows,
            columns=["ID","Date","Shift","Milk (L)","Fat %","Cream (Kg)",
                     "→Ghee","→Sold","→Wasted","Supplier","Employee"],
            keys=["id","entry_date","shift","milk_litres","fat_percent","cream_kg",
                  "cream_used_ghee","cream_sold","cream_wasted","supplier_name","employee_name"],
            filename="Cream_Production_Report", title="Cream Production Report"
        )

    def _export_cream_pdf(self):
        export_to_pdf(
            data=self._cream_rows,
            columns=["Date","Shift","Milk (L)","Cream (Kg)","→Ghee","→Sold","→Wasted"],
            keys=["entry_date","shift","milk_litres","cream_kg",
                  "cream_used_ghee","cream_sold","cream_wasted"],
            filename="Cream_Production_Report", title="Cream Production Report"
        )

    # ════════════════════════════════════════
    # 7) GHEE REPORT
    # ════════════════════════════════════════

    def _build_ghee_tab(self):
        tab = self.tabs.tab("🫙 Ghee")

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(top, text="Ghee Production Report",
                     font=("Arial", 15, "bold")).pack(side="left")

        _, self.ghee_from, self.ghee_to = self._date_filter_row(tab)
        ctk.CTkButton(self.ghee_from.master, text="🔄 Load / Preview", width=140,
                      command=self._load_ghee_report).pack(side="left", padx=8)

        cols = ("ID","Date","Shift","Cream Used","Ghee","Packed","→Sold","→Dist","→Wasted","Batch")
        cw = {"ID":40,"Date":100,"Shift":75,"Cream Used":85,"Ghee":75,
              "Packed":70,"→Sold":65,"→Dist":65,"→Wasted":70,"Batch":80}
        self.ghee_tree = self._make_tree(tab, cols, cw)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=150,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_ghee_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=150,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_ghee_pdf).pack(side="left", padx=4)

        self._load_ghee_report()

    def _load_ghee_report(self):
        df = self.ghee_from.get().strip() or None
        dt = self.ghee_to.get().strip() or None
        self._ghee_rows = get_ghee_entries(date_from=df, date_to=dt)

        for i in self.ghee_tree.get_children(): self.ghee_tree.delete(i)
        for r in self._ghee_rows:
            self.ghee_tree.insert("", "end", values=(
                r["id"], r["entry_date"], r["shift"],
                f"{float(r['cream_used_kg']):g}",
                f"{float(r['ghee_produced']):g}",
                f"{float(r['packaged_qty']):g}",
                f"{float(r['ghee_sold']):g}",
                f"{float(r['ghee_distributed']):g}",
                f"{float(r['ghee_wasted']):g}",
                r["batch_number"] or "—"
            ))

    def _export_ghee_excel(self):
        export_to_excel(
            data=self._ghee_rows,
            columns=["ID","Date","Shift","Cream Used","Ghee Produced",
                     "Packaged","Sold","Distributed","Wasted","Batch","Employee"],
            keys=["id","entry_date","shift","cream_used_kg","ghee_produced",
                  "packaged_qty","ghee_sold","ghee_distributed","ghee_wasted",
                  "batch_number","employee_name"],
            filename="Ghee_Production_Report", title="Ghee Production Report"
        )

    def _export_ghee_pdf(self):
        export_to_pdf(
            data=self._ghee_rows,
            columns=["Date","Shift","Cream Used","Ghee Produced","Sold","Distributed","Wasted"],
            keys=["entry_date","shift","cream_used_kg","ghee_produced",
                  "ghee_sold","ghee_distributed","ghee_wasted"],
            filename="Ghee_Production_Report", title="Ghee Production Report"
        )