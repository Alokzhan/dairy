import customtkinter as ctk

ctk.set_appearance_mode("light")


class SuperAdmin(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Super Admin Dashboard")
        self.geometry("1100x700")
        self.resizable(True, True)

        # ── Title ──────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="🐄  DAIRY ERP SYSTEM — SUPER ADMIN",
            font=("Arial", 26, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="Select a module to manage",
            font=("Arial", 13),
            text_color="gray"
        ).pack(pady=(0, 15))

        # ── Button grid ────────────────────────────────────
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        # (label, emoji, color, hover_color, command_method)
        buttons = [
            ("Employee Management",  "👨‍💼", "#1565C0", "#0D47A1", self.open_employee),
            ("Product Management",   "🧈",  "#2E7D32", "#1B5E20", self.open_product),
            ("Customer Management",  "👥",  "#6A1B9A", "#4A148C", self.open_customer),
            ("Inventory",            "📦",  "#E65100", "#BF360C", self.open_inventory),
            ("Sales",                "🛒",  "#00695C", "#004D40", self.open_sales),
            ("Cream Production",     "🥛",  "#1565C0", "#0D47A1", self.open_cream),
            ("Ghee Production",      "🫙",  "#F9A825", "#F57F17", self.open_ghee),

            ("Payments",             "💳",  "#00838F", "#006064", self.open_payments),
            ("Reports",              "📊",  "#4527A0", "#311B92", self.open_reports),
        ]

        row = 0
        col = 0

        for (label, emoji, color, hover, cmd) in buttons:

            btn = ctk.CTkButton(
                frame,
                text=f"{emoji}\n{label}",
                width=220,
                height=90,
                font=("Arial", 14, "bold"),
                fg_color=color,
                hover_color=hover,
                corner_radius=12,
                command=cmd
            )
            btn.grid(row=row, column=col, padx=18, pady=18)

            col += 1
            if col == 4:
                col = 0
                row += 1

    # ==========================
    # OPEN PANELS
    # ==========================

    def open_employee(self):
        from gui.employee_panel import EmployeePanel
        EmployeePanel(self)

    def open_product(self):
        from gui.product_panel import ProductPanel
        ProductPanel(self)

    def open_customer(self):
        from gui.customer_panel import CustomerPanel
        CustomerPanel(self)

    def open_inventory(self):
        from gui.inventory_panel import InventoryPanel
        InventoryPanel(self)

    def open_sales(self):
        from gui.sales_panel import SalesPanel
        SalesPanel(self)

    def open_cream(self):
        from gui.cream_admin import CreamAdmin
        CreamAdmin(self)

    def open_ghee(self):
        from gui.ghee_admin import GheeAdmin
        GheeAdmin(self)



    def open_payments(self):
        from gui.payment_panel import PaymentPanel
        PaymentPanel(self)

    def open_reports(self):
        from gui.report_panel import ReportPanel
        ReportPanel(self)