from typing import Optional

from fastapi import FastAPI, Cookie, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.config import FRONTEND_ROOT, DATA_ROOT, safe_file_path
from app.routes import auth, area, exports
from app.routes.auth import get_session


app = FastAPI(
    title="SIRIS API",
    description="API para dashboard satelital SIRIS",
    version="1.0.0"
)

app.include_router(auth.router, tags=["Autenticación"])
app.include_router(area.router, tags=["Exportación de áreas"])
app.include_router(exports.router, tags=["Descarga de archivos"])


@app.get("/")
def root(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)
    return RedirectResponse(url="/dashboard.html" if session else "/index.html")


@app.get("/api/study-area")
def api_study_area():
    geojson_path = DATA_ROOT / "study_area.geojson"

    if not geojson_path.exists():
        raise HTTPException(status_code=500, detail="No se pudo leer el area de estudio.")

    return FileResponse(
        geojson_path,
        media_type="application/json"
    )


@app.get("/index.html")
def index_html(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if session:
        return RedirectResponse(url="/dashboard.html")

    file_path = FRONTEND_ROOT / "index.html"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="index.html no encontrado.")

    return FileResponse(file_path)


@app.get("/dashboard.html")
def dashboard_html(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if not session:
        return RedirectResponse(url="/index.html")

    file_path = FRONTEND_ROOT / "dashboard.html"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="dashboard.html no encontrado.")

    return FileResponse(file_path)


@app.get("/{file_path:path}")
def serve_frontend_file(file_path: str):
    if file_path.startswith("api/") or file_path.startswith("exports/"):
        raise HTTPException(status_code=404, detail="Ruta no encontrada.")

    target = safe_file_path(FRONTEND_ROOT, file_path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return FileResponse(target)
