from dotenv import load_dotenv

load_dotenv()

import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.api import auth, console, servers, system
from app.config import BASE_DIR, get_settings
from app.database import init_db
from app.deps import get_db
from app.security import decode_access_token

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(system.router)
app.include_router(console.router)


def _current_user_or_none(request: Request, db: Session) -> models.User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    if _current_user_or_none(request, db):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")


@app.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    if _current_user_or_none(request, db):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "app_name": settings.app_name})


@app.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = _current_user_or_none(request, db)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "app_name": settings.app_name, "user": user}
    )


@app.get("/console/{instance_id}")
def console_page(request: Request, instance_id: str, db: Session = Depends(get_db)):
    user = _current_user_or_none(request, db)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "console.html",
        {"request": request, "app_name": settings.app_name, "instance_id": instance_id},
    )
