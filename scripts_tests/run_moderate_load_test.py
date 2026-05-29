import argparse
import csv
import json
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests


def normalize_base_url(value: str) -> str:
    value = value.strip()
    if not value.endswith("/"):
        value += "/"
    return value


def absolute_url(base_url: str, path: str) -> str:
    return urljoin(base_url, path.lstrip("/"))


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0

    values_sorted = sorted(values)

    if len(values_sorted) == 1:
        return values_sorted[0]

    k = (len(values_sorted) - 1) * (p / 100)
    lower = int(k)
    upper = min(lower + 1, len(values_sorted) - 1)
    weight = k - lower

    return values_sorted[lower] * (1 - weight) + values_sorted[upper] * weight


def timed_request(
    session: requests.Session,
    method: str,
    base_url: str,
    path: str,
    expected_statuses: List[int],
    **kwargs,
) -> Dict[str, Any]:
    url = absolute_url(base_url, path)
    started = time.perf_counter()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    status_code = None
    error = None
    ok = False
    response_bytes = 0

    try:
        response = session.request(method, url, timeout=60, **kwargs)
        status_code = response.status_code
        response_bytes = len(response.content or b"")
        ok = status_code in expected_statuses
    except Exception as exc:
        error = str(exc)

    elapsed_ms = (time.perf_counter() - started) * 1000

    return {
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "status_code": status_code,
        "ok": ok,
        "latency_ms": round(elapsed_ms, 2),
        "bytes": response_bytes,
        "error": error,
    }


def create_authenticated_session(base_url: str, worker_id: int) -> Dict[str, Any]:
    session = requests.Session()
    username = f"siris_load_{int(time.time())}_{worker_id}_{uuid.uuid4().hex[:6]}"
    password = "Password123"
    name = f"Usuario Load {worker_id}"

    register = timed_request(
        session,
        "POST",
        base_url,
        "/api/register",
        [200, 409],
        json={"username": username, "name": name, "password": password},
    )

    login = timed_request(
        session,
        "POST",
        base_url,
        "/api/login",
        [200],
        json={"username": username, "password": password},
    )

    return {
        "session": session,
        "username": username,
        "register": register,
        "login": login,
        "ready": login["ok"],
    }


def worker_run(base_url: str, worker_id: int, requests_per_user: int, think_time_ms: int) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []

    auth = create_authenticated_session(base_url, worker_id)

    register_record = {"worker": worker_id, "endpoint_group": "setup", **auth["register"]}
    login_record = {"worker": worker_id, "endpoint_group": "setup", **auth["login"]}

    output.append(register_record)
    output.append(login_record)

    if not auth["ready"]:
        return output

    session = auth["session"]

    endpoint_cycle = [
        ("GET", "/", [200], "home"),
        ("GET", "/api/session", [200], "session"),
        ("GET", "/api/study-area", [200], "study_area"),
        ("GET", "/api/area/geotiff-status", [200], "export_status"),
    ]

    for index in range(requests_per_user):
        method, path, expected, group = endpoint_cycle[index % len(endpoint_cycle)]

        record = timed_request(session, method, base_url, path, expected)
        record["worker"] = worker_id
        record["endpoint_group"] = group
        output.append(record)

        if think_time_ms > 0:
            time.sleep(think_time_ms / 1000)

    return output


def summarize(records: List[Dict[str, Any]], started_at_perf: float, finished_at_perf: float) -> Dict[str, Any]:
    request_records = [item for item in records if item.get("endpoint_group") != "setup"]
    setup_records = [item for item in records if item.get("endpoint_group") == "setup"]

    latencies = [float(item["latency_ms"]) for item in request_records if item.get("latency_ms") is not None]
    total = len(request_records)
    ok = sum(1 for item in request_records if item.get("ok"))
    failed = total - ok
    duration_seconds = max(finished_at_perf - started_at_perf, 0.001)

    status_counts: Dict[str, int] = {}
    endpoint_counts: Dict[str, Dict[str, Any]] = {}

    for item in request_records:
        code = str(item.get("status_code"))
        status_counts[code] = status_counts.get(code, 0) + 1

        group = item.get("endpoint_group") or item.get("path")
        if group not in endpoint_counts:
            endpoint_counts[group] = {"total": 0, "ok": 0, "failed": 0, "latencies_ms": []}

        endpoint_counts[group]["total"] += 1
        endpoint_counts[group]["ok"] += 1 if item.get("ok") else 0
        endpoint_counts[group]["failed"] += 0 if item.get("ok") else 1
        endpoint_counts[group]["latencies_ms"].append(item.get("latency_ms") or 0)

    for group, data in endpoint_counts.items():
        values = [float(value) for value in data.pop("latencies_ms")]
        data["mean_ms"] = round(statistics.mean(values), 2) if values else 0
        data["p95_ms"] = round(percentile(values, 95), 2) if values else 0

    return {
        "total_business_requests": total,
        "successful_business_requests": ok,
        "failed_business_requests": failed,
        "success_rate": round(ok / total, 4) if total else 0,
        "duration_seconds": round(duration_seconds, 2),
        "requests_per_second": round(total / duration_seconds, 2),
        "setup_requests": len(setup_records),
        "setup_successful": sum(1 for item in setup_records if item.get("ok")),
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0,
            "mean": round(statistics.mean(latencies), 2) if latencies else 0,
            "median": round(statistics.median(latencies), 2) if latencies else 0,
            "p90": round(percentile(latencies, 90), 2) if latencies else 0,
            "p95": round(percentile(latencies, 95), 2) if latencies else 0,
            "p99": round(percentile(latencies, 99), 2) if latencies else 0,
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "status_counts": status_counts,
        "endpoint_summary": endpoint_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de carga moderada SIRIS.")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--requests-per-user", type=int, default=20)
    parser.add_argument("--think-time-ms", type=int, default=100)
    parser.add_argument("--evidence-dir", default="D:\\SIRIS\\tests_evidence\\load")
    parser.add_argument("--min-success-rate", type=float, default=0.95)
    parser.add_argument("--max-p95-ms", type=float, default=2000)
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = evidence_dir / f"moderate_load_{timestamp}.json"
    csv_path = evidence_dir / f"moderate_load_{timestamp}.csv"

    print("===================================================")
    print("SIRIS - Prueba de carga moderada v0.5")
    print(f"Base URL:             {base_url}")
    print(f"Usuarios concurrentes: {args.users}")
    print(f"Solicitudes/usuario:   {args.requests_per_user}")
    print(f"Think time:            {args.think_time_ms} ms")
    print(f"Evidencia JSON:        {json_path}")
    print(f"Evidencia CSV:         {csv_path}")
    print("===================================================")

    all_records: List[Dict[str, Any]] = []

    started_at_perf = time.perf_counter()
    started_at = time.strftime("%Y-%m-%d %H:%M:%S")

    with ThreadPoolExecutor(max_workers=args.users) as executor:
        futures = [
            executor.submit(worker_run, base_url, worker_id, args.requests_per_user, args.think_time_ms)
            for worker_id in range(1, args.users + 1)
        ]

        for future in as_completed(futures):
            worker_records = future.result()
            all_records.extend(worker_records)
            worker_id = worker_records[0]["worker"] if worker_records else "?"
            ok_count = sum(1 for item in worker_records if item.get("ok"))
            print(f"Worker {worker_id}: {ok_count}/{len(worker_records)} solicitudes OK")

    finished_at_perf = time.perf_counter()
    finished_at = time.strftime("%Y-%m-%d %H:%M:%S")

    summary = summarize(all_records, started_at_perf, finished_at_perf)

    accepted = (
        summary["success_rate"] >= args.min_success_rate
        and summary["latency_ms"]["p95"] <= args.max_p95_ms
        and summary["failed_business_requests"] == 0
    )

    report = {
        "test_id": "LOAD-MODERATE-v0.5",
        "started_at": started_at,
        "finished_at": finished_at,
        "base_url": base_url,
        "users": args.users,
        "requests_per_user": args.requests_per_user,
        "think_time_ms": args.think_time_ms,
        "acceptance_criteria": {
            "min_success_rate": args.min_success_rate,
            "max_p95_ms": args.max_p95_ms,
            "no_failed_business_requests": True,
        },
        "summary": summary,
        "ok": bool(accepted),
    }

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "timestamp",
        "worker",
        "endpoint_group",
        "method",
        "path",
        "status_code",
        "ok",
        "latency_ms",
        "bytes",
        "error",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in sorted(all_records, key=lambda item: (item.get("worker", 0), item.get("timestamp", ""))):
            writer.writerow(record)

    print("\nResumen:")
    print(f"  Solicitudes funcionales: {summary['total_business_requests']}")
    print(f"  Exitosas:                {summary['successful_business_requests']}")
    print(f"  Fallidas:                {summary['failed_business_requests']}")
    print(f"  Tasa de éxito:           {summary['success_rate'] * 100:.2f}%")
    print(f"  RPS:                     {summary['requests_per_second']}")
    print(f"  Latencia media:          {summary['latency_ms']['mean']} ms")
    print(f"  Latencia p95:            {summary['latency_ms']['p95']} ms")
    print(f"  Latencia máxima:         {summary['latency_ms']['max']} ms")
    print(f"  Códigos HTTP:            {summary['status_counts']}")

    print("\nResumen por endpoint:")
    for group, data in summary["endpoint_summary"].items():
        print(
            f"  {group}: total={data['total']}, ok={data['ok']}, "
            f"fallidas={data['failed']}, media={data['mean_ms']} ms, p95={data['p95_ms']} ms"
        )

    print(f"\nEvidencia JSON: {json_path}")
    print(f"Evidencia CSV:  {csv_path}")

    if accepted:
        print("\nResultado: APROBADO.")
        return 0

    print("\nResultado: FALLIDO.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
