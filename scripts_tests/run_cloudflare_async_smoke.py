import argparse
import json
import sys
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests


DEFAULT_POLYGON_PASTO = [
    {"lat": 1.2050, "lng": -77.2950},
    {"lat": 1.2250, "lng": -77.2950},
    {"lat": 1.2250, "lng": -77.2750},
    {"lat": 1.2050, "lng": -77.2750},
]


def normalize_base_url(value: str) -> str:
    value = value.strip()
    if not value.endswith("/"):
        value += "/"
    return value


def absolute_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base_url, path.lstrip("/"))


def request_json(session: requests.Session, method: str, base_url: str, path: str, **kwargs) -> Dict[str, Any]:
    url = absolute_url(base_url, path)
    response = session.request(method, url, timeout=60, **kwargs)

    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:500]}

    return {
        "url": url,
        "status_code": response.status_code,
        "payload": payload,
        "headers": dict(response.headers),
    }


def verify_download(session: requests.Session, base_url: str, path: Optional[str], label: str) -> Dict[str, Any]:
    if not path:
        return {
            "label": label,
            "ok": False,
            "message": "No se recibió URL.",
        }

    url = absolute_url(base_url, path)

    try:
        response = session.get(url, stream=True, timeout=120)
        first_chunk = b""

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                first_chunk = chunk
                break

        response.close()

        return {
            "label": label,
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
            "first_bytes": len(first_chunk),
            "ok": response.status_code == 200 and len(first_chunk) > 0,
        }
    except Exception as error:
        return {
            "label": label,
            "url": url,
            "ok": False,
            "message": str(error),
        }


def validate_local_outputs(project_root: Optional[str], out_name: Optional[str]) -> Dict[str, Any]:
    result = {
        "enabled": bool(project_root and out_name),
        "ok": False,
        "checks": [],
    }

    if not project_root or not out_name:
        result["message"] = "No se proporcionó project_root u out_name."
        return result

    project_root_path = Path(project_root)
    export_dir = project_root_path / "backend" / "data" / "area_exports" / out_name

    result["export_dir"] = str(export_dir)

    def add_check(name: str, ok: bool, details: Optional[Dict[str, Any]] = None):
        result["checks"].append({
            "name": name,
            "ok": bool(ok),
            "details": details or {},
        })

    add_check("export_dir_exists", export_dir.exists() and export_dir.is_dir())

    if not export_dir.exists():
        result["message"] = "No existe la carpeta local de exportación."
        return result

    polygon_json = export_dir / "polygon.json"
    add_check("polygon_json_exists", polygon_json.exists())

    mp4_files = list(export_dir.glob("*.mp4"))
    zip_files = list(export_dir.glob("*geotiff_csv*.zip"))
    geotiff_dir = export_dir / "geotiff"

    add_check(
        "mp4_exists_and_non_empty",
        bool(mp4_files) and mp4_files[0].stat().st_size > 0,
        {"files": [str(p.name) for p in mp4_files], "size_bytes": mp4_files[0].stat().st_size if mp4_files else 0},
    )

    add_check(
        "zip_exists_and_non_empty",
        bool(zip_files) and zip_files[0].stat().st_size > 0,
        {"files": [str(p.name) for p in zip_files], "size_bytes": zip_files[0].stat().st_size if zip_files else 0},
    )

    add_check("geotiff_dir_exists", geotiff_dir.exists() and geotiff_dir.is_dir())

    if zip_files:
        zip_path = zip_files[0]
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                names = zip_ref.namelist()

            add_check(
                "zip_contains_expected_files",
                any(name.lower().endswith((".tif", ".tiff")) for name in names)
                and any(name.lower().endswith(".csv") for name in names),
                {
                    "num_files": len(names),
                    "sample": names[:20],
                    "has_tif": any(name.lower().endswith((".tif", ".tiff")) for name in names),
                    "has_csv": any(name.lower().endswith(".csv") for name in names),
                    "has_readme": any("readme" in name.lower() for name in names),
                },
            )
        except Exception as error:
            add_check("zip_can_be_opened", False, {"error": str(error)})

    tif_files = list(geotiff_dir.glob("*.tif")) + list(geotiff_dir.glob("*.tiff"))
    add_check("geotiff_files_exist", bool(tif_files), {"num_tif": len(tif_files)})

    if tif_files:
        try:
            import rasterio

            with rasterio.open(tif_files[0]) as dataset:
                add_check(
                    "first_geotiff_can_be_opened_with_rasterio",
                    True,
                    {
                        "file": tif_files[0].name,
                        "width": dataset.width,
                        "height": dataset.height,
                        "count": dataset.count,
                        "crs": str(dataset.crs),
                        "dtype": str(dataset.dtypes[0]) if dataset.dtypes else None,
                    },
                )

                add_check(
                    "first_geotiff_has_valid_dimensions",
                    dataset.width > 0 and dataset.height > 0 and dataset.count > 0,
                )
        except Exception as error:
            add_check(
                "first_geotiff_can_be_opened_with_rasterio",
                False,
                {"file": tif_files[0].name, "error": str(error)},
            )

    result["ok"] = all(check["ok"] for check in result["checks"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Cloudflare + exportación asíncrona SIRIS.")
    parser.add_argument("--base-url", required=True, help="URL base local o pública. Ej: http://127.0.0.1:3000 o https://xxx.trycloudflare.com")
    parser.add_argument("--date-from", default="2016-01-01")
    parser.add_argument("--date-to", default="2016-02-01")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--project-root", default="D:\\SIRIS")
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\cloudflare")
    parser.add_argument("--polygon-json", default="")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = evidence_dir / f"cloudflare_async_smoke_{timestamp}.json"

    if args.polygon_json:
        polygon = json.loads(Path(args.polygon_json).read_text(encoding="utf-8"))
    else:
        polygon = DEFAULT_POLYGON_PASTO

    username = f"siris_cf_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    password = "Password123"
    name = "Usuario Smoke Cloudflare"

    report: Dict[str, Any] = {
        "test_id": "SMOKE-CF-ASYNC-01",
        "base_url": base_url,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "username": username,
        "started_at": timestamp,
        "steps": [],
        "status_history": [],
        "downloads": [],
        "local_outputs": {},
        "ok": False,
    }

    session = requests.Session()

    try:
        print("===============================================")
        print("SIRIS - Smoke test Cloudflare + exportación asíncrona")
        print(f"Base URL: {base_url}")
        print(f"Fechas:   {args.date_from} a {args.date_to}")
        print(f"Evidencia JSON: {report_path}")
        print("===============================================")

        print("\n[1/8] Consultando página inicial...")
        home = session.get(base_url, timeout=60)
        report["steps"].append({
            "name": "home_load",
            "url": base_url,
            "status_code": home.status_code,
            "ok": home.status_code == 200,
        })
        print(f"HTTP {home.status_code}")

        print("\n[2/8] Registrando usuario de prueba...")
        register = request_json(
            session,
            "POST",
            base_url,
            "/api/register",
            json={"username": username, "name": name, "password": password},
        )
        report["steps"].append({"name": "register", **register, "ok": register["status_code"] in {200, 409}})
        print(f"HTTP {register['status_code']} - {register['payload']}")

        print("\n[3/8] Iniciando sesión...")
        login = request_json(
            session,
            "POST",
            base_url,
            "/api/login",
            json={"username": username, "password": password},
        )
        report["steps"].append({"name": "login", **login, "ok": login["status_code"] == 200})
        print(f"HTTP {login['status_code']} - {login['payload']}")

        if login["status_code"] != 200:
            raise RuntimeError("No se pudo iniciar sesión con el usuario de prueba.")

        print("\n[4/8] Verificando sesión autenticada...")
        session_check = request_json(session, "GET", base_url, "/api/session")
        report["steps"].append({
            "name": "session_authenticated",
            **session_check,
            "ok": session_check["status_code"] == 200 and session_check["payload"].get("authenticated") is True,
        })
        print(f"HTTP {session_check['status_code']} - {session_check['payload']}")

        print("\n[5/8] Consultando área de estudio...")
        study_area = request_json(session, "GET", base_url, "/api/study-area")
        report["steps"].append({
            "name": "study_area",
            **study_area,
            "ok": study_area["status_code"] == 200 and study_area["payload"].get("type") in {"Feature", "FeatureCollection"},
        })
        print(f"HTTP {study_area['status_code']} - GeoJSON type: {study_area['payload'].get('type')}")

        print("\n[6/8] Iniciando exportación asíncrona...")
        export_payload = {
            "polygon": polygon,
            "dateFrom": args.date_from,
            "dateTo": args.date_to,
        }
        export_start = request_json(session, "POST", base_url, "/api/area/export", json=export_payload)
        report["steps"].append({
            "name": "export_start",
            **export_start,
            "ok": export_start["status_code"] == 202,
        })
        print(f"HTTP {export_start['status_code']} - {export_start['payload']}")

        if export_start["status_code"] != 202:
            raise RuntimeError(f"La exportación no respondió HTTP 202: {export_start['payload']}")

        out_name = export_start["payload"].get("outName")
        report["out_name"] = out_name

        print("\n[7/8] Consultando progreso...")
        deadline = time.time() + args.timeout_seconds
        last_stage = None
        final_status = None

        while time.time() < deadline:
            status_response = request_json(session, "GET", base_url, "/api/area/geotiff-status")
            status_payload = status_response["payload"]
            report["status_history"].append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status_code": status_response["status_code"],
                "payload": status_payload,
            })

            stage = status_payload.get("stage")
            message = status_payload.get("message")

            if stage != last_stage:
                print(f"  - stage={stage} | message={message}")
                last_stage = stage

            if stage == "done":
                final_status = status_payload
                break

            if stage in {"error", "cancelled"}:
                raise RuntimeError(f"Exportación terminó con estado {stage}: {status_payload}")

            time.sleep(args.poll_seconds)

        if final_status is None:
            raise TimeoutError(f"La exportación no terminó antes de {args.timeout_seconds} segundos.")

        report["final_status"] = final_status

        print("\n[8/8] Verificando descargas y archivos locales...")
        video_check = verify_download(session, base_url, final_status.get("videoUrl"), "video")
        zip_check = verify_download(session, base_url, final_status.get("geotiffZipUrl"), "zip")
        report["downloads"].extend([video_check, zip_check])
        print(f"Video: {video_check}")
        print(f"ZIP:   {zip_check}")

        local_outputs = validate_local_outputs(args.project_root, final_status.get("outName"))
        report["local_outputs"] = local_outputs
        print(f"Validación local: ok={local_outputs.get('ok')}")

        step_ok = all(step.get("ok") for step in report["steps"])
        download_ok = all(item.get("ok") for item in report["downloads"])
        local_ok = local_outputs.get("ok", False)

        report["ok"] = bool(step_ok and download_ok and local_ok)
        report["finished_at"] = time.strftime("%Y%m%d_%H%M%S")

        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

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
