import time
from typing import Optional

from fastapi import APIRouter, Cookie
from fastapi.responses import JSONResponse

from app.config import (
    DATA_ROOT,
    EXPORTS_ROOT,
    WEB_EXPORTS_ROOT,
    NPY_ROOTS,
    MASK_ROOT,
    GEOTIFF_WORKERS
)
from app.schemas import AreaExportRequest
from app.routes.auth import get_session
from app.services.area_service import (
    run_area_export,
    run_geotiff_area_export,
    cancel_active_area_export,
    get_area_export_status
)


router = APIRouter()


@router.post("/api/area/export")
def api_area_export(
    payload: AreaExportRequest,
    siris_session: Optional[str] = Cookie(default=None)
):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesion no autenticada."}
        )

    has_polygon = payload.polygon is not None and len(payload.polygon) >= 3

    has_box = all(
        value is not None
        for value in [payload.row0, payload.col0, payload.height, payload.width]
    )

    if not has_polygon and not has_box:
        return JSONResponse(
            status_code=400,
            content={"message": "Parametros invalidos."}
        )

    if payload.dateFrom and payload.dateTo and payload.dateFrom > payload.dateTo:
        return JSONResponse(
            status_code=400,
            content={"message": "La fecha inicial no puede ser mayor que la fecha final."}
        )

    out_name = f"area_{int(time.time() * 1000)}"

    try:
        run_area_export(
            row0=payload.row0,
            col0=payload.col0,
            height=payload.height,
            width=payload.width,
            polygon=payload.polygon,
            date_from=payload.dateFrom,
            date_to=payload.dateTo,
            out_name=out_name,
            data_root=DATA_ROOT,
            exports_root=EXPORTS_ROOT,
            web_exports_root=WEB_EXPORTS_ROOT
        )

        geotiff_zip_file = None

        if has_polygon:
            run_geotiff_area_export(
                polygon=payload.polygon,
                date_from=payload.dateFrom,
                date_to=payload.dateTo,
                out_name=out_name,
                data_root=DATA_ROOT,
                exports_root=EXPORTS_ROOT,
                npy_roots=NPY_ROOTS,
                mask_root=MASK_ROOT,
                workers=GEOTIFF_WORKERS
            )

        export_dir = EXPORTS_ROOT / out_name

        if not export_dir.exists():
            raise RuntimeError("No se encontro la carpeta de exportacion.")

        files = [p.name for p in export_dir.iterdir() if p.is_file()]

        video_file = next(
            (file for file in files if file.lower().endswith(".mp4")),
            None
        )

        geotiff_zip_file = next(
            (
                file for file in files
                if file.lower().endswith(".zip") and "geotiff_csv" in file.lower()
            ),
            None
        )

        if not video_file:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "La exportacion termino, pero no se encontro el video MP4."
                }
            )

        return {
            "message": "Exportacion generada.",
            "outName": out_name,
            "videoUrl": f"/exports/{out_name}/{video_file}" if video_file else None,
            "geotiffZipUrl": f"/exports/{out_name}/{geotiff_zip_file}" if geotiff_zip_file else None
        }

    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Error generando exportacion.",
                "error": str(error)
            }
        )


@router.post("/api/area/cancel")
def api_area_cancel(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesion no autenticada."}
        )

    cancel_active_area_export(EXPORTS_ROOT)

    return {"message": "Exportacion cancelada."}


@router.get("/api/area/geotiff-status")
def api_geotiff_status(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesion no autenticada."}
        )

    return get_area_export_status()
