from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from typing import Optional, List, Dict, Any


active_area_process: Optional[subprocess.Popen] = None
active_geotiff_process: Optional[subprocess.Popen] = None
active_area_out_name: Optional[str] = None


def _date_to_yyyymmdd(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    return str(value).replace("-", "")


def _run_process(args: List[str], cwd: Path, process_type: str) -> None:
    global active_area_process
    global active_geotiff_process

    print("Ejecutando:", " ".join(args), flush=True)

    child = subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    if process_type == "area":
        active_area_process = child

    if process_type == "geotiff":
        active_geotiff_process = child

    output_lines = []

    try:
        if child.stdout:
            for line in child.stdout:
                output_lines.append(line.rstrip())
                print(line, end="", flush=True)

        return_code = child.wait()

    finally:
        if process_type == "area" and active_area_process is child:
            active_area_process = None

        if process_type == "geotiff" and active_geotiff_process is child:
            active_geotiff_process = None

    if return_code != 0:
        if return_code < 0:
            raise RuntimeError("Exportacion cancelada.")

        last_output = "\n".join(output_lines[-80:])
        raise RuntimeError(last_output or f"Proceso terminó con código {return_code}")


def run_area_export(
    *,
    row0: Optional[float],
    col0: Optional[float],
    height: Optional[float],
    width: Optional[float],
    polygon: Optional[List[Dict[str, Any]]],
    date_from: Optional[str],
    date_to: Optional[str],
    out_name: str,
    data_root: Path,
    exports_root: Path,
    web_exports_root: Path
) -> None:
    global active_area_out_name

    script_path = data_root.parent / "scripts" / "generar_area_desde_tiles.py"

    if not script_path.exists():
        raise FileNotFoundError(f"No se encontro el script: {script_path}")

    export_path = exports_root / out_name
    export_path.mkdir(parents=True, exist_ok=True)

    active_area_out_name = out_name

    args = [
        sys.executable,
        "-u",
        str(script_path),
        "--web-root", str(web_exports_root),
        "--out-name", out_name,
        "--fps", "8"
    ]

    date_from_clean = _date_to_yyyymmdd(date_from)
    date_to_clean = _date_to_yyyymmdd(date_to)

    if date_from_clean:
        args.extend(["--date-from", date_from_clean])

    if date_to_clean:
        args.extend(["--date-to", date_to_clean])

    if polygon:
        polygon_path = export_path / "polygon.json"
        polygon_path.write_text(json.dumps(polygon), encoding="utf-8")

        args.extend([
            "--polygon-file", str(polygon_path),
            "--grid-georef", str(data_root / "grid_georef.json")
        ])
    else:
        if row0 is None or col0 is None or height is None or width is None:
            raise ValueError("Para exportar por caja se requieren row0, col0, height y width.")

        args.extend([
            "--row0", str(round(row0)),
            "--col0", str(round(col0)),
            "--height", str(round(height)),
            "--width", str(round(width))
        ])

    try:
        _run_process(args, cwd=data_root, process_type="area")
    finally:
        if active_area_out_name == out_name:
            active_area_out_name = None


def run_geotiff_area_export(
    *,
    polygon: Optional[List[Dict[str, Any]]],
    date_from: Optional[str],
    date_to: Optional[str],
    out_name: str,
    data_root: Path,
    exports_root: Path,
    npy_roots: List[Path],
    mask_root: Path,
    workers: str
) -> None:
    global active_area_out_name

    if not polygon:
        raise ValueError("La exportacion GeoTIFF requiere un poligono.")

    script_path = data_root.parent / "scripts" / "generar_area_geotiff_csv_desde_npy.py"

    if not script_path.exists():
        raise FileNotFoundError(f"No se encontro el script: {script_path}")

    export_path = exports_root / out_name
    export_path.mkdir(parents=True, exist_ok=True)

    polygon_path = export_path / "polygon.json"
    polygon_path.write_text(json.dumps(polygon), encoding="utf-8")

    active_area_out_name = out_name

    args = [
        sys.executable,
        "-u",
        str(script_path),
        "--npy-roots",
        *[str(root) for root in npy_roots],
        "--mask-root", str(mask_root),
        "--polygon-file", str(polygon_path),
        "--grid-georef", str(data_root / "grid_georef.json"),
        "--out-root", str(exports_root),
        "--out-name", out_name,
        "--workers", str(workers or os.environ.get("SIRIS_GEOTIFF_WORKERS", "2"))
    ]

    date_from_clean = _date_to_yyyymmdd(date_from)
    date_to_clean = _date_to_yyyymmdd(date_to)

    if date_from_clean:
        args.extend(["--date-from", date_from_clean])

    if date_to_clean:
        args.extend(["--date-to", date_to_clean])

    try:
        _run_process(args, cwd=data_root, process_type="geotiff")
    finally:
        if active_area_out_name == out_name:
            active_area_out_name = None


def cancel_active_area_export(exports_root: Path) -> None:
    global active_area_process
    global active_geotiff_process
    global active_area_out_name

    if active_area_process and active_area_process.poll() is None:
        active_area_process.terminate()
        active_area_process = None

    if active_geotiff_process and active_geotiff_process.poll() is None:
        active_geotiff_process.terminate()
        active_geotiff_process = None

    if active_area_out_name:
        export_path = exports_root / active_area_out_name

        if export_path.exists():
            shutil.rmtree(export_path, ignore_errors=True)

        active_area_out_name = None


def get_area_export_status():
    return {
        "areaRunning": active_area_process is not None and active_area_process.poll() is None,
        "geotiffRunning": active_geotiff_process is not None and active_geotiff_process.poll() is None,
        "outName": active_area_out_name
    }
