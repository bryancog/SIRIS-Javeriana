import threading
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
    GEOTIFF_WORKERS,
)
from app.schemas import AreaExportRequest
from app.routes.auth import get_session
from app.services.area_service import (
    run_area_export,
    run_geotiff_area_export,
    cancel_active_area_export,
    get_area_export_status,
    set_area_export_status,
)


router = APIRouter()


def _find_export_outputs(out_name: str):
    export_dir = EXPORTS_ROOT / out_name

    if not export_dir.exists():
        raise RuntimeError("No se encontró la carpeta de exportación.")

    files = [p.name for p in export_dir.iterdir() if p.is_file()]

    video_file = next(
        (file for file in files if file.lower().endswith(".mp4")),
        None,
    )

    geotiff_zip_file = next(
        (
            file
            for file in files
            if file.lower().endswith(".zip") and "geotiff_csv" in file.lower()
        ),
        None,
    )

    return video_file, geotiff_zip_file


def _run_area_export_background(
    *,
    payload_data: dict,
    out_name: str,
    has_polygon: bool,
) -> None:
    try:
        set_area_export_status(
            running=True,
            stage="video",
            message="Generando video...",
            out_name=out_name,
        )

        run_area_export(
            row0=payload_data.get("row0"),
            col0=payload_data.get("col0"),
            height=payload_data.get("height"),
            width=payload_data.get("width"),
            polygon=payload_data.get("polygon"),
            date_from=payload_data.get("dateFrom"),
            date_to=payload_data.get("dateTo"),
            out_name=out_name,
            data_root=DATA_ROOT,
            exports_root=EXPORTS_ROOT,
            web_exports_root=WEB_EXPORTS_ROOT,
        )

        if has_polygon:
            set_area_export_status(
                running=True,
                stage="geotiff",
                message="Generando GeoTIFF...",
                out_name=out_name,
            )

            run_geotiff_area_export(
                polygon=payload_data.get("polygon"),
                date_from=payload_data.get("dateFrom"),
                date_to=payload_data.get("dateTo"),
                out_name=out_name,
                data_root=DATA_ROOT,
                exports_root=EXPORTS_ROOT,
                npy_roots=NPY_ROOTS,
                mask_root=MASK_ROOT,
                workers=GEOTIFF_WORKERS,
            )

        set_area_export_status(
            running=True,
            stage="zip",
            message="Validando archivos generados...",
            out_name=out_name,
        )

        video_file, geotiff_zip_file = _find_export_outputs(out_name)

        if not video_file:
            raise RuntimeError("La exportación terminó, pero no se encontró el video MP4.")

        video_url = f"/exports/{out_name}/{video_file}"
        geotiff_zip_url = (
            f"/exports/{out_name}/{geotiff_zip_file}" if geotiff_zip_file else None
        )

        set_area_export_status(
            running=False,
            stage="done",
            message="Exportación finalizada.",
            out_name=out_name,
            video_url=video_url,
            geotiff_zip_url=geotiff_zip_url,
        )

    except Exception as error:
        set_area_export_status(
            running=False,
            stage="error",
            message="Error generando exportación.",
            out_name=out_name,
            error=str(error),
        )


@router.post("/api/area/export")
def api_area_export(
    payload: AreaExportRequest,
    siris_session: Optional[str] = Cookie(default=None),
):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesión no autenticada."},
        )

    current_status = get_area_export_status()

    if current_status.get("running"):
        return JSONResponse(
            status_code=409,
            content={
                "message": "Ya hay una exportación en curso. Espera a que finalice o cancélala.",
                "outName": current_status.get("outName"),
                "stage": current_status.get("stage"),
            },
        )

    has_polygon = payload.polygon is not None and len(payload.polygon) >= 3
    has_box = all(
        value is not None
        for value in [payload.row0, payload.col0, payload.height, payload.width]
    )

    if not has_polygon and not has_box:
        return JSONResponse(
            status_code=400,
            content={"message": "Parámetros inválidos."},
        )

    if payload.dateFrom and payload.dateTo and payload.dateFrom > payload.dateTo:
        return JSONResponse(
            status_code=400,
            content={"message": "La fecha inicial no puede ser mayor que la fecha final."},
        )

    out_name = f"area_{int(time.time() * 1000)}"

    set_area_export_status(
        running=True,
        stage="queued",
        message="Exportación iniciada. Preparando procesamiento...",
        out_name=out_name,
    )

    payload_data = payload.dict()

    thread = threading.Thread(
        target=_run_area_export_background,
        kwargs={
            "payload_data": payload_data,
            "out_name": out_name,
            "has_polygon": has_polygon,
        },
        daemon=True,
    )
    thread.start()

    return JSONResponse(
        status_code=202,
        content={
            "message": "Exportación iniciada.",
            "outName": out_name,
            "statusUrl": "/api/area/geotiff-status",
        },
    )


@router.post("/api/area/cancel")
def api_area_cancel(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesión no autenticada."},
        )

    cancel_active_area_export(EXPORTS_ROOT)

    return {"message": "Exportación cancelada."}


@router.get("/api/area/geotiff-status")
def api_geotiff_status(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    if not session:
        return JSONResponse(
            status_code=401,
            content={"message": "Sesión no autenticada."},
        )

    return get_area_export_status()
