import secrets
import time
from typing import Optional

from fastapi import APIRouter, Cookie, Response
from fastapi.responses import JSONResponse

from app.config import SESSION_COOKIE
from app.schemas import LoginRequest, RegisterRequest
from app.db import get_user_by_username, verify_password, create_user


router = APIRouter()

sessions = {}


def get_session(token: Optional[str]):
    if not token:
        return None

    return sessions.get(token)


@router.get("/api/session")
def api_session(siris_session: Optional[str] = Cookie(default=None)):
    session = get_session(siris_session)

    return {
        "authenticated": bool(session),
        "user": {
            "username": session["username"],
            "name": session["name"]
        } if session else None
    }

@router.post("/api/register")
def api_register(payload: RegisterRequest):
    username = payload.username.strip()
    name = payload.name.strip()
    password = payload.password

    if len(username) < 3:
        return JSONResponse(
            status_code=400,
            content={"message": "El usuario debe tener al menos 3 caracteres."}
        )

    if len(name) < 3:
        return JSONResponse(
            status_code=400,
            content={"message": "El nombre debe tener al menos 3 caracteres."}
        )

    if len(password) < 6:
        return JSONResponse(
            status_code=400,
            content={"message": "La contraseña debe tener al menos 6 caracteres."}
        )

    existing_user = get_user_by_username(username)

    if existing_user:
        return JSONResponse(
            status_code=409,
            content={"message": "El usuario ya existe."}
        )

    create_user(
        username=username,
        password=password,
        name=name,
        is_active=1
    )

    return {
        "message": "Usuario registrado correctamente.",
        "user": {
            "username": username,
            "name": name
        }
    }

@router.post("/api/login")
def api_login(payload: LoginRequest, response: Response):
    user = get_user_by_username(payload.username)

    if not user:
        return JSONResponse(
            status_code=401,
            content={"message": "Usuario o contrasena incorrectos."}
        )

    if not user["is_active"]:
        return JSONResponse(
            status_code=403,
            content={"message": "Usuario inactivo."}
        )

    is_valid_password = verify_password(
        password=payload.password,
        salt=user["salt"],
        expected_hash=user["password_hash"]
    )

    if not is_valid_password:
        return JSONResponse(
            status_code=401,
            content={"message": "Usuario o contrasena incorrectos."}
        )

    token = secrets.token_hex(24)

    sessions[token] = {
        "username": user["username"],
        "name": user["name"],
        "createdAt": time.time()
    }

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/"
    )

    return {
        "message": "Login correcto.",
        "user": {
            "username": user["username"],
            "name": user["name"]
        }
    }


@router.post("/api/logout")
def api_logout(response: Response, siris_session: Optional[str] = Cookie(default=None)):
    if siris_session:
        sessions.pop(siris_session, None)

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/"
    )

    return {"message": "Sesion cerrada."}
