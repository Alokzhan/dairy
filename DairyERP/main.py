# main.py — updated for deployment
# Ensures all tables are created before GUI starts
# and sets correct working directory for PyInstaller

import sys
import os

# ── Fix working directory for PyInstaller .exe ─────────────────────────────
# When running as a bundled .exe, set cwd to the folder containing the exe
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    os.chdir(os.path.dirname(sys.executable))
else:
    # Running in development (PyCharm)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Create all DB tables on startup ────────────────────────────────────────
from database.db import create_tables
create_tables()

# ── Launch GUI ─────────────────────────────────────────────────────────────
from gui.login import LoginApp

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()