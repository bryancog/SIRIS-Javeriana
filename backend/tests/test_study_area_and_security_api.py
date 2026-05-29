def test_api_08_study_area_returns_valid_geojson(client):
    response = client.get("/api/study-area")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] in {"Feature", "FeatureCollection"}


def test_sec_01_area_export_requires_session(client):
    response = client.post(
        "/api/area/export",
        json={
            "polygon": [
                {"lat": 1.21, "lng": -77.30},
                {"lat": 1.22, "lng": -77.28},
                {"lat": 1.20, "lng": -77.27},
            ],
            "dateFrom": "2016-01-01",
            "dateTo": "2026-05-01",
        },
    )

    assert response.status_code == 401
    assert "no autenticada" in response.json()["message"].lower()


def test_sec_02_geotiff_status_requires_session(client):
    response = client.get("/api/area/geotiff-status")

    assert response.status_code == 401
    assert "no autenticada" in response.json()["message"].lower()


def test_sec_03_cancel_export_requires_session(client):
    response = client.post("/api/area/cancel")

    assert response.status_code == 401
    assert "no autenticada" in response.json()["message"].lower()


def test_sec_04_exports_missing_file_returns_404(client):
    response = client.get("/exports/archivo_inexistente.mp4")

    assert response.status_code == 404


def test_sec_05_exports_path_traversal_is_rejected_or_not_found(client):
    response = client.get("/exports/%2E%2E/siris.db")

    assert response.status_code in {403, 404}
