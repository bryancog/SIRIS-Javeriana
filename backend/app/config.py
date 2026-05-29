from pathlib import Path
import os

from fastapi import HTTPException


APP_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = APP_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent

FRONTEND_ROOT = PROJECT_ROOT / "frontend"
DATA_ROOT = BACKEND_ROOT / "data"
EXPORTS_ROOT = DATA_ROOT / "area_exports"
WEB_EXPORTS_ROOT = DATA_ROOT / "web_exports"
DB_PATH = DATA_ROOT / "siris.db"

EXPORTS_ROOT.mkdir(parents=True, exist_ok=True)

NPY_ROOTS = [
    Path(item.strip())
    for item in (
        os.environ.get("SIRIS_NPY_ROOTS")
        or str(DATA_ROOT / "outputs_sr_x4_lanczos")
    ).split(os.pathsep)
    if item.strip()
]

MASK_ROOT = Path(
    os.environ.get("SIRIS_MASK_ROOT")
    or str(DATA_ROOT / "outputs_imputation_masks")
)

GEOTIFF_WORKERS = os.environ.get("SIRIS_GEOTIFF_WORKERS", "2")

SESSION_COOKIE = "siris_session"

TEST_USER = {
    "username": "demo",
    "password": "demo123",
    "name": "Usuario Demo"
}


def safe_file_path(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    file_path = (root / relative_path).resolve()

    try:
        file_path.relative_to(root_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    return file_path
