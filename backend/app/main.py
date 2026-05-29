from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import DATA_ROOT, FRONTEND_ROOT, safe_file_path
from app.db import ensure_demo_user, init_db
from app.routes import area, auth, exports

FRONTEND_DIST_ROOT = FRONTEND_ROOT / "dist"
FRONTEND_ASSETS_ROOT = FRONTEND_DIST_ROOT / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_demo_user()
    yield


app = FastAPI(
    title="SIRIS API",
    description="API para dashboard satelital SIRIS",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router, tags=["Autenticación"])
app.include_router(area.router, tags=["Exportación de áreas"])
app.include_router(exports.router, tags=["Descarga de archivos"])

if FRONTEND_ASSETS_ROOT.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_ASSETS_ROOT),
        name="frontend-assets",
    )


@app.get("/api/study-area")
def api_study_area():
    geojson_path = DATA_ROOT / "study_area.geojson"
    if not geojson_path.exists():
        raise HTTPException(status_code=500, detail="No se pudo leer el área de estudio.")
    return FileResponse(geojson_path, media_type="application/json")


def serve_react_index():
    index_path = FRONTEND_DIST_ROOT / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Frontend React no compilado. Ejecuta: "
                "cd frontend && npm install && npm run build"
            ),
        )
    return FileResponse(index_path)


@app.get("/")
def root():
    return serve_react_index()


@app.get("/{file_path:path}")
def serve_frontend_app(file_path: str):
    if file_path.startswith("api/") or file_path.startswith("exports/"):
        raise HTTPException(status_code=404, detail="Ruta no encontrada.")

    target = safe_file_path(FRONTEND_DIST_ROOT, file_path)
    if target.exists() and target.is_file():
        return FileResponse(target)

    return serve_react_index()
