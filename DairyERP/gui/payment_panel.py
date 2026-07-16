import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk

from models.payment import (
    ensure_payment_tables,
    get_customer_payments,
    get_customer_dues_summary,
    record_salary_payment,
    get_salary_payments,
    delete_salary_payment,
    get_employee_salary_status,
    get_employee_salary_ledger,
    get_employees_for_payment,
    get_payment_dashboard_summary
)

from models.production_incentive import (
    ensure_incentive_tables,
    get_production_rates,
    set_production_rates,
    get_employee_incentive_status,
    record_incentive_payment,
    get_incentive_payment_history,
    delete_incentive_payment,
)

from DairyERP.utils.report_exporter import export_to_excel, export_to_pdf

PAYMENT_MODES = ["Cash", "UPI", "Card", "Bank Transfer", "Cheque"]
PAY_PERIODS   = ["This Month", "Advance", "Bonus", "Arrears", "Other"]


class PaymentPanel(ctk.CTkToplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Payment Center")
        self.geometry("1350x820")
        self.resizable(True, True)

        ensure_payment_tables()
        ensure_incentive_tables()

        self._employees = []

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

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for t in ["👥 Customer Payments", "👨‍💼 Salary Payments", "🏭 Production Incentive"]:
            self.tabs.add(t)

        self._build_customer_tab()
        self._build_salary_tab()
        self._build_incentive_tab()

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

        ctk.CTkButton(
            scroll, text="📊 View Monthly Salary Ledger", width=370,
            fg_color="#455A64", hover_color="#263238",
            command=self._show_salary_ledger
        ).pack(padx=8, pady=(0,8))

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
            self.lbl_sal_status.configure(
                text="Select an employee to see salary status")
            return
        emp_id = self._get_employee_id(value)
        if emp_id:
            status = get_employee_salary_status(emp_id)

            def line(label, amt):
                return f"{label:<20}₹{amt:,.2f}"

            sep = "─" * 32
            rows = [line("Monthly Salary", status['monthly_salary']), sep,
                    line("This Month Paid", status['paid_this_month'])]
            if status['advance_paid']:
                rows.append(line("Advance Paid", status['advance_paid']))
            rows.append(line("Remaining This Month", status['remaining_this_month']))
            if status['old_due_remaining']:
                rows.append(sep)
                rows.append(line("Old Due (Pending)", status['old_due_remaining']))
            if status['arrears_paid_total']:
                rows.append(line("Arrears Paid (All Time)", status['arrears_paid_total']))
            if status['bonus_paid']:
                rows.append(sep)
                rows.append(line("Bonus Paid (No effect on due)", status['bonus_paid']))
            rows.append(sep)
            rows.append(line("Total Balance Due", status['balance']))

            self.lbl_sal_status.configure(text="\n".join(rows), justify="left")
            color = "#2E7D32" if status['balance'] <= 0 else "#E65100"
            self.sal_status_box.configure(fg_color=color)

    def _show_salary_ledger(self):
        emp_val = self.sal_emp_var.get()
        if emp_val == "Select Employee":
            messagebox.showwarning("⚠️", "Select an employee first.")
            return
        emp_id = self._get_employee_id(emp_val)
        emp_name = emp_val.split(" (")[0]
        ledger = get_employee_salary_ledger(emp_id)

        win = ctk.CTkToplevel(self)
        win.title(f"Monthly Salary Ledger — {emp_name}")
        win.geometry("720x420")

        ctk.CTkLabel(win, text=f"📊 Monthly Salary Ledger — {emp_name}",
                     font=("Arial", 15, "bold")).pack(pady=(12, 6))

        cols = ("Month", "Salary", "This Month Paid", "Advance", "Arrears", "Bonus", "Balance")
        cw = {"Month": 90, "Salary": 90, "This Month Paid": 120,
              "Advance": 90, "Arrears": 90, "Bonus": 80, "Balance": 90}
        tree = self._make_tree(win, cols, cw, height=12)

        if not ledger:
            ctk.CTkLabel(win, text="No salary payment history found for this employee.",
                         text_color="gray").pack(pady=6)
            return

        for m in ledger:
            tree.insert("", "end", values=(
                m["month"], f"₹{m['monthly_salary']:,.0f}",
                f"₹{m['this_month_paid']:,.0f}", f"₹{m['advance_paid']:,.0f}",
                f"₹{m['arrears_paid']:,.0f}", f"₹{m['bonus_paid']:,.0f}",
                f"₹{m['balance']:,.0f}"
            ))

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
    # TAB 3 — PRODUCTION INCENTIVE (Cream/Ghee output-based pay)
    # ════════════════════════════════════════

    def _build_incentive_tab(self):
        tab = self.tabs.tab("🏭 Production Incentive")
        tab.columnconfigure(0, weight=2)
        tab.columnconfigure(1, weight=3)
        tab.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=4)

        scroll = ctk.CTkScrollableFrame(left, label_text="🏭 Pay Production Incentive",
                                        label_font=("Arial", 14, "bold"))
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        rates = get_production_rates()
        self.rate_lbl = ctk.CTkLabel(
            scroll,
            text=(f"Current Rates —  Cream: ₹{rates['cream_rate_per_kg']:,.2f}/kg   "
                  f"Ghee: ₹{rates['ghee_rate_per_kg']:,.2f}/kg"),
            font=("Arial", 11), text_color="gray"
        )
        self.rate_lbl.pack(padx=8, pady=(4,0))

        ctk.CTkButton(scroll, text="⚙️ Set Cream/Ghee Rates", width=370,
                      fg_color="#455A64", hover_color="#263238",
                      command=self._open_rate_settings).pack(padx=8, pady=(4,8))

        self._lbl(scroll, "👨‍💼 Employee (Operator)")
        self.inc_emp_var = ctk.StringVar(value="Select Employee")
        self.inc_emp_menu = ctk.CTkOptionMenu(
            scroll, variable=self.inc_emp_var,
            values=["Select Employee"], width=370,
            command=self._on_incentive_employee_select
        )
        self.inc_emp_menu.pack(padx=8, pady=(0,8))
        # employees already loaded by _build_salary_tab -> self._employees
        emp_names = ["Select Employee"] + [f"{e['name']} ({e['role']})" for e in self._employees]
        self.inc_emp_menu.configure(values=emp_names)

        self.inc_status_box = ctk.CTkFrame(scroll, fg_color="#00695C", corner_radius=8)
        self.inc_status_box.pack(fill="x", padx=8, pady=6)
        self.lbl_inc_status = ctk.CTkLabel(
            self.inc_status_box,
            text="Select an employee to see production & unpaid amount",
            font=("Arial", 11), text_color="white", justify="left"
        )
        self.lbl_inc_status.pack(padx=10, pady=10)

        self._lbl(scroll, "💳 Payment Mode")
        self.inc_mode_var = ctk.StringVar(value="Cash")
        ctk.CTkOptionMenu(scroll, variable=self.inc_mode_var,
                          values=PAYMENT_MODES, width=370).pack(padx=8, pady=(0,8))

        self._lbl(scroll, "📝 Notes")
        self.inc_notes = ctk.CTkEntry(scroll, width=370, placeholder_text="Optional")
        self.inc_notes.pack(padx=8, pady=(0,8))

        ctk.CTkButton(
            scroll, text="✅  Pay Unpaid Production Amount",
            fg_color="#00695C", hover_color="#004D40",
            width=370, height=42, font=("Arial", 14, "bold"),
            command=self._pay_incentive
        ).pack(padx=8, pady=8)

        # RIGHT — history table
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=4)

        ctk.CTkLabel(right, text="📜 Production Incentive Payment History",
                     font=("Arial", 14, "bold")).pack(pady=(10,4))

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0,4))
        self.inc_from = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.inc_from.pack(side="left", padx=(0,8))
        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0,4))
        self.inc_to = ctk.CTkEntry(frow, width=110, placeholder_text="YYYY-MM-DD")
        self.inc_to.pack(side="left", padx=(0,8))
        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_incentive_history).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_incentive_history(clear=True)).pack(side="left")

        inc_cols = ("ID","Date","Employee","Cream Kg","Ghee Kg","Cream Rate","Ghee Rate","Amount","Mode","Notes")
        inc_cw = {"ID":40,"Date":135,"Employee":120,"Cream Kg":80,"Ghee Kg":80,
                  "Cream Rate":85,"Ghee Rate":85,"Amount":90,"Mode":85,"Notes":140}
        self.inc_tree = self._make_tree(right, inc_cols, inc_cw)

        arow = ctk.CTkFrame(right, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=6)
        ctk.CTkButton(arow, text="🗑️ Delete Selected", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._delete_incentive_payment).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📊 Export Excel", width=140,
                      fg_color="#1D6F42", hover_color="#14502F",
                      command=self._export_incentive_excel).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="📄 Export PDF", width=140,
                      fg_color="#C62828", hover_color="#8E0000",
                      command=self._export_incentive_pdf).pack(side="left", padx=4)

        self._load_incentive_history(clear=True)

    def _open_rate_settings(self):
        rates = get_production_rates()
        win = ctk.CTkToplevel(self)
        win.title("Set Cream/Ghee Rates")
        win.geometry("360x260")
        win.grab_set()

        ctk.CTkLabel(win, text="⚙️ Production Incentive Rates",
                     font=("Arial", 14, "bold")).pack(pady=(14,8))

        ctk.CTkLabel(win, text="Cream Rate (₹ per Kg)").pack(anchor="w", padx=20)
        cream_entry = ctk.CTkEntry(win, width=300)
        cream_entry.insert(0, str(rates["cream_rate_per_kg"]))
        cream_entry.pack(padx=20, pady=(0,10))

        ctk.CTkLabel(win, text="Ghee Rate (₹ per Kg)").pack(anchor="w", padx=20)
        ghee_entry = ctk.CTkEntry(win, width=300)
        ghee_entry.insert(0, str(rates["ghee_rate_per_kg"]))
        ghee_entry.pack(padx=20, pady=(0,10))

        def save():
            success, msg = set_production_rates(cream_entry.get(), ghee_entry.get())
            if success:
                messagebox.showinfo("✅", msg)
                new_rates = get_production_rates()
                self.rate_lbl.configure(
                    text=(f"Current Rates —  Cream: ₹{new_rates['cream_rate_per_kg']:,.2f}/kg   "
                          f"Ghee: ₹{new_rates['ghee_rate_per_kg']:,.2f}/kg"))
                # refresh currently selected employee's status with new rates
                self._on_incentive_employee_select(self.inc_emp_var.get())
                win.destroy()
            else:
                messagebox.showerror("❌", msg)

        ctk.CTkButton(win, text="💾 Save Rates", fg_color="#00695C",
                      hover_color="#004D40", command=save).pack(pady=12)

    def _on_incentive_employee_select(self, value):
        if value == "Select Employee":
            self.lbl_inc_status.configure(
                text="Select an employee to see production & unpaid amount")
            return
        emp_id = self._get_employee_id(value)
        if emp_id:
            status = get_employee_incentive_status(emp_id)

            def line(label, val, is_amt=True):
                v = f"₹{val:,.2f}" if is_amt else f"{val:,.2f} kg"
                return f"{label:<22}{v}"

            sep = "─" * 34
            rows = [
                line("Cream Produced (Total)", status['cream_produced'], False),
                line("Ghee Produced (Total)",  status['ghee_produced'], False),
                sep,
                line("Cream Already Paid",     status['cream_paid'], False),
                line("Ghee Already Paid",      status['ghee_paid'], False),
                sep,
                line("Unpaid Cream",           status['unpaid_cream'], False),
                line("Unpaid Ghee",            status['unpaid_ghee'], False),
                sep,
                line("Amount Payable",         status['amount_payable']),
            ]
            self.lbl_inc_status.configure(text="\n".join(rows), justify="left")
            color = "#455A64" if status['amount_payable'] <= 0 else "#00695C"
            self.inc_status_box.configure(fg_color=color)

    def _pay_incentive(self):
        emp_val = self.inc_emp_var.get()
        if emp_val == "Select Employee":
            messagebox.showwarning("⚠️", "Select an employee.")
            return
        emp_id = self._get_employee_id(emp_val)
        emp_name = emp_val.split(" (")[0]

        success, result = record_incentive_payment(
            emp_id, emp_name,
            self.inc_mode_var.get(),
            self.inc_notes.get()
        )
        if success:
            messagebox.showinfo("✅ Success", f"Incentive payment recorded! (ID: {result})")
            self.inc_notes.delete(0, "end")
            self._load_incentive_history(clear=True)
            self._on_incentive_employee_select(emp_val)
        else:
            messagebox.showwarning("⚠️", result)

    def _load_incentive_history(self, clear=False):
        if clear:
            self.inc_from.delete(0, "end")
            self.inc_to.delete(0, "end")

        self._inc_rows = get_incentive_payment_history(
            date_from=self.inc_from.get().strip() or None,
            date_to=self.inc_to.get().strip() or None
        )
        for i in self.inc_tree.get_children(): self.inc_tree.delete(i)
        for r in self._inc_rows:
            self.inc_tree.insert("", "end", values=(
                r["id"], r["payment_date"], r["employee_name"],
                f"{float(r['cream_qty']):,.2f}", f"{float(r['ghee_qty']):,.2f}",
                f"₹{float(r['cream_rate']):,.2f}", f"₹{float(r['ghee_rate']):,.2f}",
                f"₹{float(r['amount']):,.2f}", r["payment_mode"], r["notes"] or ""
            ))

    def _delete_incentive_payment(self):
        sel = self.inc_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to delete.")
            return
        pid = int(self.inc_tree.item(sel, "values")[0])
        if not messagebox.askyesno("⚠️ Confirm",
                f"Delete incentive payment ID {pid}?\nThat quantity will become unpaid again."):
            return
        success, msg = delete_incentive_payment(pid)
        if success:
            messagebox.showinfo("✅", msg)
            self._load_incentive_history(clear=True)
            self._on_incentive_employee_select(self.inc_emp_var.get())
        else:
            messagebox.showerror("❌", msg)

    def _export_incentive_excel(self):
        export_to_excel(
            data=self._inc_rows,
            columns=["ID","Date","Employee","Cream Kg","Ghee Kg","Cream Rate","Ghee Rate","Amount","Mode","Notes"],
            keys=["id","payment_date","employee_name","cream_qty","ghee_qty",
                  "cream_rate","ghee_rate","amount","payment_mode","notes"],
            filename="Production_Incentive_Report", title="Production Incentive Payments Report"
        )

    def _export_incentive_pdf(self):
        export_to_pdf(
            data=self._inc_rows,
            columns=["Date","Employee","Cream Kg","Ghee Kg","Amount"],
            keys=["payment_date","employee_name","cream_qty","ghee_qty","amount"],
            filename="Production_Incentive_Report", title="Production Incentive Payments Report"
        )

    # ════════════════════════════════════════
    # DASHBOARD
    # ════════════════════════════════════════

    def _refresh_dashboard(self):
        s = get_payment_dashboard_summary()
        self.s_collected.configure(text=f"₹{s['collected_today']:,.2f}")
        self.s_cust_due.configure(text=f"₹{s['total_customer_due']:,.2f}")
        self.s_salary.configure(text=f"₹{s['salary_paid_month']:,.2f}")

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
        if hasattr(self, "inc_emp_menu"):
            self.inc_emp_menu.configure(values=names)

    def _get_employee_id(self, display_val):
        for e in self._employees:
            if display_val.startswith(e["name"]):
                return e["id"]
        return None

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