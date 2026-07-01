import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime

from models.ghee import (
    ensure_ghee_tables,
    add_ghee_entry,
    get_ghee_entries,
    get_ghee_entry_by_id,
    update_ghee_entry,
    delete_ghee_entry,
    get_current_ghee_stock,
    get_available_cream_stock,
    get_ghee_summary,
    get_daily_ghee_data,
    get_employees_list
)

SHIFTS = ["Morning", "Evening", "Night", "Full Day"]
PACKET_SIZES = ["100g", "200g", "250g", "500g", "1Kg", "5Kg", "15Kg Tin", "Loose"]


class GheeAdmin(ctk.CTkToplevel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Ghee Production Management")
        self.geometry("1350x820")
        self.resizable(True, True)

        ensure_ghee_tables()

        self._selected_id = None
        self._employees   = []
        self.lbl_cur_stock = None
        self.lbl_avail_cream = None

        self._build_ui()
        self.after(100, self._refresh_dashboard)

    # ════════════════════════════════════════
    # BUILD UI
    # ════════════════════════════════════════

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="🫙  GHEE PRODUCTION MANAGEMENT",
            font=("Arial", 22, "bold")
        ).pack(pady=(12, 4))

        dash = ctk.CTkFrame(self, height=62)
        dash.pack(fill="x", padx=20, pady=(0, 8))
        dash.pack_propagate(False)

        self.s_stock     = self._stat(dash, "🫙 Ghee Stock (Kg)",     "0",  "#F9A825")
        self.s_cream_avl = self._stat(dash, "🥛 Cream Available (Kg)","0",  "#1565C0")
        self.s_produced  = self._stat(dash, "📦 Total Produced",     "0",  "#2E7D32")
        self.s_sold      = self._stat(dash, "💰 Sold (Kg)",          "0",  "#6A1B9A")
        self.s_dist      = self._stat(dash, "🚚 Distributed (Kg)",   "0",  "#00695C")
        self.s_yield     = self._stat(dash, "📊 Avg Yield %",        "0%", "#E65100")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for t in ["➕ Add Entry", "📋 Production Records",
                  "📊 Reports", "📈 Daily Summary"]:
            self.tabs.add(t)

        self._build_add_tab()
        self._build_records_tab()
        self._build_reports_tab()
        self._build_summary_tab()

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
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        # ── LEFT: Form ─────────────────────────────────────
        left = ctk.CTkFrame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=4)

        scroll = ctk.CTkScrollableFrame(
            left, label_text="➕ New Ghee Production Entry",
            label_font=("Arial", 14, "bold"))
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Entry ID
        self._lbl(scroll, "Entry ID (auto)")
        self.e_id = ctk.CTkEntry(scroll, width=370,
                                  placeholder_text="Auto-generated",
                                  state="readonly")
        self.e_id.pack(padx=8, pady=(0, 6))

        # Date
        self._lbl(scroll, "📅 Entry Date (YYYY-MM-DD) *")
        self.e_date = ctk.CTkEntry(scroll, width=370)
        self.e_date.pack(padx=8, pady=(0, 6))
        self.e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Shift
        self._lbl(scroll, "⏰ Shift")
        self.shift_var = ctk.StringVar(value="Morning")
        ctk.CTkOptionMenu(scroll, variable=self.shift_var,
                          values=SHIFTS, width=370).pack(padx=8, pady=(0, 6))

        # Available cream info box
        self.avail_box = ctk.CTkFrame(scroll, fg_color="#1565C0", corner_radius=8)
        self.avail_box.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(self.avail_box, text="🥛 Cream Available from Cream Production",
                     font=("Arial", 11), text_color="white").pack(pady=(6,0))
        self.lbl_avail_cream = ctk.CTkLabel(
            self.avail_box, text="0.000 Kg",
            font=("Arial", 18, "bold"), text_color="white")
        self.lbl_avail_cream.pack(pady=(0,8))

        # Cream used
        self._lbl(scroll, "🥛 Cream Used (Kg) *")
        self.e_cream_used = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_cream_used.pack(padx=8, pady=(0, 6))
        self.e_cream_used.bind("<KeyRelease>", self._live_calc)

        # Ghee produced
        self._lbl(scroll, "🫙 Ghee Produced (Kg) *")
        self.e_ghee = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_ghee.pack(padx=8, pady=(0, 6))
        self.e_ghee.bind("<KeyRelease>", self._live_calc)

        # Packaged qty
        self._lbl(scroll, "📦 Packaged Quantity")
        self.e_packaged = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_packaged.pack(padx=8, pady=(0, 6))
        self.e_packaged.bind("<KeyRelease>", self._live_calc)

        # Packet size
        self._lbl(scroll, "📏 Packet Size")
        self.packet_var = ctk.StringVar(value="Select Size")
        ctk.CTkOptionMenu(scroll, variable=self.packet_var,
                          values=PACKET_SIZES, width=370).pack(padx=8, pady=(0, 6))

        # Sold
        self._lbl(scroll, "💰 Ghee Sold (Kg)")
        self.e_sold = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_sold.pack(padx=8, pady=(0, 6))
        self.e_sold.bind("<KeyRelease>", self._live_calc)

        # Distributed
        self._lbl(scroll, "🚚 Distributed to Distributors (Kg)")
        self.e_dist = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_dist.pack(padx=8, pady=(0, 6))
        self.e_dist.bind("<KeyRelease>", self._live_calc)

        # Wasted
        self._lbl(scroll, "🗑️ Wasted / Loss (Kg)")
        self.e_wasted = ctk.CTkEntry(scroll, width=370, placeholder_text="0")
        self.e_wasted.pack(padx=8, pady=(0, 6))
        self.e_wasted.bind("<KeyRelease>", self._live_calc)

        # Batch number
        self._lbl(scroll, "🔖 Batch Number")
        self.e_batch = ctk.CTkEntry(scroll, width=370, placeholder_text="e.g. GH-001")
        self.e_batch.pack(padx=8, pady=(0, 6))

        # Employee
        self._lbl(scroll, "👨‍💼 Employee")
        self.emp_var = ctk.StringVar(value="Select Employee")
        self.emp_menu = ctk.CTkOptionMenu(
            scroll, variable=self.emp_var,
            values=["Select Employee"], width=370
        )
        self.emp_menu.pack(padx=8, pady=(0, 6))
        self._load_employees()

        # Notes
        self._lbl(scroll, "📝 Notes")
        self.e_notes = ctk.CTkEntry(scroll, width=370, placeholder_text="Optional")
        self.e_notes.pack(padx=8, pady=(0, 8))

        # Buttons
        ctk.CTkButton(
            scroll, text="➕  Add Entry",
            fg_color="#F9A825", hover_color="#F57F17",
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

        # ── RIGHT: Live Calculation ────────────────────────
        right = ctk.CTkFrame(tab)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=4)

        ctk.CTkLabel(right, text="🔢 Live Calculation",
                     font=("Arial", 14, "bold")).pack(pady=(16, 8))

        self.calc_frame = ctk.CTkFrame(right, fg_color="#1e1e1e", corner_radius=10)
        self.calc_frame.pack(fill="x", padx=15, pady=4)

        self.lbl_cream_in   = self._calc_row(self.calc_frame, "Cream Used",       "0 Kg")
        self.lbl_ghee_out   = self._calc_row(self.calc_frame, "Ghee Produced",    "0 Kg")
        self.lbl_yield      = self._calc_row(self.calc_frame, "Yield %",          "0%")

        ctk.CTkLabel(self.calc_frame, text="─"*30, text_color="gray").pack(pady=4)

        self.lbl_packaged   = self._calc_row(self.calc_frame, "Packaged",         "0")
        self.lbl_sold_out   = self._calc_row(self.calc_frame, "→ Sold",           "0 Kg")
        self.lbl_dist_out   = self._calc_row(self.calc_frame, "→ Distributed",    "0 Kg")
        self.lbl_waste_out  = self._calc_row(self.calc_frame, "→ Wasted",         "0 Kg")

        ctk.CTkLabel(self.calc_frame, text="─"*30, text_color="gray").pack(pady=4)

        self.lbl_balance    = self._calc_row(self.calc_frame, "Balance in Hand",  "0 Kg",
                                             bold=True, color="#FFD54F")

        ctk.CTkLabel(right, text="🫙 Current Ghee Stock",
                     font=("Arial", 13, "bold")).pack(pady=(20, 6))

        self.stock_box = ctk.CTkFrame(right, fg_color="#F57F17", corner_radius=10)
        self.stock_box.pack(fill="x", padx=15, pady=4)

        self.lbl_cur_stock = ctk.CTkLabel(
            self.stock_box, text="0.000 Kg",
            font=("Arial", 28, "bold"), text_color="white"
        )
        self.lbl_cur_stock.pack(pady=16)

        ctk.CTkButton(
            right, text="🔄 Refresh Stock",
            fg_color="#E65100", hover_color="#BF360C",
            command=self._refresh_dashboard
        ).pack(padx=15, pady=8, fill="x")

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, anchor="w",
                     font=("Arial", 11)).pack(fill="x", padx=8, pady=(4,0))

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

        cream    = fval(self.e_cream_used)
        ghee     = fval(self.e_ghee)
        packaged = fval(self.e_packaged)
        sold     = fval(self.e_sold)
        dist     = fval(self.e_dist)
        wasted   = fval(self.e_wasted)

        yield_pct = round(ghee / cream * 100, 2) if cream > 0 else 0.0
        balance   = round(ghee - sold - dist - wasted, 3)

        self.lbl_cream_in.configure(text=f"{cream:g} Kg")
        self.lbl_ghee_out.configure(text=f"{ghee:g} Kg")
        self.lbl_yield.configure(text=f"{yield_pct}%")
        self.lbl_packaged.configure(text=f"{packaged:g}")
        self.lbl_sold_out.configure(text=f"{sold:g} Kg")
        self.lbl_dist_out.configure(text=f"{dist:g} Kg")
        self.lbl_waste_out.configure(text=f"{wasted:g} Kg")

        # check against available cream
        avail = get_available_cream_stock()["available_cream"]
        if cream > avail:
            self.lbl_cream_in.configure(text=f"{cream:g} Kg ⚠️ exceeds!", text_color="#EF5350")
        else:
            self.lbl_cream_in.configure(text_color="white")

        color = "#EF9A9A" if balance < 0 else "#FFD54F"
        self.lbl_balance.configure(text=f"{balance:g} Kg", text_color=color)

    # ════════════════════════════════════════
    # TAB 2 — PRODUCTION RECORDS
    # ════════════════════════════════════════

    def _build_records_tab(self):
        tab = self.tabs.tab("📋 Production Records")

        frow = ctk.CTkFrame(tab, fg_color="transparent")
        frow.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(frow, text="From:").pack(side="left", padx=(0, 4))
        self.rec_from = ctk.CTkEntry(frow, width=120, placeholder_text="YYYY-MM-DD")
        self.rec_from.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0, 4))
        self.rec_to = ctk.CTkEntry(frow, width=120, placeholder_text="YYYY-MM-DD")
        self.rec_to.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="Shift:").pack(side="left", padx=(0, 4))
        self.rec_shift_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(frow, variable=self.rec_shift_var,
                          values=["All"] + SHIFTS, width=120).pack(side="left", padx=(0, 8))

        ctk.CTkButton(frow, text="🔍 Filter", width=80,
                      command=self._load_records).pack(side="left", padx=(0, 6))
        ctk.CTkButton(frow, text="🔄 All", width=70,
                      fg_color="#4CAF50", hover_color="#1B5E20",
                      command=lambda: self._load_records(clear=True)).pack(side="left")

        cols = ("ID", "Date", "Shift", "Cream (Kg)", "Ghee (Kg)",
                "Packed", "Size", "→ Sold", "→ Dist", "→ Wasted",
                "Balance", "Batch", "Employee", "Notes")
        cw = {
            "ID": 40, "Date": 100, "Shift": 75, "Cream (Kg)": 85,
            "Ghee (Kg)": 80, "Packed": 65, "Size": 70,
            "→ Sold": 70, "→ Dist": 65, "→ Wasted": 70,
            "Balance": 75, "Batch": 80, "Employee": 110, "Notes": 140
        }

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Ghee.Treeview",
            background="#2b2b2b", foreground="white",
            rowheight=27, fieldbackground="#2b2b2b", font=("Arial", 11))
        style.configure("Ghee.Treeview.Heading",
            background="#F57F17", foreground="white", font=("Arial", 11, "bold"))
        style.map("Ghee.Treeview", background=[("selected", "#FB8C00")])

        tc = tk.Frame(tab, bg="#2b2b2b")
        tc.pack(fill="both", expand=True, padx=10, pady=4)

        self.rec_tree = ttk.Treeview(tc, columns=cols, show="headings",
                                     style="Ghee.Treeview", selectmode="browse")
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
                      command=lambda: self._load_records(clear=True)).pack(side="left", padx=4)

        self._load_records(clear=True)

    def _load_records(self, clear=False):
        if clear:
            self.rec_from.delete(0, "end")
            self.rec_to.delete(0, "end")
            self.rec_shift_var.set("All")

        rows = get_ghee_entries(
            date_from=self.rec_from.get().strip() or None,
            date_to=self.rec_to.get().strip() or None,
            shift=self.rec_shift_var.get()
        )
        for i in self.rec_tree.get_children():
            self.rec_tree.delete(i)

        for r in rows:
            ghee    = float(r["ghee_produced"])
            sold    = float(r["ghee_sold"])
            dist    = float(r["ghee_distributed"])
            wasted  = float(r["ghee_wasted"])
            balance = round(ghee - sold - dist - wasted, 3)
            self.rec_tree.insert("", "end", values=(
                r["id"], r["entry_date"], r["shift"],
                f"{float(r['cream_used_kg']):g}",
                f"{ghee:g}",
                f"{float(r['packaged_qty']):g}",
                r["packet_size"] or "—",
                f"{sold:g}", f"{dist:g}", f"{wasted:g}",
                f"{balance:g}",
                r["batch_number"] or "—",
                r["employee_name"] or "—",
                r["notes"] or ""
            ))

    def _on_row_select(self, event):
        sel = self.rec_tree.focus()
        if not sel: return
        vals = self.rec_tree.item(sel, "values")
        row = get_ghee_entry_by_id(int(vals[0]))
        if row:
            self._fill_form(row)
            self.tabs.set("➕ Add Entry")

    def _fill_form(self, row):
        self._clear_fields()
        self._selected_id = row["id"]

        self.e_id.configure(state="normal")
        self.e_id.insert(0, row["id"])
        self.e_id.configure(state="readonly")

        self.e_date.insert(0, row["entry_date"])
        self.shift_var.set(row["shift"])
        self.e_cream_used.insert(0, str(row["cream_used_kg"]))
        self.e_ghee.insert(0, str(row["ghee_produced"]))
        self.e_packaged.insert(0, str(row["packaged_qty"]))
        if row["packet_size"]:
            self.packet_var.set(row["packet_size"])
        self.e_sold.insert(0, str(row["ghee_sold"]))
        self.e_dist.insert(0, str(row["ghee_distributed"]))
        self.e_wasted.insert(0, str(row["ghee_wasted"]))
        self.e_batch.insert(0, row["batch_number"] or "")
        self.e_notes.insert(0, row["notes"] or "")

        if row["employee_name"]:
            self.emp_var.set(row["employee_name"])

        self._live_calc()

    def _edit_selected(self):
        sel = self.rec_tree.focus()
        if not sel:
            messagebox.showwarning("⚠️", "Select a record to edit.")
            return
        vals = self.rec_tree.item(sel, "values")
        row = get_ghee_entry_by_id(int(vals[0]))
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
        success, msg = delete_ghee_entry(eid)
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
        self.rpt_from = ctk.CTkEntry(frow, width=130, placeholder_text="YYYY-MM-DD")
        self.rpt_from.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(frow, text="To:").pack(side="left", padx=(0, 4))
        self.rpt_to = ctk.CTkEntry(frow, width=130, placeholder_text="YYYY-MM-DD")
        self.rpt_to.pack(side="left", padx=(0, 8))

        ctk.CTkButton(frow, text="📊 Generate Report", width=160,
                      command=self._generate_report).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="📅 This Month", width=120,
                      fg_color="#00695C", hover_color="#004D40",
                      command=self._this_month).pack(side="left", padx=4)
        ctk.CTkButton(frow, text="📅 Today", width=90,
                      fg_color="#1565C0", hover_color="#0D47A1",
                      command=self._today_report).pack(side="left", padx=4)

        cards = ctk.CTkFrame(tab)
        cards.pack(fill="x", padx=15, pady=8)

        self.rpt_entries = self._rpt_card(cards, "Entries",      "0",  "#1565C0")
        self.rpt_cream   = self._rpt_card(cards, "Cream Used",   "0",  "#0277BD")
        self.rpt_ghee    = self._rpt_card(cards, "Ghee Made",    "0",  "#F9A825")
        self.rpt_packed  = self._rpt_card(cards, "Packaged",     "0",  "#558B2F")
        self.rpt_sold    = self._rpt_card(cards, "Sold",         "0",  "#6A1B9A")
        self.rpt_dist    = self._rpt_card(cards, "Distributed",  "0",  "#00695C")
        self.rpt_wasted  = self._rpt_card(cards, "Wasted",       "0",  "#B71C1C")
        self.rpt_yield   = self._rpt_card(cards, "Avg Yield %",  "0%", "#E65100")

        ctk.CTkLabel(tab, text="📅 Daily Breakdown",
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=(8, 4))

        rpt_cols = ("Date", "Shift", "Cream (Kg)", "Ghee (Kg)",
                    "Packed", "→ Sold", "→ Dist", "→ Wasted", "Balance", "Employee")
        rpt_cw = {
            "Date": 100, "Shift": 75, "Cream (Kg)": 85, "Ghee (Kg)": 80,
            "Packed": 70, "→ Sold": 70, "→ Dist": 65,
            "→ Wasted": 70, "Balance": 75, "Employee": 130
        }

        rc = tk.Frame(tab, bg="#2b2b2b")
        rc.pack(fill="both", expand=True, padx=15, pady=4)

        self.rpt_tree = ttk.Treeview(rc, columns=rpt_cols, show="headings",
                                     style="Ghee.Treeview", selectmode="none")
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

        s = get_ghee_summary(df, dt)
        self.rpt_entries.configure(text=str(s["entries"]))
        self.rpt_cream.configure(text=f"{s['cream']:g}")
        self.rpt_ghee.configure(text=f"{s['ghee']:g}")
        self.rpt_packed.configure(text=f"{s['packaged']:g}")
        self.rpt_sold.configure(text=f"{s['sold']:g}")
        self.rpt_dist.configure(text=f"{s['distributed']:g}")
        self.rpt_wasted.configure(text=f"{s['wasted']:g}")
        self.rpt_yield.configure(text=f"{s['yield_pct']}%")

        rows = get_ghee_entries(date_from=df, date_to=dt)
        for i in self.rpt_tree.get_children():
            self.rpt_tree.delete(i)
        for r in rows:
            ghee    = float(r["ghee_produced"])
            sold    = float(r["ghee_sold"])
            dist    = float(r["ghee_distributed"])
            wasted  = float(r["ghee_wasted"])
            balance = round(ghee - sold - dist - wasted, 3)
            self.rpt_tree.insert("", "end", values=(
                r["entry_date"], r["shift"],
                f"{float(r['cream_used_kg']):g}",
                f"{ghee:g}",
                f"{float(r['packaged_qty']):g}",
                f"{sold:g}", f"{dist:g}", f"{wasted:g}",
                f"{balance:g}",
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
                      fg_color="#E65100").pack(pady=(0, 8))

        sum_cols = ("Date", "Cream Used (Kg)", "Ghee Produced (Kg)", "Yield %")
        sc = tk.Frame(tab, bg="#2b2b2b")
        sc.pack(fill="both", expand=True, padx=15, pady=4)

        self.sum_tree = ttk.Treeview(sc, columns=sum_cols, show="headings",
                                     style="Ghee.Treeview", selectmode="none")
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
        for r in get_daily_ghee_data(days=30):
            cream = float(r["cream"])
            ghee  = float(r["ghee"])
            yld   = round(ghee / cream * 100, 2) if cream > 0 else 0.0
            self.sum_tree.insert("", "end", values=(
                r["entry_date"], f"{cream:g} Kg", f"{ghee:g} Kg", f"{yld}%"
            ))

    # ════════════════════════════════════════
    # ADD / UPDATE ENTRY
    # ════════════════════════════════════════

    def _add_entry(self):
        emp_id, emp_name = self._get_selected_employee()
        packet_size = self.packet_var.get() if self.packet_var.get() != "Select Size" else ""

        success, result = add_ghee_entry(
            self.e_date.get().strip(),
            self.shift_var.get(),
            self.e_cream_used.get(),
            self.e_ghee.get(),
            self.e_packaged.get(),
            packet_size,
            self.e_sold.get(),
            self.e_dist.get(),
            self.e_wasted.get(),
            self.e_batch.get().strip(),
            emp_id, emp_name,
            self.e_notes.get().strip()
        )
        if success:
            messagebox.showinfo("✅ Success", f"Ghee entry added! (ID: {result})")
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
        packet_size = self.packet_var.get() if self.packet_var.get() != "Select Size" else ""

        success, msg = update_ghee_entry(
            self._selected_id,
            self.e_date.get().strip(),
            self.shift_var.get(),
            self.e_cream_used.get(),
            self.e_ghee.get(),
            self.e_packaged.get(),
            packet_size,
            self.e_sold.get(),
            self.e_dist.get(),
            self.e_wasted.get(),
            self.e_batch.get().strip(),
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
        stock = get_current_ghee_stock()
        cream = get_available_cream_stock()
        s     = get_ghee_summary()

        cur = stock['current_stock']

        self.s_stock.configure(text=f"{cur:g} Kg")
        self.s_cream_avl.configure(text=f"{cream['available_cream']:g} Kg")
        self.s_produced.configure(text=f"{stock['total_produced']:g} Kg")
        self.s_sold.configure(text=f"{stock['total_sold']:g} Kg")
        self.s_dist.configure(text=f"{stock['total_distributed']:g} Kg")
        self.s_yield.configure(text=f"{s['yield_pct']}%")

        if self.lbl_avail_cream:
            avail = cream['available_cream']
            color = "#1565C0" if avail > 0 else "#B71C1C"
            self.avail_box.configure(fg_color=color)
            self.lbl_avail_cream.configure(text=f"{avail:g} Kg")

        if self.lbl_cur_stock:
            color = "#B71C1C" if cur <= 0 else ("#E65100" if cur < 10 else "#F57F17")
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

    def _clear_fields(self):
        self._selected_id = None
        self.e_id.configure(state="normal")
        self.e_id.delete(0, "end")
        self.e_id.configure(state="readonly")

        for e in [self.e_date, self.e_cream_used, self.e_ghee, self.e_packaged,
                  self.e_sold, self.e_dist, self.e_wasted, self.e_batch, self.e_notes]:
            e.delete(0, "end")

        self.e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.shift_var.set("Morning")
        self.packet_var.set("Select Size")
        self.emp_var.set("Select Employee")
        self._live_calc()