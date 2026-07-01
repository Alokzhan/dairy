import customtkinter as ctk
import sqlite3
import os
from tkinter import messagebox

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class LoginApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Dairy ERP System")
        self.geometry("500x400")
        self.resizable(False, False)

        title = ctk.CTkLabel(
            self,
            text="DAIRY ERP SYSTEM",
            font=("Arial", 24, "bold")
        )
        title.pack(pady=30)

        self.username = ctk.CTkEntry(
            self,
            width=250,
            placeholder_text="Username"
        )
        self.username.pack(pady=10)

        self.password = ctk.CTkEntry(
            self,
            width=250,
            placeholder_text="Password",
            show="*"
        )
        self.password.pack(pady=10)

        login_btn = ctk.CTkButton(
            self,
            text="Login",
            width=200,
            command=self.login
        )
        login_btn.pack(pady=20)

        # Enter key triggers login
        self.bind("<Return>", lambda e: self.login())

    def login(self):

        user = self.username.get().strip()
        pwd  = self.password.get().strip()

        if not user or not pwd:
            messagebox.showwarning(
                "Missing Fields",
                "Please enter both username and password."
            )
            return

        BASE_DIR = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
        DB_PATH = os.path.join(BASE_DIR, "dairy.db")

        print("Database Path:", DB_PATH)

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            print("Tables Found:", cursor.fetchall())

            cursor.execute(
                "SELECT role FROM users WHERE username=? AND password=?",
                (user, pwd)
            )
            result = cursor.fetchone()
            conn.close()

            if result:

                # normalize role to lowercase for safe comparison
                role = result[0].strip().lower()

                print(f"Role found: '{role}'")

                # ── Super Admin ──────────────────────────
                if role in ("superadmin", "super admin", "super_admin"):
                    from gui.super_admin import SuperAdmin
                    self.withdraw()
                    app = SuperAdmin()
                    app.protocol("WM_DELETE_WINDOW", lambda: self._close(app))
                    app.mainloop()

                # ── Cream Admin ──────────────────────────
                elif role in ("creamadmin", "cream admin", "cream_admin"):
                    from gui.cream_admin import CreamAdmin
                    self.withdraw()
                    app = CreamAdmin()
                    app.protocol("WM_DELETE_WINDOW", lambda: self._close(app))
                    app.mainloop()

                # ── Ghee Admin ───────────────────────────
                elif role in ("gheeadmin", "ghee admin", "ghee_admin"):
                    from gui.ghee_admin import GheeAdmin
                    self.withdraw()
                    app = GheeAdmin()
                    app.protocol("WM_DELETE_WINDOW", lambda: self._close(app))
                    app.mainloop()

                # ── Employee ─────────────────────────────
                elif role == "employee":
                    from gui.employee_panel import EmployeePanel
                    self.withdraw()
                    app = EmployeePanel(self)
                    app.protocol("WM_DELETE_WINDOW", lambda: self._close(app))

                else:
                    messagebox.showerror(
                        "Unknown Role",
                        f"Role '{result[0]}' is not recognized.\n"
                        "Contact your administrator."
                    )

            else:
                messagebox.showerror(
                    "Login Failed",
                    "Invalid Username or Password.\n"
                    "Default: admin / admin123"
                )

        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def _close(self, window):
        """Close dashboard -> also exit the whole app."""
        window.destroy()
        self.destroy()


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()