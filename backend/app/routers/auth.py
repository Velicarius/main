from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4
import os

from fastapi import FastAPI
from fastapi import status

# --- DB glue (минимально): возьми ваши session/engine/model, поправь импорты при необходимости ---
from sqlalchemy.orm import Session as SASession
from sqlalchemy import select, insert
from app.database import get_db  # если у вас другой путь к dependency — поправь
from app.models.user import User  # модель User с полями id(UUID), email, name — поправь под вашу схему

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth конфиг из ENV
_cfg = {
    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    "GOOGLE_DISCOVERY_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "BASE_URL": os.getenv("PUBLIC_BASE_URL", "http://localhost:8001"),
    "SESSION_SECRET": os.getenv("SESSION_SECRET", "dev-secret-change-me"),
}
config = Config(environ=_cfg)
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url=_cfg["GOOGLE_DISCOVERY_URL"],
    client_id=_cfg["GOOGLE_CLIENT_ID"],
    client_secret=_cfg["GOOGLE_CLIENT_SECRET"],
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login")
async def login(request: Request):
    redirect_uri = _cfg["BASE_URL"] + "/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, db: SASession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    name = userinfo.get("name") or ""

    if not email:
        return JSONResponse({"error": "email not provided by Google"}, status_code=400)

    # upsert пользователя
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        # создаём
        uid = uuid4()
        db.execute(insert(User).values(id=uid, email=email, name=name))
        db.commit()
        user = db.execute(select(User).where(User.email == email)).scalar_one()

    # сохраняем user_id в сессию
    request.session["user_id"] = str(user.id)
    request.session["email"] = user.email
    request.session["name"] = user.name

    # редирект в UI
    return RedirectResponse(url="/ui/#/dashboard/overview", status_code=status.HTTP_302_FOUND)

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"ok": True})

@router.get("/me")
async def me(request: Request):
    return {
        "user_id": request.session.get("user_id"),
        "email": request.session.get("email"),
        "name": request.session.get("name"),
        "authenticated": bool(request.session.get("user_id")),
    }

