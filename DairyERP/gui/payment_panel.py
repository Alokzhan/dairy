import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime

from models.payment import (
    ensure_payment_tables,
    get_customer_payments,
    get_customer_dues_summary,
    record_salary_payment,
    get_salary_payments,
    delete_salary_payment,
    get_employee_salary_status,
    record_distributor_payment,
    get_distributor_payments,
    delete_distributor_payment,
    get_employees_for_payment,
    get_distributors_for_payment,
    get_payment_dashboard_summary
)

from utils.report_exporter import export_to_excel, export_to_pdf

PAYMENT_MODES = ["Cash", "UPI", "Card", "Bank Transfer", "Cheque"]
PAY_PERIODS   = ["This Month", "Advance", "Bonus", "Arrears", "Other"]
DIST_TYPES    = ["Payment Made", "Payment Received"]


class PaymentPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Payment Center")
        self.geometry("1350x820")
        self.resizable(True, True)

        ensure_payment_tables()

        self._employees    = []
        self._distributors = []

        self._build_ui()
        self.after(100, self._refresh_dashboard)

    # ════════════════════════════════════════
    # BUILD UI
    # ════════════════════════════════════════

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="💳  PAYMENT CENTER",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        dash = ctk.CTkFrame(self, height=62)
        dash.pack(fill="x", padx=20, pady=(0, 8))
        dash.pack_propagate(False)

        self.s_collected = self._stat(dash, "💰 Collected Today",      "₹0", "#2E7D32")
        self.s_cust_due  = self._stat(dash, "⏳ Customer Dues",        "₹0", "#C62828")
        self.s_salary    = self._stat(dash, "👨‍💼 Salary Paid (Month)", "₹0", "#1565C0")
        self.s_dist_owed = self._stat(dash, "🚚 Owed to Distributors", "₹0", "#E65100")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for t in ["👥 Customer Payments", "👨‍💼 Salary Payments", "🚚 Distributor Payments"]:
            self.tabs.add(t)

        self._build_customer_tab()
        self._build_salary_tab()
        self._build_distributor_tab()

    def _stat(self, parent, label, val, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=6, pady=6)
        ctk.CTkLabel(f, text=label, font=("Arial", 11), text_color="white").pack(pady=(3,0))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 15, "bold"), text_color="white")
        lbl.pack(pady=(0,3))
        return lbl

    # ════════════════════════════════════════
    # TAB 1 — CUSTOMER PAYMENTS (read-only history)
    # ════════════════════════════════════════

    def _build_customer_tab(self):
        tab = self.tabs.tab("👥 Customer Payments")

        note = ctk.CTkLabel(
            tab, text="ℹ️ Customer due payments are collected from the Sales → Due Payments tab. "
                      "This view shows payment history and outstanding dues.",
            font=("Arial", 11), text_color="gray", wraplength=1100, justify="left"
        )
        note.pack(anchor="w", padx=15, pady=(10, 6))

        # sub-tabs: Payment History | Outstanding Dues
        sub = ctk.CTkTabview(tab)
        sub.pack(fill="both", expand=True, padx=15, pady=4)
        sub.add("📜 Payment History")
        sub.add("⏳ Outstanding Dues")

        # ── Payment History ────────────────────────────────
        hist_tab = sub.tab("📜 Payment History")

        frow = ctk.CTkFrame(hist_tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frow, text="Search Customer:").pack(side="left", padx=(0,4))
        self.cp_search = ctk.CTkEntry(frow, width=160, placeholder_text="Name...")
        self.cp_search.pack(side="left", padx=(0,8))

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.cp_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.cp_from.pack(side="left", padx=(0,8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.cp_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.cp_to.pack(side="left", padx=(0,8))

        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_customer_payments).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_customer_payments(clear=True)).pack(side="left")

        cp_cols = ("ID","Date","Customer","Mobile","Amount","Method","Notes")
        cp_cw = {"ID":40,"Date":140,"Customer":160,"Mobile":110,
                 "Amount":90,"Method":100,"Notes":200}
        self.cp_tree = self._make_tree(hist_tab, cp_cols, cp_cw)

        btn_row = ctk.CTkFrame(hist_tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(btn_row, text="📊 Export Excel", width=140,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_customer_excel).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="📄 Export PDF", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_customer_pdf).pack(side="left", padx=4)

        self._load_customer_payments(clear=True)

        # ── Outstanding Dues ───────────────────────────────
        due_tab = sub.tab("⏳ Outstanding Dues")

        ctk.CTkButton(due_tab, text="🔄 Refresh Dues List",
                      command=self._load_dues, fg_color="#C62828",
                      hover_color="#8E0000").pack(pady=8)

        due_cols = ("ID","Customer Name","Mobile","Outstanding Due")
        due_cw = {"ID":50,"Customer Name":220,"Mobile":140,"Outstanding Due":150}
        self.due_tree = self._make_tree(due_tab, due_cols, due_cw)
        self.due_tree.tag_configure("high", foreground="#EF5350")

        self._load_dues()

    def _load_customer_payments(self, clear=False):
        if clear:
            self.cp_search.delete(0, "end")
            self.cp_from.delete(0, "end")
            self.cp_to.delete(0, "end")

        self._cp_rows = get_customer_payments(
            date_from=self.cp_from.get().strip() or None,
            date_to=self.cp_to.get().strip() or None,
            search=self.cp_search.get().strip() or None
        )
        for i in self.cp_tree.get_children(): self.cp_tree.delete(i)
        for r in self._cp_rows:
            self.cp_tree.insert("", "end", values=(
                r["id"], r["payment_date"],
                r["customer_name"] or "—",
                r["customer_mobile"] or "—",
                f"₹{float(r['amount']):,.2f}",
                r["method"] or "—",
                r["notes"] or ""
            ))

    def _load_dues(self):
        rows = get_customer_dues_summary()
        for i in self.due_tree.get_children(): self.due_tree.delete(i)
        for r in rows:
            bal = float(r["current_balance"])
            tag = "high" if bal > 1000 else ""
            self.due_tree.insert("", "end", tags=(tag,), values=(
                r["id"], r["name"], r["mobile"], f"₹{bal:,.2f}"
            ))

    def _export_customer_excel(self):
        export_to_excel(
            data=self._cp_rows,
            columns=["ID","Date","Customer","Mobile","Amount","Method","Notes"],
            keys=["id","payment_date","customer_name","customer_mobile","amount","method","notes"],
            filename="Customer_Payments_Report", title="Customer Payments Report"
        )

    def _export_customer_pdf(self):
        export_to_pdf(
            data=self._cp_rows,
            columns=["Date","Customer","Mobile","Amount","Method"],
            keys=["payment_date","customer_name","customer_mobile","amount","method"],
            filename="Customer_Payments_Report", title="Customer Payments Report"
        )

    # ════════════════════════════════════════
    # TAB 2 — SALARY PAYMENTS
    # ════════════════════════════════════════

    def _build_salary_tab(self):
        tab = self.tabs.tab("👨‍💼 Salary Payments")
        tab.columnconfigure(0, weight=2)
        tab.columnconfigure(1, weight=3)
        tab.rowconfigure(0, weight=1)

        # LEFT — form
        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=4)

        scroll = ctk.CTkScrollableFrame(left, label_text="💰 Pay Employee Salary",
                                        label_font=("Arial", 14, "bold"))
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._lbl(scroll, "👨‍💼 Employee")
        self.sal_emp_var = ctk.StringVar(value="Select Employee")
        self.sal_emp_menu = ctk.CTkOptionMenu(
            scroll, variable=self.sal_emp_var,
            values=["Select Employee"], width=370,
            command=self._on_employee_select
        )
        self.sal_emp_menu.pack(padx=8, pady=(0,8))
        self._load_employees()

        # salary status box
        self.sal_status_box = ctk.CTkFrame(scroll, fg_color="#1565C0", corner_radius=8)
        self.sal_status_box.pack(fill="x", padx=8, pady=6)
        self.lbl_sal_status = ctk.CTkLabel(
            self.sal_status_box,
            text="Select an employee to see salary status",
            font=("Arial", 11), text_color="white", justify="left"
        )
        self.lbl_sal_status.pack(padx=10, pady=10)

        self._lbl(scroll, "💵 Amount to Pay (₹) *")
        self.sal_amount = ctk.CTkEntry(scroll, width=370, placeholder_text="0.00")
        self.sal_amount.pack(padx=8, pady=(0,8))

        self._lbl(scroll, "📅 Pay Period")
        self.sal_period_var = ctk.StringVar(value="This Month")
        ctk.CTkOptionMenu(scroll, variable=self.sal_period_var,
                          values=PAY_PERIODS, width=370).pack(padx=8, pady=(0,8))

        self._lbl(scroll, "💳 Payment Mode")
        self.sal_mode_var = ctk.StringVar(value="Cash")
        ctk.CTkOptionMenu(scroll, variable=self.sal_mode_var,
                          values=PAYMENT_MODES, width=370).pack(padx=8, pady=(0,8))

        self._lbl(scroll, "📝 Notes")
        self.sal_notes = ctk.CTkEntry(scroll, width=370, placeholder_text="Optional")
        self.sal_notes.pack(padx=8, pady=(0,8))

        ctk.CTkButton(
            scroll, text="✅  Record Salary Payment",
            fg_color="#1565C0", hover_color="#0D47A1",
            width=370, height=42, font=("Arial", 14, "bold"),
            command=self._pay_salary
        ).pack(padx=8, pady=8)

        # RIGHT — history table
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=4)

        ctk.CTkLabel(right, text="📜 Salary Payment History",
                     font=("Arial", 14, "bold")).pack(pady=(10,4))

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.sal_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.sal_from.pack(side="left", padx=(0,8))
        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.sal_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.sal_to.pack(side="left", padx=(0,8))
        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_salary_history).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_salary_history(clear=True)).pack(side="left")

        sal_cols = ("ID","Date","Employee","Amount","Period","Mode","Notes")
        sal_cw = {"ID":40,"Date":140,"Employee":150,"Amount":90,
                  "Period":100,"Mode":90,"Notes":160}
        self.sal_tree = self._make_tree(right, sal_cols, sal_cw)

        arow = ctk.CTkFrame(right, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(arow, text="🗑️ Delete Selected", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._delete_salary).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📊 Export Excel", width=140,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_salary_excel).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📄 Export PDF", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_salary_pdf).pack(side="left", padx=4)

        self._load_salary_history(clear=True)

    def _on_employee_select(self, value):
        if value == "Select Employee":
            self.lbl_sal_status.configure(text="Select an employee to see salary status")
            return
        emp_id = self._get_employee_id(value)
        if emp_id:
            status = get_employee_salary_status(emp_id)
            self.lbl_sal_status.configure(
                text=(f"Monthly Salary: ₹{status['monthly_salary']:,.2f}\n"
                     f"Paid This Month: ₹{status['paid_this_month']:,.2f}\n"
                     f"Balance Due: ₹{status['balance']:,.2f}")
            )
            color = "#1565C0" if status['balance'] <= 0 else "#E65100"
            self.sal_status_box.configure(fg_color=color)

    def _pay_salary(self):
        emp_val = self.sal_emp_var.get()
        if emp_val == "Select Employee":
            messagebox.showwarning("⚠️", "Select an employee.")
            return
        emp_id = self._get_employee_id(emp_val)
        emp_name = emp_val.split(" (")[0]

        success, result = record_salary_payment(
            emp_id, emp_name,
            self.sal_amount.get(),
            self.sal_period_var.get(),
            self.sal_mode_var.get(),
            self.sal_notes.get()
        )
        if success:
            messagebox.showinfo("✅ Success", f"Salary payment recorded! (ID: {result})")
            self.sal_amount.delete(0, "end")
            self.sal_notes.delete(0, "end")
            self._load_salary_history(clear=True)
            self._on_employee_select(emp_val)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌ Error", result)

    def _load_salary_history(self, clear=False):
        if clear:
            self.sal_from.delete(0, "end")
            self.sal_to.delete(0, "end")

        self._sal_rows = get_salary_payments(
            date_from=self.sal_from.get().strip() or None,
            date_to=self.sal_to.get().strip() or None
        )
        for i in self.sal_tree.get_children(): self.sal_tree.delete(i)
        for r in self._sal_rows:
            self.sal_tree.insert("", "end", values=(
                r["id"], r["payment_date"], r["employee_name"],
                f"₹{float(r['amount']):,.2f}", r["pay_period"] or "—",
                r["payment_mode"], r["notes"] or ""
            ))

    def _delete_salary(self):
        sel = self.sal_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to delete.")
            return
        pid = int(self.sal_tree.item(sel, "values")[0])
        if not messagebox.askyesno("⚠️ Confirm", f"Delete salary payment ID {pid}?"):
            return
        success, msg = delete_salary_payment(pid)
        if success:
            messagebox.showinfo("✅", msg)
            self._load_salary_history(clear=True)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌", msg)

    def _export_salary_excel(self):
        export_to_excel(
            data=self._sal_rows,
            columns=["ID","Date","Employee","Amount","Period","Mode","Notes"],
            keys=["id","payment_date","employee_name","amount","pay_period","payment_mode","notes"],
            filename="Salary_Payments_Report", title="Salary Payments Report"
        )

    def _export_salary_pdf(self):
        export_to_pdf(
            data=self._sal_rows,
            columns=["Date","Employee","Amount","Period","Mode"],
            keys=["payment_date","employee_name","amount","pay_period","payment_mode"],
            filename="Salary_Payments_Report", title="Salary Payments Report"
        )

    # ════════════════════════════════════════
    # TAB 3 — DISTRIBUTOR PAYMENTS
    # ════════════════════════════════════════

    def _build_distributor_tab(self):
        tab = self.tabs.tab("🚚 Distributor Payments")
        tab.columnconfigure(0, weight=2)
        tab.columnconfigure(1, weight=3)
        tab.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=4)

        scroll = ctk.CTkScrollableFrame(left, label_text="🚚 Distributor Payment",
                                        label_font=("Arial", 14, "bold"))
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._lbl(scroll, "🚚 Distributor")
        self.dist_var = ctk.StringVar(value="Select Distributor")
        self.dist_menu = ctk.CTkOptionMenu(
            scroll, variable=self.dist_var,
            values=["Select Distributor"], width=370,
            command=self._on_distributor_select
        )
        self.dist_menu.pack(padx=8, pady=(0,8))
        self._load_distributors()

        self.dist_status_box = ctk.CTkFrame(scroll, fg_color="#E65100", corner_radius=8)
        self.dist_status_box.pack(fill="x", padx=8, pady=6)
        self.lbl_dist_status = ctk.CTkLabel(
            self.dist_status_box,
            text="Select a distributor to see balance",
            font=("Arial", 11), text_color="white"
        )
        self.lbl_dist_status.pack(padx=10, pady=10)

        self._lbl(scroll, "📋 Payment Type")
        self.dist_type_var = ctk.StringVar(value="Payment Made")
        ctk.CTkOptionMenu(scroll, variable=self.dist_type_var,
                          values=DIST_TYPES, width=370).pack(padx=8, pady=(0,8))

        self._lbl(scroll, "💵 Amount (₹) *")
        self.dist_amount = ctk.CTkEntry(scroll, width=370, placeholder_text="0.00")
        self.dist_amount.pack(padx=8, pady=(0,8))

        self._lbl(scroll, "💳 Payment Mode")
        self.dist_mode_var = ctk.StringVar(value="Cash")
        ctk.CTkOptionMenu(scroll, variable=self.dist_mode_var,
                          values=PAYMENT_MODES, width=370).pack(padx=8, pady=(0,8))

        self._lbl(scroll, "📝 Notes")
        self.dist_notes = ctk.CTkEntry(scroll, width=370, placeholder_text="Optional")
        self.dist_notes.pack(padx=8, pady=(0,8))

        ctk.CTkButton(
            scroll, text="✅  Record Payment",
            fg_color="#E65100", hover_color="#BF360C",
            width=370, height=42, font=("Arial", 14, "bold"),
            command=self._pay_distributor
        ).pack(padx=8, pady=8)

        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=4)

        ctk.CTkLabel(right, text="📜 Distributor Payment History",
                     font=("Arial", 14, "bold")).pack(pady=(10,4))

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.dp_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.dp_from.pack(side="left", padx=(0,8))
        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.dp_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.dp_to.pack(side="left", padx=(0,8))
        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_distributor_history).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_distributor_history(clear=True)).pack(side="left")

        dp_cols = ("ID","Date","Distributor","Amount","Type","Mode","Notes")
        dp_cw = {"ID":40,"Date":140,"Distributor":150,"Amount":90,
                 "Type":120,"Mode":90,"Notes":160}
        self.dp_tree = self._make_tree(right, dp_cols, dp_cw)

        arow = ctk.CTkFrame(right, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(arow, text="🗑️ Delete Selected", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._delete_distributor_payment).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📊 Export Excel", width=140,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_dist_excel).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📄 Export PDF", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_dist_pdf).pack(side="left", padx=4)

        self._load_distributor_history(clear=True)

    def _on_distributor_select(self, value):
        if value == "Select Distributor":
            self.lbl_dist_status.configure(text="Select a distributor to see balance")
            return
        for d in self._distributors:
            if value.startswith(d["name"]):
                bal = float(d["balance"])
                txt = f"Current Balance Owed: ₹{bal:,.2f}" if bal >= 0 else \
                      f"They owe us: ₹{abs(bal):,.2f}"
                self.lbl_dist_status.configure(text=txt)
                color = "#E65100" if bal > 0 else "#2E7D32"
                self.dist_status_box.configure(fg_color=color)
                break

    def _pay_distributor(self):
        val = self.dist_var.get()
        if val == "Select Distributor":
            messagebox.showwarning("⚠️", "Select a distributor.")
            return
        dist_id = None
        dist_name = val.split(" (")[0]
        for d in self._distributors:
            if val.startswith(d["name"]):
                dist_id = d["id"]; break

        success, result = record_distributor_payment(
            dist_id, dist_name,
            self.dist_amount.get(),
            self.dist_type_var.get(),
            self.dist_mode_var.get(),
            self.dist_notes.get()
        )
        if success:
            messagebox.showinfo("✅ Success", f"Payment recorded! (ID: {result})")
            self.dist_amount.delete(0, "end")
            self.dist_notes.delete(0, "end")
            self._load_distributors()
            self._load_distributor_history(clear=True)
            self._on_distributor_select(val)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌ Error", result)

    def _load_distributor_history(self, clear=False):
        if clear:
            self.dp_from.delete(0, "end")
            self.dp_to.delete(0, "end")

        self._dp_rows = get_distributor_payments(
            date_from=self.dp_from.get().strip() or None,
            date_to=self.dp_to.get().strip() or None
        )
        for i in self.dp_tree.get_children(): self.dp_tree.delete(i)
        for r in self._dp_rows:
            self.dp_tree.insert("", "end", values=(
                r["id"], r["payment_date"], r["distributor_name"],
                f"₹{float(r['amount']):,.2f}", r["payment_type"],
                r["payment_mode"], r["notes"] or ""
            ))

    def _delete_distributor_payment(self):
        sel = self.dp_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to delete.")
            return
        pid = int(self.dp_tree.item(sel, "values")[0])
        if not messagebox.askyesno("⚠️ Confirm", f"Delete payment ID {pid}?"):
            return
        success, msg = delete_distributor_payment(pid)
        if success:
            messagebox.showinfo("✅", msg)
            self._load_distributors()
            self._load_distributor_history(clear=True)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌", msg)

    def _export_dist_excel(self):
        export_to_excel(
            data=self._dp_rows,
            columns=["ID","Date","Distributor","Amount","Type","Mode","Notes"],
            keys=["id","payment_date","distributor_name","amount","payment_type","payment_mode","notes"],
            filename="Distributor_Payments_Report", title="Distributor Payments Report"
        )

    def _export_dist_pdf(self):
        export_to_pdf(
            data=self._dp_rows,
            columns=["Date","Distributor","Amount","Type","Mode"],
            keys=["payment_date","distributor_name","amount","payment_type","payment_mode"],
            filename="Distributor_Payments_Report", title="Distributor Payments Report"
        )

    # ════════════════════════════════════════
    # DASHBOARD
    # ════════════════════════════════════════

    def _refresh_dashboard(self):
        s = get_payment_dashboard_summary()
        self.s_collected.configure(text=f"₹{s['collected_today']:,.2f}")
        self.s_cust_due.configure(text=f"₹{s['total_customer_due']:,.2f}")
        self.s_salary.configure(text=f"₹{s['salary_paid_month']:,.2f}")
        self.s_dist_owed.configure(text=f"₹{s['distributor_owed']:,.2f}")

    # ════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, anchor="w",
                     font=("Arial", 11)).pack(fill="x", padx=8, pady=(4,0))

    def _load_employees(self):
        self._employees = get_employees_for_payment()
        names = ["Select Employee"] + [f"{e['name']} ({e['role']})" for e in self._employees]
        self.sal_emp_menu.configure(values=names)
        self.sal_emp_var.set("Select Employee")

    def _get_employee_id(self, display_val):
        for e in self._employees:
            if display_val.startswith(e["name"]):
                return e["id"]
        return None

    def _load_distributors(self):
        self._distributors = get_distributors_for_payment()
        names = ["Select Distributor"] + [
            f"{d['name']} (Bal: ₹{float(d['balance']):,.0f})" for d in self._distributors
        ]
        self.dist_menu.configure(values=names)
        self.dist_var.set("Select Distributor")

    def _make_tree(self, parent, cols, col_widths, height=14):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Pay.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=26, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Pay.Treeview.Heading",
            background="#1565C0", foreground="white", font=("Arial", 11,"bold"))
        style.map("Pay.Treeview", background=[("selected","#1976D2")])

        c = tk.Frame(parent, bg="#2b2b2b")
        c.pack(fill="both", expand=True, padx=10, pady=4)

        tree = ttk.Treeview(c, columns=cols, show="headings",
                            style="Pay.Treeview", selectmode="browse", height=height)
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