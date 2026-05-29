import argparse
import csv
import gzip
import io
import json
import math
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional


def add_check(report: Dict[str, Any], check_id: str, name: str, ok: bool, details: Optional[Dict[str, Any]] = None) -> None:
    report["checks"].append(
        {
            "id": check_id,
            "name": name,
            "ok": bool(ok),
            "details": details or {},
        }
    )


def newest_export_dir(exports_root: Path) -> Optional[Path]:
    if not exports_root.exists():
        return None

    dirs = [p for p in exports_root.iterdir() if p.is_dir() and p.name.startswith("area_")]

    if not dirs:
        return None

    return max(dirs, key=lambda p: p.stat().st_mtime)


def safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return 0


def load_json_file(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_valid_polygon(payload: Any) -> bool:
    if not isinstance(payload, list) or len(payload) < 3:
        return False

    for item in payload:
        if not isinstance(item, dict):
            return False

        lat = item.get("lat")
        lng = item.get("lng")

        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return False

        if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
            return False

    return True


def summarize_zip(zip_path: Path) -> Dict[str, Any]:
    summary = {
        "path": str(zip_path),
        "exists": zip_path.exists(),
        "size_bytes": safe_size(zip_path),
        "can_open": False,
        "num_entries": 0,
        "has_tif": False,
        "has_csv": False,
        "has_excel": False,
        "has_readme": False,
        "sample_entries": [],
        "bad_file": None,
        "error": None,
    }

    if not zip_path.exists():
        return summary

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            names = zip_ref.namelist()
            bad = zip_ref.testzip()

        lower_names = [name.lower() for name in names]

        summary.update(
            {
                "can_open": True,
                "num_entries": len(names),
                "has_tif": any(name.endswith((".tif", ".tiff")) for name in lower_names),
                "has_csv": any(name.endswith((".csv", ".csv.gz")) for name in lower_names),
                "has_excel": any(name.endswith((".xlsx", ".xls")) for name in lower_names),
                "has_readme": any("readme" in name for name in lower_names),
                "sample_entries": names[:25],
                "bad_file": bad,
            }
        )

    except Exception as error:
        summary["error"] = str(error)

    return summary


def summarize_csv_stream(text_handle, source_label: str, max_count: int = 10000) -> Dict[str, Any]:
    summary = {
        "source": source_label,
        "can_open": False,
        "columns": [],
        "sample_rows": [],
        "rows_counted_up_to_limit": 0,
        "reached_count_limit": False,
        "error": None,
    }

    try:
        # Intento normal con encabezado
        reader = csv.DictReader(text_handle)
        summary["columns"] = reader.fieldnames or []

        count = 0

        for row in reader:
            count += 1

            if len(summary["sample_rows"]) < 5:
                summary["sample_rows"].append({key: row.get(key) for key in summary["columns"][:12]})

            if count >= max_count:
                summary["reached_count_limit"] = True
                break

        summary["can_open"] = True
        summary["rows_counted_up_to_limit"] = count

    except Exception as error:
        summary["error"] = str(error)

    return summary


def summarize_csv_file(csv_path: Path, max_count: int = 10000) -> Dict[str, Any]:
    summary = {
        "location": "filesystem",
        "path": str(csv_path),
        "exists": csv_path.exists(),
        "size_bytes": safe_size(csv_path),
        "can_open": False,
        "columns": [],
        "sample_rows": [],
        "rows_counted_up_to_limit": 0,
        "reached_count_limit": False,
        "error": None,
    }

    if not csv_path.exists():
        return summary

    try:
        if csv_path.name.lower().endswith(".gz"):
            with gzip.open(csv_path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
                parsed = summarize_csv_stream(handle, str(csv_path), max_count=max_count)
        else:
            with open(csv_path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
                parsed = summarize_csv_stream(handle, str(csv_path), max_count=max_count)

        summary.update(parsed)

    except Exception as error:
        summary["error"] = str(error)

    return summary


def summarize_csv_inside_zip(zip_path: Path, max_count: int = 10000) -> Dict[str, Any]:
    summary = {
        "location": "zip",
        "zip_path": str(zip_path),
        "exists": zip_path.exists(),
        "member": None,
        "size_bytes": None,
        "can_open": False,
        "columns": [],
        "sample_rows": [],
        "rows_counted_up_to_limit": 0,
        "reached_count_limit": False,
        "error": None,
    }

    if not zip_path.exists():
        return summary

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            members = [
                name
                for name in zip_ref.namelist()
                if name.lower().endswith((".csv", ".csv.gz"))
            ]

            if not members:
                summary["error"] = "No se encontró archivo CSV dentro del ZIP."
                return summary

            # Preferir CSV de píxeles si existe.
            member = next((name for name in members if "pixel" in name.lower() or "pixeles" in name.lower()), members[0])
            info = zip_ref.getinfo(member)

            summary["member"] = member
            summary["size_bytes"] = info.file_size

            with zip_ref.open(member, "r") as raw:
                if member.lower().endswith(".gz"):
                    with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
                        text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace", newline="")
                        parsed = summarize_csv_stream(text, f"{zip_path.name}:{member}", max_count=max_count)
                else:
                    text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
                    parsed = summarize_csv_stream(text, f"{zip_path.name}:{member}", max_count=max_count)

            summary.update(parsed)

    except Exception as error:
        summary["error"] = str(error)

    return summary


def summarize_geotiff(tif_path: Path, read_sample: bool = True) -> Dict[str, Any]:
    summary = {
        "path": str(tif_path),
        "exists": tif_path.exists(),
        "size_bytes": safe_size(tif_path),
        "can_open": False,
        "width": None,
        "height": None,
        "count": None,
        "crs": None,
        "transform": None,
        "bounds": None,
        "dtypes": [],
        "nodata": None,
        "has_valid_dimensions": False,
        "has_valid_crs": False,
        "has_valid_transform": False,
        "sample_read_ok": False,
        "error": None,
    }

    if not tif_path.exists():
        return summary

    try:
        import rasterio
        from rasterio.windows import Window

        with rasterio.open(tif_path) as dataset:
            summary["can_open"] = True
            summary["width"] = int(dataset.width)
            summary["height"] = int(dataset.height)
            summary["count"] = int(dataset.count)
            summary["crs"] = str(dataset.crs) if dataset.crs else None
            summary["transform"] = str(dataset.transform)
            summary["bounds"] = {
                "left": float(dataset.bounds.left),
                "bottom": float(dataset.bounds.bottom),
                "right": float(dataset.bounds.right),
                "top": float(dataset.bounds.top),
            }
            summary["dtypes"] = list(dataset.dtypes)
            summary["nodata"] = dataset.nodata
            summary["has_valid_dimensions"] = dataset.width > 0 and dataset.height > 0 and dataset.count > 0
            summary["has_valid_crs"] = dataset.crs is not None

            transform_values = tuple(dataset.transform)
            summary["has_valid_transform"] = all(
                isinstance(value, (int, float)) and math.isfinite(float(value))
                for value in transform_values
            )

            if read_sample and dataset.width > 0 and dataset.height > 0 and dataset.count > 0:
                win_width = min(64, dataset.width)
                win_height = min(64, dataset.height)
                sample = dataset.read(1, window=Window(0, 0, win_width, win_height), masked=True)
                summary["sample_read_ok"] = sample.size > 0

    except Exception as error:
        summary["error"] = str(error)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validación geoespacial local de productos exportados por SIRIS.")
    parser.add_argument("--project-root", default="D:\\SIRIS")
    parser.add_argument("--out-name", default="", help="Nombre de exportación. Ej: area_178007220795. Si se omite, se usa la más reciente.")
    parser.add_argument("--exports-root", default="", help="Ruta opcional al directorio area_exports.")
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\geospatial")
    parser.add_argument("--max-geotiffs", type=int, default=5, help="Cantidad máxima de GeoTIFF a inspeccionar con rasterio.")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    exports_root = Path(args.exports_root) if args.exports_root else project_root / "backend" / "data" / "area_exports"
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = evidence_dir / f"geospatial_validation_{timestamp}.json"

    report: Dict[str, Any] = {
        "test_id": "GEO-LOCAL-VALIDATION-v0.3.1",
        "started_at": timestamp,
        "project_root": str(project_root),
        "exports_root": str(exports_root),
        "out_name_argument": args.out_name or None,
        "checks": [],
        "geotiffs": [],
        "csv": {},
        "zip": {},
        "ok": False,
    }

    print("===================================================")
    print("SIRIS - Validación geoespacial local v0.3.1")
    print(f"Proyecto:      {project_root}")
    print(f"Exports root:  {exports_root}")
    print(f"Evidencia:     {report_path}")
    print("===================================================")

    try:
        add_check(report, "GEO-00", "Directorio de exportaciones existe", exports_root.exists() and exports_root.is_dir(), {"path": str(exports_root)})

        if args.out_name:
            export_dir = exports_root / args.out_name
        else:
            export_dir = newest_export_dir(exports_root)

        if export_dir is None:
            raise RuntimeError("No se encontró ninguna exportación area_*.")

        out_name = export_dir.name
        report["out_name"] = out_name
        report["export_dir"] = str(export_dir)

        print(f"\nExportación evaluada: {out_name}")
        print(f"Ruta: {export_dir}")

        add_check(report, "GEO-01", "Directorio de exportación existe", export_dir.exists() and export_dir.is_dir(), {"path": str(export_dir)})

        polygon_path = export_dir / "polygon.json"
        polygon_payload = load_json_file(polygon_path)
        add_check(
            report,
            "GEO-02",
            "polygon.json existe y contiene al menos tres vértices válidos",
            polygon_path.exists() and is_valid_polygon(polygon_payload),
            {
                "path": str(polygon_path),
                "vertices": len(polygon_payload) if isinstance(polygon_payload, list) else None,
            },
        )

        mp4_files = sorted(export_dir.glob("*.mp4"))
        add_check(
            report,
            "GEO-03",
            "Video MP4 existe y no está vacío",
            bool(mp4_files) and safe_size(mp4_files[0]) > 0,
            {
                "files": [{"name": p.name, "size_bytes": safe_size(p)} for p in mp4_files],
            },
        )

        zip_files = sorted(export_dir.glob("*geotiff_csv*.zip"))
        zip_summary = summarize_zip(zip_files[0]) if zip_files else {"exists": False, "error": "No se encontró ZIP geotiff_csv."}
        report["zip"] = zip_summary
        add_check(
            report,
            "GEO-04",
            "ZIP GeoTIFF/CSV existe, abre correctamente y contiene TIF/CSV",
            bool(zip_files)
            and zip_summary.get("exists")
            and zip_summary.get("size_bytes", 0) > 0
            and zip_summary.get("can_open")
            and zip_summary.get("bad_file") is None
            and zip_summary.get("has_tif")
            and (zip_summary.get("has_csv") or zip_summary.get("has_excel")),
            zip_summary,
        )

        geotiff_dir = export_dir / "geotiff"
        add_check(
            report,
            "GEO-05",
            "Directorio geotiff existe",
            geotiff_dir.exists() and geotiff_dir.is_dir(),
            {"path": str(geotiff_dir)},
        )

        tif_files = sorted(list(geotiff_dir.glob("*.tif")) + list(geotiff_dir.glob("*.tiff"))) if geotiff_dir.exists() else []
        add_check(
            report,
            "GEO-06",
            "Existen archivos GeoTIFF",
            bool(tif_files),
            {"num_geotiffs": len(tif_files), "sample": [p.name for p in tif_files[:15]]},
        )

        print("\nInspeccionando GeoTIFF con rasterio...")
        for tif_path in tif_files[: args.max_geotiffs]:
            geo_summary = summarize_geotiff(tif_path)
            report["geotiffs"].append(geo_summary)
            status = "OK" if (
                geo_summary["can_open"]
                and geo_summary["has_valid_dimensions"]
                and geo_summary["has_valid_crs"]
                and geo_summary["has_valid_transform"]
                and geo_summary["sample_read_ok"]
            ) else "FALLA"
            print(f"  - {tif_path.name}: {status}")

        geotiff_checks_ok = bool(report["geotiffs"]) and all(
            item.get("can_open")
            and item.get("has_valid_dimensions")
            and item.get("has_valid_crs")
            and item.get("has_valid_transform")
            and item.get("sample_read_ok")
            for item in report["geotiffs"]
        )

        add_check(
            report,
            "GEO-07",
            "GeoTIFF inspeccionados abren con rasterio y tienen metadatos válidos",
            geotiff_checks_ok,
            {
                "num_inspected": len(report["geotiffs"]),
                "max_geotiffs": args.max_geotiffs,
            },
        )

        # CSV puede estar fuera del ZIP o únicamente empaquetado dentro del ZIP.
        csv_files = sorted(list(export_dir.rglob("*.csv")) + list(export_dir.rglob("*.csv.gz")))
        csv_summary = {}

        if csv_files:
            csv_summary = summarize_csv_file(csv_files[0])
        elif zip_files:
            csv_summary = summarize_csv_inside_zip(zip_files[0])
        else:
            csv_summary = {"exists": False, "error": "No se encontró CSV fuera ni dentro de ZIP."}

        report["csv"] = csv_summary

        columns = csv_summary.get("columns") or []
        rows_counted = csv_summary.get("rows_counted_up_to_limit", 0)
        csv_has_data_structure = bool(columns) or rows_counted > 0
        csv_has_content = csv_summary.get("size_bytes") is None or csv_summary.get("size_bytes", 1) > 0

        add_check(
            report,
            "GEO-08",
            "CSV existe dentro o fuera del ZIP, abre correctamente y tiene estructura tabular",
            bool(csv_summary)
            and csv_summary.get("can_open")
            and csv_has_data_structure
            and csv_has_content,
            csv_summary,
        )

        all_checks_ok = all(check["ok"] for check in report["checks"])
        report["ok"] = bool(all_checks_ok)
        report["finished_at"] = time.strftime("%Y%m%d_%H%M%S")

        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\nResumen de validaciones:")
        for check in report["checks"]:
            print(f"  {check['id']} - {'APROBADO' if check['ok'] else 'FALLIDO'} - {check['name']}")

        if report["ok"]:
            print("\nResultado: APROBADO.")
            print(f"Evidencia JSON: {report_path}")
            return 0

        print("\nResultado: FALLIDO.")
        print(f"Evidencia JSON: {report_path}")
        return 1

    except Exception as error:
        report["ok"] = False
        report["error"] = str(error)
        report["finished_at"] = time.strftime("%Y%m%d_%H%M%S")
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\nResultado: FALLIDO.")
        print(f"Error: {error}")
        print(f"Evidencia JSON: {report_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
