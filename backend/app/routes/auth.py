import secrets
import time
from typing import Optional

from fastapi import APIRouter, Cookie, Response
from fastapi.responses import JSONResponse

from app.config import SESSION_COOKIE, TEST_USER
from app.schemas import LoginRequest


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


@router.post("/api/login")
def api_login(payload: LoginRequest, response: Response):
    if payload.username != TEST_USER["username"] or payload.password != TEST_USER["password"]:
        return JSONResponse(
            status_code=401,
            content={"message": "Usuario o contrasena incorrectos."}
        )

    token = secrets.token_hex(24)

    sessions[token] = {
        "username": TEST_USER["username"],
        "name": TEST_USER["name"],
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
            "username": TEST_USER["username"],
            "name": TEST_USER["name"]
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
