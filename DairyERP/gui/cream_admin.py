import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime

from models.cream import (
    ensure_cream_tables,
    add_cream_entry,
    get_cream_entries,
    get_cream_entry_by_id,
    update_cream_entry,
    delete_cream_entry,
    get_current_cream_stock,
    get_cream_summary,
    get_daily_cream_data,
    get_employees_list
)

SHIFTS = ["Morning", "Evening", "Night", "Full Day"]


class CreamAdmin(ctk.CTkToplevel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Cream Production Management")
        self.geometry("1350x820")
        self.resizable(True, True)

        ensure_cream_tables()

        self._selected_id    = None
        self._employees      = []
        self.lbl_cur_stock   = None   # will be set during _build_ui

        self._build_ui()
        self.after(100, self._refresh_dashboard)  # after UI fully rendered

    # ════════════════════════════════════════
    # BUILD UI
    # ════════════════════════════════════════

    def _build_ui(self):

        # Title
        ctk.CTkLabel(
            self, text="🥛  CREAM PRODUCTION MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        # ── Dashboard Stats ────────────────────────────────
        dash = ctk.CTkFrame(self, height=62)
        dash.pack(fill="x", padx=20, pady=(0, 8))
        dash.pack_propagate(False)

        self.s_stock    = self._stat(dash, "🥛 Current Stock (Kg)", "0",   "#1565C0")
        self.s_produced = self._stat(dash, "📦 Total Produced (Kg)","0",   "#2E7D32")
        self.s_ghee     = self._stat(dash, "🫙 Sent to Ghee (Kg)",  "0",   "#E65100")
        self.s_sold     = self._stat(dash, "💰 Sold (Kg)",           "0",   "#6A1B9A")
        self.s_wasted   = self._stat(dash, "🗑️ Wasted (Kg)",         "0",   "#B71C1C")
        self.s_yield    = self._stat(dash, "📊 Avg Yield %",         "0%",  "#00695C")

        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for t in ["➕ Add Entry", "📋 Production Records",
                  "📊 Reports", "📈 Daily Summary"]:
            self.tabs.add(t)

        self._build_add_tab()
        self._build_records_tab()
        self._build_reports_tab()
        self._build_summary_tab()

    # ════════════════════════════════════════
    # STAT CARD
    # ════════════════════════════════════════

    def _stat(self, parent, label, val, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=5, pady=6)
        ctk.CTkLabel(f, text=label, font=("Arial", 10),
                     text_color="white").pack(pady=(3, 0))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 14, "bold"),
                           text_color="white")
        lbl.pack(pady=(0, 3))
        return lbl

    # ════════════════════════════════════════
    # TAB 1 — ADD ENTRY
    # ════════════════════════════════════════

    def _build_add_tab(self):
        tab = self.tabs.tab("➕ Add Entry")

        # Two columns: form | live calculation
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        # ── LEFT: Form ─────────────────────────────────────
        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=4)

        # Use CTkScrollableFrame so all fields fit without cutting off
        scroll = ctk.CTkScrollableFrame(left, label_text="➕ New Cream Production Entry",
                                         label_font=("Arial", 14, "bold"))
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Entry ID (readonly)
        self._two_col(scroll, "Entry ID (auto)")
        self.e_id = ctk.CTkEntry(scroll, width=370,
                                  placeholder_text="Auto-generated",
                                  state="readonly")
        self.e_id.pack(padx=8, pady=(0, 6))

        # Date  ← always visible at top
        self._two_col(scroll, "📅 Entry Date (YYYY-MM-DD) *")
        self.e_date = ctk.CTkEntry(scroll, width=370)
        self.e_date.pack(padx=8, pady=(0, 6))
        self.e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Shift
        self._two_col(scroll, "⏰ Shift")
        self.shift_var = ctk.StringVar(value="Morning")
        ctk.CTkOptionMenu(scroll, variable=self.shift_var,
                          values=SHIFTS, width=370).pack(padx=8, pady=(0, 6))

        # Milk received
        self._two_col(scroll, "🥛 Milk Received (Litres)")
        self.e_milk = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_milk.pack(padx=8, pady=(0, 6))
        self.e_milk.bind("<KeyRelease>", self._live_calc)

        # Fat %
        self._two_col(scroll, "🔬 Fat % (optional)")
        self.e_fat = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_fat.pack(padx=8, pady=(0, 6))
        self.e_fat.bind("<KeyRelease>", self._live_calc)

        # Cream produced
        self._two_col(scroll, "📦 Cream Produced (Kg) *")
        self.e_cream = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_cream.pack(padx=8, pady=(0, 6))
        self.e_cream.bind("<KeyRelease>", self._live_calc)

        # Cream used for ghee
        self._two_col(scroll, "🫙 Cream Sent to Ghee (Kg)")
        self.e_ghee = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_ghee.pack(padx=8, pady=(0, 6))
        self.e_ghee.bind("<KeyRelease>", self._live_calc)

        # Cream sold
        self._two_col(scroll, "💰 Cream Sold (Kg)")
        self.e_sold = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_sold.pack(padx=8, pady=(0, 6))
        self.e_sold.bind("<KeyRelease>", self._live_calc)

        # Cream wasted
        self._two_col(scroll, "🗑️ Cream Wasted / Loss (Kg)")
        self.e_wasted = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_wasted.pack(padx=8, pady=(0, 6))
        self.e_wasted.bind("<KeyRelease>", self._live_calc)

        # Supplier
        self._two_col(scroll, "🚜 Supplier / Farmer Name")
        self.e_supplier = ctk.CTkEntry(scroll, width=370, placeholder_text="Name")
        self.e_supplier.pack(padx=8, pady=(0, 6))

        # Employee
        self._two_col(scroll, "👨‍💼 Employee")
        self.emp_var = ctk.StringVar(value="Select Employee")
        self.emp_menu = ctk.CTkOptionMenu(
            scroll, variable=self.emp_var,
            values=["Select Employee"], width=370
        )
        self.emp_menu.pack(padx=8, pady=(0, 6))
        self._load_employees()

        # Notes
        self._two_col(scroll, "📝 Notes")
        self.e_notes = ctk.CTkEntry(scroll, width=370, placeholder_text="Optional")
        self.e_notes.pack(padx=8, pady=(0, 8))

        # Buttons
        ctk.CTkButton(
            scroll, text="➕  Add Entry",
            fg_color="#2196F3", hover_color="#1565C0",
            width=370, height=42, font=("Arial", 14, "bold"),
            command=self._add_entry
        ).pack(padx=8, pady=5)

        ctk.CTkButton(
            scroll, text="✏️  Update Entry",
            fg_color="#FF9800", hover_color="#E65100",
            width=370, height=36,
            command=self._update_entry
        ).pack(padx=8, pady=4)

        ctk.CTkButton(
            scroll, text="✖  Clear Fields",
            fg_color="#607D8B", hover_color="#37474F",
            width=370, height=34,
            command=self._clear_fields
        ).pack(padx=8, pady=4)

        # ── RIGHT: Live Calculation Panel ──────────────────
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=4)

        ctk.CTkLabel(right, text="🔢 Live Calculation",
                     font=("Arial", 14, "bold")).pack(pady=(16, 8))

        self.calc_frame = ctk.CTkFrame(right, fg_color="#1e1e1e", corner_radius=10)
        self.calc_frame.pack(fill="x", padx=15, pady=4)

        self.lbl_milk_in   = self._calc_row(self.calc_frame, "Milk In",         "0 Litres")
        self.lbl_cream_out = self._calc_row(self.calc_frame, "Cream Produced",  "0 Kg")
        self.lbl_yield     = self._calc_row(self.calc_frame, "Yield %",         "0%")

        ctk.CTkLabel(self.calc_frame, text="─"*30,
                     text_color="gray").pack(pady=4)

        self.lbl_ghee_out  = self._calc_row(self.calc_frame, "→ Ghee",          "0 Kg")
        self.lbl_sold_out  = self._calc_row(self.calc_frame, "→ Sold",           "0 Kg")
        self.lbl_waste_out = self._calc_row(self.calc_frame, "→ Wasted",         "0 Kg")

        ctk.CTkLabel(self.calc_frame, text="─"*30,
                     text_color="gray").pack(pady=4)

        self.lbl_balance   = self._calc_row(self.calc_frame, "Balance in Hand",  "0 Kg",
                                             bold=True, color="#64B5F6")

        # Current stock box
        ctk.CTkLabel(right, text="📦 Current Cream Stock",
                     font=("Arial", 13, "bold")).pack(pady=(20, 6))

        self.stock_box = ctk.CTkFrame(right, fg_color="#1B5E20", corner_radius=10)
        self.stock_box.pack(fill="x", padx=15, pady=4)

        self.lbl_cur_stock = ctk.CTkLabel(
            self.stock_box, text="0.000 Kg",
            font=("Arial", 28, "bold"), text_color="white"
        )
        self.lbl_cur_stock.pack(pady=16)

        ctk.CTkButton(
            right, text="🔄 Refresh Stock",
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._refresh_dashboard
        ).pack(padx=15, pady=8, fill="x")

    def _calc_row(self, parent, label, val, bold=False, color="white"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label, font=("Arial", 12),
                     text_color="#aaaaaa", width=140, anchor="w").pack(side="left")
        font = ("Arial", 13, "bold") if bold else ("Arial", 12)
        lbl  = ctk.CTkLabel(row, text=val, font=font,
                             text_color=color, anchor="e")
        lbl.pack(side="right")
        return lbl

    def _live_calc(self, event=None):
        def fval(entry):
            try: return float(entry.get()) if entry.get().strip() else 0.0
            except: return 0.0

        milk   = fval(self.e_milk)
        cream  = fval(self.e_cream)
        ghee   = fval(self.e_ghee)
        sold   = fval(self.e_sold)
        wasted = fval(self.e_wasted)

        yield_pct = round(cream / milk * 100, 2) if milk > 0 else 0.0
        balance   = round(cream - ghee - sold - wasted, 3)

        self.lbl_milk_in.configure(text=f"{milk:g} Litres")
        self.lbl_cream_out.configure(text=f"{cream:g} Kg")
        self.lbl_yield.configure(text=f"{yield_pct}%")
        self.lbl_ghee_out.configure(text=f"{ghee:g} Kg")
        self.lbl_sold_out.configure(text=f"{sold:g} Kg")
        self.lbl_waste_out.configure(text=f"{wasted:g} Kg")

        color = "#EF9A9A" if balance < 0 else "#64B5F6"
        self.lbl_balance.configure(text=f"{balance:g} Kg", text_color=color)

    # ════════════════════════════════════════
    # TAB 2 — PRODUCTION RECORDS
    # ════════════════════════════════════════

    def _build_records_tab(self):
        tab = self.tabs.tab("📋 Production Records")

        # Filter row
        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0, 4))
        self.rec_from = ctk.CTkEntry(frow, width=120,
                                     placeholder_text="YYYY-MM-DD")
        self.rec_from.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0, 4))
        self.rec_to = ctk.CTkEntry(frow, width=120,
                                   placeholder_text="YYYY-MM-DD")
        self.rec_to.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="Shift:").pack(side="left", padx=(0, 4))
        self.rec_shift_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(frow, variable=self.rec_shift_var,
                          values=["All"] + SHIFTS,
                          width=120).pack(side="left", padx=(0, 8))

        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_records).pack(side="left", padx=(0, 6))
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_records(clear=True)
                      ).pack(side="left")

        # Table
        cols = ("ID", "Date", "Shift", "Milk (L)", "Fat %",
                "Cream (Kg)", "→ Ghee", "→ Sold",
                "→ Wasted", "Balance", "Supplier", "Employee", "Notes")
        cw   = {
            "ID": 40, "Date": 100, "Shift": 80, "Milk (L)": 75,
            "Fat %": 60, "Cream (Kg)": 90, "→ Ghee": 75,
            "→ Sold": 75, "→ Wasted": 75, "Balance": 80,
            "Supplier": 120, "Employee": 120, "Notes": 160
        }

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cream.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=27, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Cream.Treeview.Heading",
            background="#1565C0", foreground="white",
            font=("Arial", 11, "bold"))
        style.map("Cream.Treeview",
                  background=[("selected", "#1976D2")])

        tc = tk.Frame(tab, bg="#2b2b2b")
        tc.pack(fill="both", expand=True, padx=10, pady=4)

        self.rec_tree = ttk.Treeview(tc, columns=cols, show="headings",
                                     style="Cream.Treeview",
                                     selectmode="browse")
        for col in cols:
            self.rec_tree.heading(col, text=col)
            self.rec_tree.column(col, width=cw.get(col, 90), anchor="center")

        vsb = ttk.Scrollbar(tc, orient="vertical",   command=self.rec_tree.yview)
        hsb = ttk.Scrollbar(tc, orient="horizontal", command=self.rec_tree.xview)
        self.rec_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.rec_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tc.rowconfigure(0, weight=1)
        tc.columnconfigure(0, weight=1)

        self.rec_tree.bind("<<TreeviewSelect>>", self._on_row_select)

        # Action buttons
        arow = ctk.CTkFrame(tab, fg_color="transparent")
        arow.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(arow, text="✏️ Edit Selected", width=140,
                      fg_color="#FF9800", hover_color="#E65100",
                      command=self._edit_selected).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="🗑️ Delete Selected", width=150,
                      fg_color="#C62828", hover_color="#B71C1C",
                      command=self._delete_selected).pack(side="left", padx=4)
        ctk.CTkButton(arow, text="🔄 Refresh", width=100,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_records(clear=True)
                      ).pack(side="left", padx=4)

        self._load_records(clear=True)

    def _load_records(self, clear=False):
        if clear:
            self.rec_from.delete(0, "end")
            self.rec_to.delete(0, "end")
            self.rec_shift_var.set("All")

        rows = get_cream_entries(
            date_from=self.rec_from.get().strip() or None,
            date_to=self.rec_to.get().strip() or None,
            shift=self.rec_shift_var.get()
        )
        for i in self.rec_tree.get_children():
            self.rec_tree.delete(i)

        for r in rows:
            cream   = float(r["cream_kg"])
            ghee    = float(r["cream_used_ghee"])
            sold    = float(r["cream_sold"])
            wasted  = float(r["cream_wasted"])
            balance = round(cream - ghee - sold - wasted, 3)
            self.rec_tree.insert("", "end", values=(
                r["id"],
                r["entry_date"],
                r["shift"],
                f"{float(r['milk_litres']):g}",
                f"{float(r['fat_percent']):g}",
                f"{cream:g}",
                f"{ghee:g}",
                f"{sold:g}",
                f"{wasted:g}",
                f"{balance:g}",
                r["supplier_name"] or "—",
                r["employee_name"] or "—",
                r["notes"] or ""
            ))

    def _on_row_select(self, event):
        sel = self.rec_tree.focus()
        if not sel: return
        vals = self.rec_tree.item(sel, "values")
        eid  = int(vals[0])
        row  = get_cream_entry_by_id(eid)
        if row:
            self._fill_form(row)
            self.tabs.set("➕ Add Entry")

    def _fill_form(self, row):
        self._clear_fields()
        self._selected_id = row["id"]

        self.e_id.configure(state="normal")
        self.e_id.insert(0, row["id"])
        self.e_id.configure(state="readonly")

        self.e_date.insert(0,     row["entry_date"])
        self.shift_var.set(       row["shift"])
        self.e_milk.insert(0,     str(row["milk_litres"]))
        self.e_fat.insert(0,      str(row["fat_percent"]))
        self.e_cream.insert(0,    str(row["cream_kg"]))
        self.e_ghee.insert(0,     str(row["cream_used_ghee"]))
        self.e_sold.insert(0,     str(row["cream_sold"]))
        self.e_wasted.insert(0,   str(row["cream_wasted"]))
        self.e_supplier.insert(0, row["supplier_name"] or "")
        self.e_notes.insert(0,    row["notes"] or "")

        if row["employee_name"]:
            self.emp_var.set(row["employee_name"])

        self._live_calc()

    def _edit_selected(self):
        sel = self.rec_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to edit.")
            return
        vals = self.rec_tree.item(sel, "values")
        row  = get_cream_entry_by_id(int(vals[0]))
        if row:
            self._fill_form(row)
            self.tabs.set("➕ Add Entry")

    def _delete_selected(self):
        sel = self.rec_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to delete.")
            return
        eid = int(self.rec_tree.item(sel, "values")[0])
        if not messagebox.askyesno("⚠️ Confirm",
                                   f"Delete entry ID {eid}? Cannot be undone."):
            return
        success, msg = delete_cream_entry(eid)
        if success:
            messagebox.showinfo("✅", msg)
            self._load_records(clear=True)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌", msg)

    # ════════════════════════════════════════
    # TAB 3 — REPORTS
    # ════════════════════════════════════════

    def _build_reports_tab(self):
        tab = self.tabs.tab("📊 Reports")

        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0, 4))
        self.rpt_from = ctk.CTkEntry(frow, width=130,
                                     placeholder_text="YYYY-MM-DD")
        self.rpt_from.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0, 4))
        self.rpt_to = ctk.CTkEntry(frow, width=130,
                                   placeholder_text="YYYY-MM-DD")
        self.rpt_to.pack(side="left", padx=(0, 8))

        ctk.CTkButton(frow, text="📊 Generate Report", width=160,
                      command=self._generate_report).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="📅 This Month", width=120,
                      fg_color="#00695C", hover_color="#004D40",
                      command=self._this_month).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="📅 Today", width=90,
                      fg_color="#1565C0", hover_color="#0D47A1",
                      command=self._today_report).pack(side="left", padx=4)

        # Summary cards
        cards = ctk.CTkFrame(tab)
        cards.pack(fill="x", padx=15, pady=8)

        self.rpt_entries  = self._rpt_card(cards, "Total Entries",    "0",    "#1565C0")
        self.rpt_milk     = self._rpt_card(cards, "Milk (Litres)",    "0",    "#2E7D32")
        self.rpt_cream    = self._rpt_card(cards, "Cream (Kg)",       "0",    "#00695C")
        self.rpt_ghee     = self._rpt_card(cards, "→ Ghee (Kg)",      "0",    "#E65100")
        self.rpt_sold     = self._rpt_card(cards, "→ Sold (Kg)",      "0",    "#6A1B9A")
        self.rpt_wasted   = self._rpt_card(cards, "→ Wasted (Kg)",    "0",    "#B71C1C")
        self.rpt_yield    = self._rpt_card(cards, "Avg Yield %",      "0%",   "#0277BD")
        self.rpt_avg_fat  = self._rpt_card(cards, "Avg Fat %",        "0%",   "#558B2F")

        # Daily breakdown table
        ctk.CTkLabel(tab, text="📅 Daily Breakdown",
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=(8, 4))

        rpt_cols = ("Date", "Shift", "Milk (L)", "Fat %", "Cream (Kg)",
                    "→ Ghee", "→ Sold", "→ Wasted", "Balance", "Supplier", "Employee")
        rpt_cw   = {
            "Date": 100, "Shift": 75, "Milk (L)": 75, "Fat %": 60,
            "Cream (Kg)": 90, "→ Ghee": 75, "→ Sold": 75,
            "→ Wasted": 75, "Balance": 80,
            "Supplier": 130, "Employee": 120
        }

        rc = tk.Frame(tab, bg="#2b2b2b")
        rc.pack(fill="both", expand=True, padx=15, pady=4)

        self.rpt_tree = ttk.Treeview(rc, columns=rpt_cols, show="headings",
                                     style="Cream.Treeview", selectmode="none")
        for col in rpt_cols:
            self.rpt_tree.heading(col, text=col)
            self.rpt_tree.column(col, width=rpt_cw.get(col, 90), anchor="center")

        vsb = ttk.Scrollbar(rc, orient="vertical",   command=self.rpt_tree.yview)
        hsb = ttk.Scrollbar(rc, orient="horizontal", command=self.rpt_tree.xview)
        self.rpt_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.rpt_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        rc.rowconfigure(0, weight=1)
        rc.columnconfigure(0, weight=1)

    def _rpt_card(self, parent, label, val, color):
        f = ctk.CTkFrame(parent, fg_color=color, corner_radius=8)
        f.pack(side="left", expand=True, fill="both", padx=4, pady=6)
        ctk.CTkLabel(f, text=label, font=("Arial", 10),
                     text_color="white").pack(pady=(4, 0))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 13, "bold"),
                           text_color="white")
        lbl.pack(pady=(0, 4))
        return lbl

    def _today_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.rpt_from.delete(0, "end"); self.rpt_from.insert(0, today)
        self.rpt_to.delete(0, "end");   self.rpt_to.insert(0, today)
        self._generate_report()

    def _this_month(self):
        now = datetime.now()
        self.rpt_from.delete(0, "end")
        self.rpt_from.insert(0, now.strftime("%Y-%m-01"))
        self.rpt_to.delete(0, "end")
        self.rpt_to.insert(0, now.strftime("%Y-%m-%d"))
        self._generate_report()

    def _generate_report(self):
        df = self.rpt_from.get().strip() or None
        dt = self.rpt_to.get().strip() or None

        s = get_cream_summary(df, dt)
        self.rpt_entries.configure(text=str(s["entries"]))
        self.rpt_milk.configure(text=f"{s['milk']:g}")
        self.rpt_cream.configure(text=f"{s['cream']:g}")
        self.rpt_ghee.configure(text=f"{s['ghee']:g}")
        self.rpt_sold.configure(text=f"{s['sold']:g}")
        self.rpt_wasted.configure(text=f"{s['wasted']:g}")
        self.rpt_yield.configure(text=f"{s['yield_pct']}%")
        self.rpt_avg_fat.configure(text=f"{s['avg_fat']}%")

        rows = get_cream_entries(date_from=df, date_to=dt)
        for i in self.rpt_tree.get_children():
            self.rpt_tree.delete(i)
        for r in rows:
            cream   = float(r["cream_kg"])
            ghee    = float(r["cream_used_ghee"])
            sold    = float(r["cream_sold"])
            wasted  = float(r["cream_wasted"])
            balance = round(cream - ghee - sold - wasted, 3)
            self.rpt_tree.insert("", "end", values=(
                r["entry_date"], r["shift"],
                f"{float(r['milk_litres']):g}",
                f"{float(r['fat_percent']):g}",
                f"{cream:g}", f"{ghee:g}", f"{sold:g}",
                f"{wasted:g}", f"{balance:g}",
                r["supplier_name"] or "—",
                r["employee_name"] or "—"
            ))

    # ════════════════════════════════════════
    # TAB 4 — DAILY SUMMARY
    # ════════════════════════════════════════

    def _build_summary_tab(self):
        tab = self.tabs.tab("📈 Daily Summary")

        ctk.CTkLabel(tab, text="📈 Daily Production Summary (Last 30 Days)",
                     font=("Arial", 14, "bold")).pack(pady=(12, 6))

        ctk.CTkButton(tab, text="🔄 Refresh",
                      command=self._load_daily_summary,
                      fg_color="#2E7D32").pack(pady=(0, 8))

        sum_cols = ("Date", "Milk (L)", "Cream (Kg)", "Yield %")
        sc = tk.Frame(tab, bg="#2b2b2b")
        sc.pack(fill="both", expand=True, padx=15, pady=4)

        self.sum_tree = ttk.Treeview(sc, columns=sum_cols, show="headings",
                                     style="Cream.Treeview", selectmode="none")
        for col in sum_cols:
            self.sum_tree.heading(col, text=col)
            self.sum_tree.column(col, width=200, anchor="center")

        vsb = ttk.Scrollbar(sc, orient="vertical", command=self.sum_tree.yview)
        self.sum_tree.configure(yscrollcommand=vsb.set)
        self.sum_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        sc.rowconfigure(0, weight=1)
        sc.columnconfigure(0, weight=1)

        self._load_daily_summary()

    def _load_daily_summary(self):
        for i in self.sum_tree.get_children():
            self.sum_tree.delete(i)
        for r in get_daily_cream_data(days=30):
            milk  = float(r["milk"])
            cream = float(r["cream"])
            yld   = round(cream / milk * 100, 2) if milk > 0 else 0.0
            self.sum_tree.insert("", "end", values=(
                r["entry_date"],
                f"{milk:g} L",
                f"{cream:g} Kg",
                f"{yld}%"
            ))

    # ════════════════════════════════════════
    # ADD / UPDATE ENTRY
    # ════════════════════════════════════════

    def _add_entry(self):
        emp_id, emp_name = self._get_selected_employee()

        success, result = add_cream_entry(
            self.e_date.get().strip(),
            self.shift_var.get(),
            self.e_milk.get(),
            self.e_fat.get(),
            self.e_cream.get(),
            self.e_ghee.get(),
            self.e_sold.get(),
            self.e_wasted.get(),
            self.e_supplier.get().strip(),
            emp_id, emp_name,
            self.e_notes.get().strip()
        )
        if success:
            messagebox.showinfo("✅ Success",
                                f"Cream entry added! (ID: {result})")
            self._clear_fields()
            self._load_records(clear=True)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌ Error", result)

    def _update_entry(self):
        if not self._selected_id:
            messagebox.showwarning("⚠️", "Select a record to update.")
            return
        if not messagebox.askyesno("Confirm Update",
                                   f"Update entry ID {self._selected_id}?"):
            return

        emp_id, emp_name = self._get_selected_employee()

        success, msg = update_cream_entry(
            self._selected_id,
            self.e_date.get().strip(),
            self.shift_var.get(),
            self.e_milk.get(),
            self.e_fat.get(),
            self.e_cream.get(),
            self.e_ghee.get(),
            self.e_sold.get(),
            self.e_wasted.get(),
            self.e_supplier.get().strip(),
            emp_id, emp_name,
            self.e_notes.get().strip()
        )
        if success:
            messagebox.showinfo("✅ Success", msg)
            self._clear_fields()
            self._load_records(clear=True)
            self._refresh_dashboard()
        else:
            messagebox.showerror("❌ Error", msg)

    # ════════════════════════════════════════
    # REFRESH DASHBOARD
    # ════════════════════════════════════════

    def _refresh_dashboard(self):
        stock = get_current_cream_stock()
        s     = get_cream_summary()

        cur  = stock['current_stock']
        prod = stock['total_produced']

        self.s_stock.configure(text=f"{cur:g} Kg")
        self.s_produced.configure(text=f"{prod:g} Kg")
        self.s_ghee.configure(text=f"{stock['total_ghee']:g} Kg")
        self.s_sold.configure(text=f"{stock['total_sold']:g} Kg")
        self.s_wasted.configure(text=f"{stock['total_wasted']:g} Kg")
        self.s_yield.configure(text=f"{s['yield_pct']}%")

        # update the big stock box in Add Entry tab
        if self.lbl_cur_stock:
            color = "#B71C1C" if cur <= 0 else ("#E65100" if cur < 10 else "#1B5E20")
            self.stock_box.configure(fg_color=color)
            self.lbl_cur_stock.configure(text=f"{cur:g} Kg")

    # ════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════

    def _load_employees(self):
        self._employees = get_employees_list()
        names = ["Select Employee"] + [f"{e['name']} ({e['role']})"
                                        for e in self._employees]
        self.emp_menu.configure(values=names)
        self.emp_var.set("Select Employee")

    def _get_selected_employee(self):
        val = self.emp_var.get()
        if val == "Select Employee":
            return None, ""
        for e in self._employees:
            if val.startswith(e["name"]):
                return e["id"], e["name"]
        return None, val

    def _two_col(self, parent, label):
        ctk.CTkLabel(parent, text=label, anchor="w",
                     font=("Arial", 11)).pack(fill="x", padx=8, pady=(4,0))

    def _field(self, parent, placeholder):
        ctk.CTkLabel(parent, text=placeholder, anchor="w").pack(fill="x", padx=8)
        e = ctk.CTkEntry(parent, width=380, placeholder_text=placeholder)
        e.pack(padx=8, pady=(0, 8))
        return e

    def _clear_fields(self):
        self._selected_id = None
        self.e_id.configure(state="normal")
        self.e_id.delete(0, "end")
        self.e_id.configure(state="readonly")

        for e in [self.e_date, self.e_milk, self.e_fat, self.e_cream,
                  self.e_ghee, self.e_sold, self.e_wasted,
                  self.e_supplier, self.e_notes]:
            e.delete(0, "end")

        self.e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.shift_var.set("Morning")
        self.emp_var.set("Select Employee")
        self._live_calc()