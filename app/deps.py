from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.security import decode_access_token


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ")
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def get_current_user_ws(token: str | None, db: Session) -> models.User | None:
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()
