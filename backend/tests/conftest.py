import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Cliente de pruebas FastAPI usando una base SQLite temporal.

    La aplicación SIRIS define DB_PATH como constante en app.config y app.db.
    Para no modificar backend/data/siris.db, esta fixture redirige ambos valores
    hacia tmp_path antes de importar app.main.
    """

    test_db_path = tmp_path / "siris_test.db"
    test_exports_root = tmp_path / "area_exports"
    test_web_exports_root = tmp_path / "web_exports"
    test_exports_root.mkdir(parents=True, exist_ok=True)
    test_web_exports_root.mkdir(parents=True, exist_ok=True)

    # Evita que una importación previa deje el estado de sesiones o rutas fijo.
    modules_to_reload = [
        "app.main",
        "app.routes.auth",
        "app.routes.area",
        "app.routes.exports",
        "app.db",
        "app.config",
    ]

    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]

    import app.config as config

    monkeypatch.setattr(config, "DB_PATH", test_db_path, raising=False)
    monkeypatch.setattr(config, "EXPORTS_ROOT", test_exports_root, raising=False)
    monkeypatch.setattr(config, "WEB_EXPORTS_ROOT", test_web_exports_root, raising=False)

    import app.db as db

    monkeypatch.setattr(db, "DB_PATH", test_db_path, raising=False)

    # Importa app.main después del monkeypatch.
    import app.main as main
    import app.routes.auth as auth

    auth.sessions.clear()

    with TestClient(main.app) as test_client:
        yield test_client
