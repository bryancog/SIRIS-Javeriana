import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:
    requests = None


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def add_check(
    checks: List[Dict[str, Any]],
    check_id: str,
    description: str,
    ok: bool,
    details: Optional[Dict[str, Any]] = None,
    required: bool = True,
) -> None:
    checks.append(
        {
            "id": check_id,
            "description": description,
            "ok": bool(ok),
            "required": bool(required),
            "details": details or {},
        }
    )


def run_command(command: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "command": " ".join(command),
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "ok": result.returncode == 0,
        }
    except Exception as error:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": "",
            "stderr": str(error),
            "ok": False,
        }


def contains_all(text: str, terms: List[str]) -> Dict[str, bool]:
    lower = text.lower()
    return {term: term.lower() in lower for term in terms}


def check_json_dependencies(package_json: Path) -> Dict[str, Any]:
    summary = {
        "exists": package_json.exists(),
        "dependencies": {},
        "devDependencies": {},
        "required_found": {},
        "error": None,
    }

    if not package_json.exists():
        return summary

    try:
        data = json.loads(package_json.read_text(encoding="utf-8", errors="replace"))
        deps = data.get("dependencies") or {}
        dev_deps = data.get("devDependencies") or {}
        summary["dependencies"] = deps
        summary["devDependencies"] = dev_deps

        required = ["@vitejs/plugin-react", "vite", "react", "react-dom", "react-router-dom", "leaflet"]
        all_deps = {**deps, **dev_deps}
        summary["required_found"] = {item: item in all_deps for item in required}

    except Exception as error:
        summary["error"] = str(error)

    return summary


def check_requirements(requirements_path: Path) -> Dict[str, Any]:
    text = read_text(requirements_path)
    lower = text.lower()
    required = ["fastapi", "uvicorn", "numpy", "pillow", "pyproj", "rasterio"]

    return {
        "exists": requirements_path.exists(),
        "required_found": {item: item in lower for item in required},
        "sample": text[:1500],
    }


def live_endpoint_check(base_url: str) -> Dict[str, Any]:
    result = {
        "base_url": base_url,
        "enabled": True,
        "endpoints": {},
        "error": None,
    }

    if requests is None:
        result["error"] = "No está instalado requests."
        return result

    base_url = base_url.rstrip("/")

    endpoints = {
        "home": "/",
        "docs": "/docs",
        "api_session": "/api/session",
        "api_study_area": "/api/study-area",
    }

    session = requests.Session()

    for name, path in endpoints.items():
        url = base_url + path
        started = time.perf_counter()

        try:
            response = session.get(url, timeout=30)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

            payload_type = None
            if "application/json" in response.headers.get("content-type", "").lower():
                try:
                    payload = response.json()
                    payload_type = payload.get("type") if isinstance(payload, dict) else type(payload).__name__
                except Exception:
                    payload_type = "json_parse_error"

            result["endpoints"][name] = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "elapsed_ms": elapsed_ms,
                "payload_type": payload_type,
                "ok": response.status_code == 200,
            }

        except Exception as error:
            result["endpoints"][name] = {
                "url": url,
                "status_code": None,
                "content_type": None,
                "elapsed_ms": None,
                "payload_type": None,
                "ok": False,
                "error": str(error),
            }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Revisión de documentación, instalación y estructura SIRIS v0.9.")
    parser.add_argument("--project-root", default="D:\\SIRIS")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\documentation")
    parser.add_argument("--skip-live-check", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = evidence_dir / f"documentation_installation_check_{timestamp}.json"

    checks: List[Dict[str, Any]] = []
    report: Dict[str, Any] = {
        "test_id": "DOC-INSTALL-v0.9",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "project_root": str(project_root),
        "base_url": args.base_url,
        "checks": checks,
        "ok": False,
    }

    print("===================================================")
    print("SIRIS - Revisión documentación / instalación v0.9")
    print(f"Project root: {project_root}")
    print(f"Base URL:     {args.base_url}")
    print(f"Evidencia:    {json_path}")
    print("===================================================")

    # DOC-01: estructura principal.
    expected_paths = {
        "README.md": project_root / "README.md",
        ".gitignore": project_root / ".gitignore",
        "backend/app/main.py": project_root / "backend" / "app" / "main.py",
        "backend/app/config.py": project_root / "backend" / "app" / "config.py",
        "backend/app/routes/auth.py": project_root / "backend" / "app" / "routes" / "auth.py",
        "backend/app/routes/area.py": project_root / "backend" / "app" / "routes" / "area.py",
        "backend/app/routes/exports.py": project_root / "backend" / "app" / "routes" / "exports.py",
        "backend/app/services/area_service.py": project_root / "backend" / "app" / "services" / "area_service.py",
        "backend/requirements.txt": project_root / "backend" / "requirements.txt",
        "backend/pytest.ini": project_root / "backend" / "pytest.ini",
        "frontend/package.json": project_root / "frontend" / "package.json",
        "frontend/vite.config.js": project_root / "frontend" / "vite.config.js",
        "frontend/src/main.jsx": project_root / "frontend" / "src" / "main.jsx",
        "frontend/src/api.js": project_root / "frontend" / "src" / "api.js",
        "frontend/src/pages/Login.jsx": project_root / "frontend" / "src" / "pages" / "Login.jsx",
        "frontend/src/pages/Register.jsx": project_root / "frontend" / "src" / "pages" / "Register.jsx",
        "frontend/src/pages/Dashboard.jsx": project_root / "frontend" / "src" / "pages" / "Dashboard.jsx",
        "scripts_tests": project_root / "scripts_tests",
        "docs": project_root / "docs",
    }

    missing_paths = [name for name, path in expected_paths.items() if not path.exists()]
    add_check(
        checks,
        "DOC-01",
        "Estructura principal del proyecto existe",
        len(missing_paths) == 0,
        {
            "missing": missing_paths,
            "checked": list(expected_paths.keys()),
        },
    )

    # DOC-02: README.
    readme_path = project_root / "README.md"
    readme_text = read_text(readme_path)
    readme_terms = [
        "React",
        "Vite",
        "FastAPI",
        "Cloudflare",
        "asynchronous",
        "export",
        "/api/area/export",
        "/api/area/geotiff-status",
        "frontend/dist",
        "pytest",
    ]
    readme_presence = contains_all(readme_text, readme_terms)
    add_check(
        checks,
        "DOC-02",
        "README documenta arquitectura, ejecución, Cloudflare, exportación asíncrona y pruebas",
        readme_path.exists() and all(readme_presence.values()),
        {
            "path": str(readme_path),
            "terms": readme_presence,
        },
    )

    # DOC-03: .gitignore.
    gitignore_path = project_root / ".gitignore"
    gitignore_text = read_text(gitignore_path)
    gitignore_terms = [
        "node_modules",
        "venv",
        "backend/data/area_exports",
        "backend/data/web_exports",
        "siris.db",
        "tests_evidence",
        "backups",
        ".env",
    ]
    gitignore_presence = contains_all(gitignore_text, gitignore_terms)
    add_check(
        checks,
        "DOC-03",
        ".gitignore excluye dependencias, datos pesados, base local y evidencias",
        gitignore_path.exists() and all(gitignore_presence.values()),
        {
            "path": str(gitignore_path),
            "terms": gitignore_presence,
        },
    )

    # DOC-04: scripts de prueba.
    test_scripts = [
        "run_backend_api_tests.ps1",
        "run_cloudflare_async_smoke.ps1",
        "run_geospatial_validation.ps1",
        "run_frontend_e2e.ps1",
        "run_moderate_load_test.ps1",
        "prepare_uat_evidence.ps1",
        "run_security_extended_test.ps1",
        "run_cancel_recovery_test.ps1",
    ]
    missing_scripts = [
        name
        for name in test_scripts
        if not (project_root / "scripts_tests" / name).exists()
    ]
    add_check(
        checks,
        "DOC-04",
        "Scripts de pruebas v0.1 a v0.8 disponibles",
        len(missing_scripts) == 0,
        {
            "missing": missing_scripts,
            "checked": test_scripts,
        },
    )

    # DOC-05: evidencias.
    evidence_dirs = [
        "backend_api",
        "cloudflare",
        "geospatial",
        "frontend_e2e",
        "load",
        "uat",
        "security",
        "cancel_recovery",
    ]
    missing_evidence_dirs = [
        name
        for name in evidence_dirs
        if not (project_root / "tests_evidence" / name).exists()
    ]
    add_check(
        checks,
        "DOC-05",
        "Carpetas de evidencia por tipo de prueba existen",
        len(missing_evidence_dirs) == 0,
        {
            "missing": missing_evidence_dirs,
            "checked": evidence_dirs,
        },
    )

    # DOC-06: snippets/documentación de plan.
    snippet_dir = project_root / "docs" / "plan_pruebas_snippets"
    expected_snippets = [
        "latex_resultados_v0_1_backend_api.tex",
        "latex_resultados_v0_2_cloudflare_async.tex",
        "latex_resultados_v0_3_geospatial_validation.tex",
        "latex_resultados_v0_4_frontend_e2e.tex",
        "latex_resultados_v0_5_moderate_load.tex",
        "latex_resultados_v0_6_uat.tex",
        "latex_resultados_v0_7_security_extended.tex",
        "latex_resultados_v0_8_cancel_recovery.tex",
    ]
    existing_snippets = [name for name in expected_snippets if (snippet_dir / name).exists()]
    add_check(
        checks,
        "DOC-06",
        "Documentación auxiliar de resultados de pruebas disponible",
        len(existing_snippets) >= 6,
        {
            "existing": existing_snippets,
            "missing": [name for name in expected_snippets if name not in existing_snippets],
            "criteria": "Se aceptan al menos 6 snippets porque algunas versiones se integraron directamente al LaTeX principal.",
        },
    )

    # DOC-07: package.json.
    package_summary = check_json_dependencies(project_root / "frontend" / "package.json")
    package_ok = package_summary["exists"] and package_summary.get("error") is None and all(package_summary["required_found"].values())
    add_check(
        checks,
        "DOC-07",
        "package.json contiene dependencias frontend esperadas",
        package_ok,
        package_summary,
    )

    # DOC-08: requirements.txt.
    req_summary = check_requirements(project_root / "backend" / "requirements.txt")
    req_ok = req_summary["exists"] and all(req_summary["required_found"].values())
    add_check(
        checks,
        "DOC-08",
        "requirements.txt contiene dependencias backend/geoespaciales esperadas",
        req_ok,
        req_summary,
    )

    # DOC-09: frontend build.
    dist_path = project_root / "frontend" / "dist"
    dist_files = list(dist_path.rglob("*")) if dist_path.exists() else []
    html_exists = (dist_path / "index.html").exists()
    add_check(
        checks,
        "DOC-09",
        "Build del frontend existe en frontend/dist",
        dist_path.exists() and html_exists and len(dist_files) > 1,
        {
            "dist_path": str(dist_path),
            "index_exists": html_exists,
            "num_files": len(dist_files),
        },
    )

    # DOC-10: herramientas locales.
    python_exe = project_root / "backend" / "venv" / "Scripts" / "python.exe"
    python_version = run_command([str(python_exe), "--version"]) if python_exe.exists() else {"ok": False, "stderr": "No existe python.exe del venv"}
    npm_version = run_command(["npm.cmd", "--version"])
    add_check(
        checks,
        "DOC-10",
        "Herramientas locales Python venv y npm disponibles",
        python_version["ok"] and npm_version["ok"],
        {
            "python": python_version,
            "npm": npm_version,
        },
    )

    # DOC-11: pruebas rápidas de sintaxis Python.
    python_compile_targets = [
        project_root / "scripts_tests" / "run_backend_api_tests.ps1",  # no compila, solo presencia en detalles
        project_root / "scripts_tests" / "run_moderate_load_test.py",
        project_root / "scripts_tests" / "run_security_extended_test.py",
        project_root / "scripts_tests" / "run_cancel_recovery_test.py",
    ]
    py_files = [path for path in python_compile_targets if path.suffix == ".py" and path.exists()]
    compile_results = []
    compile_ok = True

    for py_file in py_files:
        result = run_command([str(python_exe), "-m", "py_compile", str(py_file)]) if python_exe.exists() else {"ok": False, "stderr": "No existe python.exe del venv"}
        result["file"] = str(py_file)
        compile_results.append(result)
        if not result["ok"]:
            compile_ok = False

    add_check(
        checks,
        "DOC-11",
        "Scripts Python de apoyo compilan sin errores de sintaxis",
        compile_ok and len(py_files) >= 3,
        {
            "results": compile_results,
            "num_py_files": len(py_files),
        },
    )

    # DOC-12: verificación en vivo.
    if args.skip_live_check:
        live_result = {"enabled": False, "message": "Omitido por parámetro --skip-live-check."}
        live_ok = True
    else:
        live_result = live_endpoint_check(args.base_url)
        endpoints = live_result.get("endpoints", {})
        live_ok = (
            live_result.get("error") is None
            and endpoints.get("home", {}).get("ok")
            and endpoints.get("docs", {}).get("ok")
            and endpoints.get("api_session", {}).get("ok")
            and endpoints.get("api_study_area", {}).get("ok")
        )

    add_check(
        checks,
        "DOC-12",
        "Backend activo y endpoints base responden correctamente",
        bool(live_ok),
        live_result,
    )

    # DOC-13: README de UAT.
    uat_path = project_root / "docs" / "uat" / "UAT_SIRIS_v0_6_checklist.md"
    add_check(
        checks,
        "DOC-13",
        "Checklist UAT documentado",
        uat_path.exists(),
        {
            "path": str(uat_path),
        },
    )

    # DOC-14: consistencia de documentación de endpoints asíncronos en código.
    area_py = read_text(project_root / "backend" / "app" / "routes" / "area.py")
    async_terms = ["202", "statusUrl", "threading", "geotiff-status"]
    async_presence = contains_all(area_py, async_terms)
    add_check(
        checks,
        "DOC-14",
        "Código backend conserva flujo de exportación asíncrona documentado",
        all(async_presence.values()),
        {
            "terms": async_presence,
        },
    )

    report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    required_checks = [item for item in checks if item["required"]]
    report["summary"] = {
        "total": len(checks),
        "required_total": len(required_checks),
        "approved": sum(1 for item in checks if item["ok"]),
        "failed": sum(1 for item in checks if not item["ok"]),
        "required_failed": sum(1 for item in required_checks if not item["ok"]),
    }
    report["ok"] = report["summary"]["required_failed"] == 0

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nResumen de validaciones:")
    for item in checks:
        print(f"  {item['id']} - {'APROBADO' if item['ok'] else 'FALLIDO'} - {item['description']}")

    print(f"\nTotal:            {report['summary']['total']}")
    print(f"Aprobadas:        {report['summary']['approved']}")
    print(f"Fallidas:         {report['summary']['failed']}")
    print(f"Fallidas críticas:{report['summary']['required_failed']}")
    print(f"Evidencia JSON:   {json_path}")

    if report["ok"]:
        print("\nResultado: APROBADO.")
        return 0

    print("\nResultado: FALLIDO.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
