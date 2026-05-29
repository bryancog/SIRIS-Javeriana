import time


def unique_username(prefix="testuser"):
    return f"{prefix}_{int(time.time() * 1000)}"


def test_api_01_register_success(client):
    username = unique_username()

    response = client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Prueba",
            "password": "Password123",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Usuario registrado correctamente."
    assert payload["user"]["username"] == username
    assert payload["user"]["name"] == "Usuario Prueba"


def test_api_02_register_duplicate_user(client):
    username = unique_username("duplicado")

    first_response = client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Duplicado",
            "password": "Password123",
        },
    )

    second_response = client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Duplicado",
            "password": "Password123",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert "ya existe" in second_response.json()["message"]


def test_api_03_register_rejects_invalid_fields(client):
    cases = [
        (
            {"username": "ab", "name": "Usuario Prueba", "password": "Password123"},
            "usuario debe tener",
        ),
        (
            {"username": "usuario_valido", "name": "AB", "password": "Password123"},
            "nombre debe tener",
        ),
        (
            {"username": "usuario_valido", "name": "Usuario Prueba", "password": "123"},
            "contraseña debe tener",
        ),
    ]

    for payload, expected_message in cases:
        response = client.post("/api/register", json=payload)
        assert response.status_code == 400
        assert expected_message in response.json()["message"].lower()


def test_api_04_login_success_and_session_authenticated(client):
    username = unique_username("loginok")

    register_response = client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Login",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": "Password123",
        },
    )

    session_response = client.get("/api/session")

    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert "siris_session" in login_response.cookies
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True
    assert session_response.json()["user"]["username"] == username


def test_api_05_login_rejects_invalid_password(client):
    username = unique_username("badlogin")

    client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Login",
            "password": "Password123",
        },
    )

    response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["message"].lower()


def test_api_06_session_without_authentication(client):
    response = client.get("/api/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert response.json()["user"] is None


def test_api_07_logout_closes_session(client):
    username = unique_username("logout")

    client.post(
        "/api/register",
        json={
            "username": username,
            "name": "Usuario Logout",
            "password": "Password123",
        },
    )

    login_response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": "Password123",
        },
    )

    assert login_response.status_code == 200
    assert client.get("/api/session").json()["authenticated"] is True

    logout_response = client.post("/api/logout")
    session_response = client.get("/api/session")

    assert logout_response.status_code == 200
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is False
