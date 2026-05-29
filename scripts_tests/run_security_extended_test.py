import argparse
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def absolute_url(base_url: str, path: str) -> str:
    # No usar urljoin aquí porque normaliza secuencias "../" y puede convertir
    # /exports/../data/siris.db en /data/siris.db antes de enviar la solicitud.
    if not path.startswith("/"):
        path = "/" + path
    return base_url + path


def add_result(results: List[Dict[str, Any]], case_id: str, description: str, ok: bool, details: Optional[Dict[str, Any]] = None) -> None:
    results.append(
        {
            "id": case_id,
            "description": description,
            "ok": bool(ok),
            "details": details or {},
        }
    )


def request_json(session: requests.Session, method: str, base_url: str, path: str, **kwargs) -> Dict[str, Any]:
    url = absolute_url(base_url, path)
    started = time.perf_counter()

    try:
        response = session.request(method, url, timeout=60, allow_redirects=False, **kwargs)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text[:500]}

        return {
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "payload": payload,
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as error:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "payload": None,
            "elapsed_ms": elapsed_ms,
            "error": str(error),
        }


def request_raw(session: requests.Session, method: str, base_url: str, path: str, **kwargs) -> Dict[str, Any]:
    url = absolute_url(base_url, path)
    started = time.perf_counter()

    try:
        response = session.request(method, url, timeout=60, allow_redirects=False, **kwargs)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        body = response.content[:512]
        text_sample = body.decode("utf-8", errors="replace")

        return {
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type", ""),
            "content_disposition": response.headers.get("content-disposition", ""),
            "body_prefix_hex": body[:32].hex(),
            "body_sample": text_sample,
            "elapsed_ms": elapsed_ms,
            "error": None,
        }

    except Exception as error:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "content_type": "",
            "content_disposition": "",
            "body_prefix_hex": "",
            "body_sample": "",
            "elapsed_ms": elapsed_ms,
            "error": str(error),
        }


def cookie_header_has_security_flags(set_cookie_header: str) -> Dict[str, Any]:
    lower = set_cookie_header.lower()

    return {
        "set_cookie": set_cookie_header,
        "has_httponly": "httponly" in lower,
        "has_samesite": "samesite" in lower,
        "has_session_cookie": "siris_session" in lower,
        "has_secure": "secure" in lower,
    }


def inspect_db_for_plain_password(db_path: Path, username: str, raw_password: str) -> Dict[str, Any]:
    summary = {
        "db_path": str(db_path),
        "exists": db_path.exists(),
        "checked": False,
        "found_username": False,
        "plain_password_found": False,
        "matching_tables": [],
        "error": None,
    }

    if not db_path.exists():
        summary["error"] = "No existe la base de datos local."
        return summary

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        tables = [
            row[0]
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]

        for table in tables:
            try:
                columns_info = cursor.execute(f"PRAGMA table_info({table})").fetchall()
                columns = [item[1] for item in columns_info]

                if not columns:
                    continue

                select_cols = ", ".join([f'"{col}"' for col in columns])
                rows = cursor.execute(f'SELECT {select_cols} FROM "{table}"').fetchall()

                for row in rows:
                    values = {col: row[col] for col in columns}

                    if any(str(value) == username for value in values.values()):
                        summary["found_username"] = True
                        summary["matching_tables"].append(
                            {
                                "table": table,
                                "columns": columns,
                                "password_like_columns": [
                                    col for col in columns if "pass" in col.lower() or "hash" in col.lower() or "salt" in col.lower()
                                ],
                            }
                        )

                        for value in values.values():
                            if value is not None and str(value) == raw_password:
                                summary["plain_password_found"] = True

            except Exception:
                continue

        conn.close()
        summary["checked"] = True

    except Exception as error:
        summary["error"] = str(error)

    return summary


def traversal_response_is_safe(item: Dict[str, Any]) -> bool:
    status = item.get("status_code")
    content_type = (item.get("content_type") or "").lower()
    content_disposition = (item.get("content_disposition") or "").lower()
    body_sample = item.get("body_sample") or ""
    body_hex = item.get("body_prefix_hex") or ""

    # Respuestas de rechazo o no encontrado son válidas.
    if status in {400, 401, 403, 404, 405, 422}:
        return True

    # Redirect no se sigue. No debería exponer contenido sensible.
    if status in {301, 302, 303, 307, 308}:
        return True

    # Si la app SPA responde index.html con 200, no se considera exposición
    # de archivo sensible. Esto puede pasar cuando el cliente/servidor normaliza
    # la ruta fuera de /exports.
    if status == 200 and "text/html" in content_type:
        lower_body = body_sample.lower()
        looks_like_spa = "<html" in lower_body or "<!doctype html" in lower_body or "siris" in lower_body
        leaks_sqlite = "sqlite format 3" in lower_body or body_hex.startswith("53514c69746520666f726d6174203300")
        has_attachment = "attachment" in content_disposition

        return looks_like_spa and not leaks_sqlite and not has_attachment

    # Cualquier 200 que no sea HTML de la SPA sí es sospechoso.
    if status == 200:
        return False

    # Otros estados 5xx no exponen archivo, pero sí indican posible error no controlado.
    # Para esta prueba se consideran no seguros porque deberían manejarse como 403/404.
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de seguridad funcional ampliada para SIRIS.")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--project-root", default="D:\\SIRIS")
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\security")
    parser.add_argument("--skip-db-check", action="store_true")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    project_root = Path(args.project_root)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = evidence_dir / f"security_extended_{timestamp}.json"

    results: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {
        "test_id": "SEC-EXT-v0.7.1",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "project_root": str(project_root),
        "results": results,
        "ok": False,
    }

    print("===================================================")
    print("SIRIS - Seguridad funcional ampliada v0.7.1")
    print(f"Base URL:      {base_url}")
    print(f"Project root:  {project_root}")
    print(f"Evidencia:     {json_path}")
    print("===================================================")

    anonymous = requests.Session()

    unauth_export = request_json(
        anonymous,
        "POST",
        base_url,
        "/api/area/export",
        json={
            "polygon": [
                {"lat": 1.205, "lng": -77.295},
                {"lat": 1.225, "lng": -77.295},
                {"lat": 1.225, "lng": -77.275},
            ],
            "dateFrom": "2016-01-01",
            "dateTo": "2016-02-01",
        },
    )
    add_result(results, "SEC-01", "Exportación sin sesión debe ser rechazada", unauth_export["status_code"] == 401, unauth_export)

    unauth_status = request_json(anonymous, "GET", base_url, "/api/area/geotiff-status")
    add_result(results, "SEC-02", "Consulta de estado sin sesión debe ser rechazada", unauth_status["status_code"] == 401, unauth_status)

    unauth_cancel = request_json(anonymous, "POST", base_url, "/api/area/cancel")
    add_result(results, "SEC-03", "Cancelación sin sesión debe ser rechazada", unauth_cancel["status_code"] == 401, unauth_cancel)

    anonymous_session = request_json(anonymous, "GET", base_url, "/api/session")
    add_result(
        results,
        "SEC-04",
        "Sesión anónima no debe quedar autenticada",
        anonymous_session["status_code"] == 200 and anonymous_session["payload"].get("authenticated") is False,
        anonymous_session,
    )

    username = f"siris_sec_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    password = "Password123"
    name = "Usuario Seguridad"

    auth_session = requests.Session()

    register = request_json(
        auth_session,
        "POST",
        base_url,
        "/api/register",
        json={"username": username, "name": name, "password": password},
    )
    add_result(results, "SEC-05", "Registro válido de usuario de seguridad", register["status_code"] == 200, register)

    duplicate = request_json(
        requests.Session(),
        "POST",
        base_url,
        "/api/register",
        json={"username": username, "name": name, "password": password},
    )
    add_result(results, "SEC-06", "Registro duplicado debe ser rechazado", duplicate["status_code"] == 409, duplicate)

    invalid_login = request_json(
        requests.Session(),
        "POST",
        base_url,
        "/api/login",
        json={"username": username, "password": "PasswordIncorrecto123"},
    )
    add_result(results, "SEC-07", "Login con contraseña incorrecta debe ser rechazado", invalid_login["status_code"] == 401, invalid_login)

    login = request_json(
        auth_session,
        "POST",
        base_url,
        "/api/login",
        json={"username": username, "password": password},
    )
    add_result(results, "SEC-08", "Login válido debe autenticar al usuario", login["status_code"] == 200, login)

    set_cookie = login["headers"].get("set-cookie", "")
    cookie_flags = cookie_header_has_security_flags(set_cookie)
    add_result(
        results,
        "SEC-09",
        "Cookie de sesión debe incluir HttpOnly y SameSite",
        cookie_flags["has_session_cookie"] and cookie_flags["has_httponly"] and cookie_flags["has_samesite"],
        cookie_flags,
    )

    session_check = request_json(auth_session, "GET", base_url, "/api/session")
    add_result(
        results,
        "SEC-10",
        "Sesión autenticada debe devolver usuario correcto",
        session_check["status_code"] == 200
        and session_check["payload"].get("authenticated") is True
        and session_check["payload"].get("user", {}).get("username") == username,
        session_check,
    )

    export_invalid_dates = request_json(
        auth_session,
        "POST",
        base_url,
        "/api/area/export",
        json={
            "polygon": [
                {"lat": 1.205, "lng": -77.295},
                {"lat": 1.225, "lng": -77.295},
                {"lat": 1.225, "lng": -77.275},
            ],
            "dateFrom": "2026-02-01",
            "dateTo": "2016-01-01",
        },
    )
    add_result(
        results,
        "SEC-11",
        "Exportación autenticada con fechas inválidas debe ser rechazada",
        export_invalid_dates["status_code"] in {400, 422},
        export_invalid_dates,
    )

    export_invalid_polygon = request_json(
        auth_session,
        "POST",
        base_url,
        "/api/area/export",
        json={
            "polygon": [
                {"lat": 1.205, "lng": -77.295},
                {"lat": 1.225, "lng": -77.295},
            ],
            "dateFrom": "2016-01-01",
            "dateTo": "2016-02-01",
        },
    )
    add_result(
        results,
        "SEC-12",
        "Exportación autenticada con polígono menor de tres puntos debe ser rechazada",
        export_invalid_polygon["status_code"] in {400, 422},
        export_invalid_polygon,
    )

    malformed_export = request_json(
        auth_session,
        "POST",
        base_url,
        "/api/area/export",
        json={"dateFrom": "2016-01-01"},
    )
    add_result(
        results,
        "SEC-13",
        "Exportación con payload incompleto debe ser rechazada",
        malformed_export["status_code"] in {400, 422},
        malformed_export,
    )

    traversal_paths = [
        "/exports/%2E%2E/data/siris.db",
        "/exports/%2e%2e%2fdata%2fsiris.db",
        "/exports/..%2fdata%2fsiris.db",
        "/exports/%2E%2E%5Cdata%5Csiris.db",
        "/exports/%252e%252e%252fdata%252fsiris.db",
        "/exports/%2E%2E/backend/data/siris.db",
        "/exports/%2E%2E/%2E%2E/backend/data/siris.db",
    ]

    traversal_details = []
    traversal_ok = True

    for path in traversal_paths:
        item = request_raw(auth_session, "GET", base_url, path)
        item["safe_evaluation"] = traversal_response_is_safe(item)
        traversal_details.append(item)

        if not item["safe_evaluation"]:
            traversal_ok = False

    add_result(
        results,
        "SEC-14",
        "Intentos de path traversal en /exports no deben exponer archivos sensibles",
        traversal_ok,
        {"attempts": traversal_details},
    )

    missing_export = request_raw(auth_session, "GET", base_url, "/exports/area_no_existe/archivo_no_existe.zip")
    add_result(
        results,
        "SEC-15",
        "Archivo exportado inexistente debe retornar 404 o error controlado",
        missing_export["status_code"] in {403, 404},
        missing_export,
    )

    logout = request_json(auth_session, "POST", base_url, "/api/logout")
    after_logout = request_json(auth_session, "GET", base_url, "/api/session")
    add_result(
        results,
        "SEC-16",
        "Después de logout la sesión no debe seguir autenticada",
        logout["status_code"] == 200
        and after_logout["status_code"] == 200
        and after_logout["payload"].get("authenticated") is False,
        {"logout": logout, "after_logout": after_logout},
    )

    if not args.skip_db_check:
        db_path = project_root / "backend" / "data" / "siris.db"
        db_check = inspect_db_for_plain_password(db_path, username, password)
        add_result(
            results,
            "SEC-17",
            "La contraseña no debe almacenarse en texto plano en SQLite",
            db_check["checked"] and db_check["found_username"] and not db_check["plain_password_found"],
            db_check,
        )

    report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    report["summary"] = {
        "total": len(results),
        "approved": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
    }
    report["ok"] = report["summary"]["failed"] == 0

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nResumen de validaciones:")
    for item in results:
        print(f"  {item['id']} - {'APROBADO' if item['ok'] else 'FALLIDO'} - {item['description']}")

    print(f"\nTotal:     {report['summary']['total']}")
    print(f"Aprobadas: {report['summary']['approved']}")
    print(f"Fallidas:  {report['summary']['failed']}")
    print(f"Evidencia JSON: {json_path}")

    if report["ok"]:
        print("\nResultado: APROBADO.")
        return 0

    print("\nResultado: FALLIDO.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
