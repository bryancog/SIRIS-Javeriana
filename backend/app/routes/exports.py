from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import EXPORTS_ROOT, safe_file_path


router = APIRouter()


@router.get("/exports/{file_path:path}")
def serve_export(file_path: str):
    target = safe_file_path(EXPORTS_ROOT, file_path)

    if not target.exists() or not target.is_file():
        return PlainTextResponse("Archivo no encontrado.", status_code=404)

    return FileResponse(
        target,
        filename=target.name if target.suffix.lower() == ".zip" else None
    )
