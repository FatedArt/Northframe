"""Northframe dashboard entrypoint.

Jalankan aplikasi dari root `northframe/`:
    python3 app.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from jinja2 import FileSystemLoader


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE_DIR = PROJECT_ROOT / "design-audit" / "design-system-audit"
MODULE_APP_FILE = MODULE_DIR / "app.py"


def _load_dashboard_app():
    if not MODULE_APP_FILE.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {MODULE_APP_FILE}")

    if str(MODULE_DIR) not in sys.path:
        sys.path.insert(0, str(MODULE_DIR))

    spec = importlib.util.spec_from_file_location("northframe_design_system_audit_app", MODULE_APP_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Gagal memuat modul dashboard Northframe.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


app = _load_dashboard_app()
app.root_path = str(MODULE_DIR)
app.template_folder = str(MODULE_DIR / "templates")
app.jinja_loader = FileSystemLoader(app.template_folder)


if __name__ == "__main__":
    debug_flag = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5555"))
    app.run(debug=debug_flag, port=port)
