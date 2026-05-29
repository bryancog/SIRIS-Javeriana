import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
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
    started = time.perf_counter()

    try:
        response = session.request(method, url, timeout=90, **kwargs)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text[:500]}

        return {
            "url": url,
            "status_code": response.status_code,
            "payload": payload,
            "headers": dict(response.headers),
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as error:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "url": url,
            "status_code": None,
            "payload": None,
            "headers": {},
            "elapsed_ms": elapsed_ms,
            "error": str(error),
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


def wait_for_stage(
    session: requests.Session,
    base_url: str,
    accepted_stages: List[str],
    timeout_seconds: int,
    poll_seconds: int,
    history: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    last_stage = None

    while time.time() < deadline:
        status_response = request_json(session, "GET", base_url, "/api/area/geotiff-status")
        payload = status_response.get("payload") or {}
        stage = payload.get("stage")
        message = payload.get("message")

        history.append(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status_code": status_response.get("status_code"),
                "payload": payload,
            }
        )

        if stage != last_stage:
            print(f"  - stage={stage} | message={message}")
            last_stage = stage

        if stage in accepted_stages:
            return payload

        time.sleep(poll_seconds)

    return None


def export_dir(project_root: str, out_name: Optional[str]) -> Optional[Path]:
    if not project_root or not out_name:
        return None
    return Path(project_root) / "backend" / "data" / "area_exports" / out_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de cancelación y recuperación de exportación asíncrona SIRIS.")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--project-root", default="D:\\SIRIS")
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\cancel_recovery")
    parser.add_argument("--cancel-date-from", default="2016-01-01")
    parser.add_argument("--cancel-date-to", default="2026-05-01")
    parser.add_argument("--recovery-date-from", default="2016-01-01")
    parser.add_argument("--recovery-date-to", default="2016-02-01")
    parser.add_argument("--cancel-delay-seconds", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    project_root = Path(args.project_root)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = evidence_dir / f"cancel_recovery_{timestamp}.json"

    report: Dict[str, Any] = {
        "test_id": "CANCEL-RECOVERY-v0.8",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "project_root": str(project_root),
        "cancel_range": {
            "date_from": args.cancel_date_from,
            "date_to": args.cancel_date_to,
        },
        "recovery_range": {
            "date_from": args.recovery_date_from,
            "date_to": args.recovery_date_to,
        },
        "steps": [],
        "cancel_status_history": [],
        "recovery_status_history": [],
        "downloads": [],
        "checks": [],
        "ok": False,
    }

    def add_check(check_id: str, description: str, ok: bool, details: Optional[Dict[str, Any]] = None):
        report["checks"].append(
            {
                "id": check_id,
                "description": description,
                "ok": bool(ok),
                "details": details or {},
            }
        )

    print("===================================================")
    print("SIRIS - Cancelación y recuperación v0.8")
    print(f"Base URL:      {base_url}")
    print(f"Project root:  {project_root}")
    print(f"Evidencia:     {json_path}")
    print("===================================================")

    session = requests.Session()

    try:
        username = f"siris_cancel_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        password = "Password123"
        name = "Usuario Cancel Recovery"

        print("\n[1/9] Registro de usuario de prueba...")
        register = request_json(
            session,
            "POST",
            base_url,
            "/api/register",
            json={"username": username, "name": name, "password": password},
        )
        report["steps"].append({"name": "register", **register})
        add_check("CAN-01", "Registro de usuario de prueba", register["status_code"] == 200, register)
        print(f"HTTP {register['status_code']} - {register['payload']}")

        print("\n[2/9] Login...")
        login = request_json(
            session,
            "POST",
            base_url,
            "/api/login",
            json={"username": username, "password": password},
        )
        report["steps"].append({"name": "login", **login})
        add_check("CAN-02", "Login de usuario de prueba", login["status_code"] == 200, login)
        print(f"HTTP {login['status_code']} - {login['payload']}")

        if login["status_code"] != 200:
            raise RuntimeError("No se pudo iniciar sesión.")

        # Limpiar cualquier exportación activa previa.
        print("\n[3/9] Cancelación preventiva de exportación activa previa...")
        pre_cancel = request_json(session, "POST", base_url, "/api/area/cancel")
        report["steps"].append({"name": "pre_cancel", **pre_cancel})
        print(f"HTTP {pre_cancel['status_code']} - {pre_cancel['payload']}")
        time.sleep(1)

        print("\n[4/9] Iniciando exportación larga para cancelación...")
        long_export = request_json(
            session,
            "POST",
            base_url,
            "/api/area/export",
            json={
                "polygon": DEFAULT_POLYGON_PASTO,
                "dateFrom": args.cancel_date_from,
                "dateTo": args.cancel_date_to,
            },
        )
        report["steps"].append({"name": "long_export_start", **long_export})
        add_check(
            "CAN-03",
            "Exportación larga inicia con HTTP 202",
            long_export["status_code"] == 202,
            long_export,
        )
        print(f"HTTP {long_export['status_code']} - {long_export['payload']}")

        if long_export["status_code"] != 202:
            raise RuntimeError(f"No se pudo iniciar exportación larga: {long_export['payload']}")

        cancel_out_name = long_export["payload"].get("outName")
        report["cancel_out_name"] = cancel_out_name

        print(f"\n[5/9] Esperando {args.cancel_delay_seconds} segundos antes de cancelar...")
        time.sleep(args.cancel_delay_seconds)

        print("\nEstado antes de cancelar:")
        before_cancel_status = request_json(session, "GET", base_url, "/api/area/geotiff-status")
        report["steps"].append({"name": "before_cancel_status", **before_cancel_status})
        print(f"HTTP {before_cancel_status['status_code']} - {before_cancel_status['payload']}")

        print("\n[6/9] Cancelando exportación activa...")
        cancel_response = request_json(session, "POST", base_url, "/api/area/cancel")
        report["steps"].append({"name": "cancel_response", **cancel_response})
        add_check(
            "CAN-04",
            "Endpoint de cancelación responde correctamente",
            cancel_response["status_code"] == 200,
            cancel_response,
        )
        print(f"HTTP {cancel_response['status_code']} - {cancel_response['payload']}")

        print("\nVerificando estado cancelado...")
        cancelled_status = wait_for_stage(
            session=session,
            base_url=base_url,
            accepted_stages=["cancelled"],
            timeout_seconds=30,
            poll_seconds=2,
            history=report["cancel_status_history"],
        )

        add_check(
            "CAN-05",
            "Estado de exportación queda en cancelled",
            cancelled_status is not None and cancelled_status.get("stage") == "cancelled",
            {"final_cancel_status": cancelled_status},
        )

        cancel_dir = export_dir(str(project_root), cancel_out_name)
        cancel_dir_exists = cancel_dir.exists() if cancel_dir else None

        add_check(
            "CAN-06",
            "Directorio de exportación cancelada no queda disponible como producto final",
            cancel_dir is not None and not cancel_dir_exists,
            {
                "cancel_out_name": cancel_out_name,
                "cancel_dir": str(cancel_dir) if cancel_dir else None,
                "exists": cancel_dir_exists,
            },
        )

        print("\n[7/9] Iniciando nueva exportación de recuperación...")
        recovery_export = request_json(
            session,
            "POST",
            base_url,
            "/api/area/export",
            json={
                "polygon": DEFAULT_POLYGON_PASTO,
                "dateFrom": args.recovery_date_from,
                "dateTo": args.recovery_date_to,
            },
        )
        report["steps"].append({"name": "recovery_export_start", **recovery_export})
        add_check(
            "CAN-07",
            "Después de cancelar, el sistema permite iniciar una nueva exportación",
            recovery_export["status_code"] == 202,
            recovery_export,
        )
        print(f"HTTP {recovery_export['status_code']} - {recovery_export['payload']}")

        if recovery_export["status_code"] != 202:
            raise RuntimeError(f"No se pudo iniciar exportación de recuperación: {recovery_export['payload']}")

        recovery_out_name = recovery_export["payload"].get("outName")
        report["recovery_out_name"] = recovery_out_name

        print("\n[8/9] Esperando finalización de exportación de recuperación...")
        recovery_done = wait_for_stage(
            session=session,
            base_url=base_url,
            accepted_stages=["done", "error"],
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
            history=report["recovery_status_history"],
        )

        add_check(
            "CAN-08",
            "Exportación de recuperación finaliza con stage done",
            recovery_done is not None and recovery_done.get("stage") == "done",
            {"final_recovery_status": recovery_done},
        )

        if recovery_done is None or recovery_done.get("stage") != "done":
            raise RuntimeError(f"La exportación de recuperación no finalizó correctamente: {recovery_done}")

        print("\n[9/9] Verificando video y ZIP de recuperación...")
        video_check = verify_download(session, base_url, recovery_done.get("videoUrl"), "video")
        zip_check = verify_download(session, base_url, recovery_done.get("geotiffZipUrl"), "zip")
        report["downloads"].extend([video_check, zip_check])

        add_check("CAN-09", "Video de recuperación descargable", video_check.get("ok"), video_check)
        add_check("CAN-10", "ZIP GeoTIFF/CSV de recuperación descargable", zip_check.get("ok"), zip_check)

        recovery_dir = export_dir(str(project_root), recovery_out_name)
        recovery_dir_exists = recovery_dir.exists() if recovery_dir else None
        add_check(
            "CAN-11",
            "Directorio local de exportación de recuperación existe",
            recovery_dir is not None and recovery_dir_exists,
            {
                "recovery_out_name": recovery_out_name,
                "recovery_dir": str(recovery_dir) if recovery_dir else None,
                "exists": recovery_dir_exists,
            },
        )

        report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report["summary"] = {
            "total": len(report["checks"]),
            "approved": sum(1 for item in report["checks"] if item["ok"]),
            "failed": sum(1 for item in report["checks"] if not item["ok"]),
        }
        report["ok"] = report["summary"]["failed"] == 0
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\nResumen de validaciones:")
        for check in report["checks"]:
            print(f"  {check['id']} - {'APROBADO' if check['ok'] else 'FALLIDO'} - {check['description']}")

        print(f"\nTotal:     {report['summary']['total']}")
        print(f"Aprobadas: {report['summary']['approved']}")
        print(f"Fallidas:  {report['summary']['failed']}")
        print(f"Evidencia JSON: {json_path}")

        if report["ok"]:
            print("\nResultado: APROBADO.")
            return 0

        print("\nResultado: FALLIDO.")
        return 1

    except Exception as error:
        report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report["error"] = str(error)
        report["summary"] = {
            "total": len(report["checks"]),
            "approved": sum(1 for item in report["checks"] if item["ok"]),
            "failed": sum(1 for item in report["checks"] if not item["ok"]),
        }
        report["ok"] = False
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\nResultado: FALLIDO.")
        print(f"Error: {error}")
        print(f"Evidencia JSON: {json_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
