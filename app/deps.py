import time
from collections import defaultdict
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.emulators.manager import get_manager
from app.security import decode_access_token
from app.soap.client import SoapError

_login_attempts = defaultdict(list)
_cleanup_last = 0


def _cleanup_old_attempts() -> None:
    global _cleanup_last
    now = time.time()
    if now - _cleanup_last < 60:
        return
    _cleanup_last = now
    for key in list(_login_attempts.keys()):
        _login_attempts[key] = [t for t in _login_attempts[key] if now - t < 900]
        if not _login_attempts[key]:
            del _login_attempts[key]


def check_login_rate_limit(request: Request, username: str) -> None:
    _cleanup_old_attempts()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{username}"
    now = time.time()
    _login_attempts[key] = [t for t in _login_attempts[key] if now - t < 900]
    if len(_login_attempts[key]) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesion. Intenta de nuevo mas tarde."
        )


def record_login_attempt(request: Request, username: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{username}"
    _login_attempts[key].append(time.time())


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


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permisos de administrador")
    return current_user


def get_servers_snapshot() -> list[dict]:
    """Estado actual (CPU/RAM/jugadores/diff) de las instancias habilitadas.

    Pensada para tareas en segundo plano de plugins (hilos propios, sin
    request HTTP ni usuario autenticado) que necesiten leer estos datos
    igual que ya hace GET /api/servers, sin acceder directamente a
    EmulatorManager (fuera del contrato de importaciones de los plugins).
    """
    snapshot = []
    for driver in get_manager().list_drivers():
        if not driver.config.enabled:
            continue
        status_info = driver.get_status()
        snapshot.append(
            {
                "id": driver.config.id,
                "name": driver.config.name,
                "state": status_info["state"],
                "cpu_percent": status_info["cpu_percent"],
                "cpu_percent_host": status_info["cpu_percent_host"],
                "memory_mb": status_info["memory_mb"],
                "players_online": status_info["players_online"],
                "update_diff_ms": status_info["update_diff_ms"],
            }
        )
    return snapshot


def get_instance_modules_conf_dir(instance_id: str) -> Path | None:
    """Directorio etc/modules/ de una instancia habilitada, o None si no existe.

    Deriva la ruta del WORKDIR (etc/ es hermano de bin/), para que un plugin
    pueda listar/editar los .conf de los modulos sin conocer el layout de
    AzerothCore ni importar EmulatorManager directamente.
    """
    driver = get_manager().get_driver(instance_id)
    if not driver or not driver.config.enabled or not driver.config.workdir:
        return None
    conf_dir = Path(driver.config.workdir).parent / "etc" / "modules"
    return conf_dir if conf_dir.is_dir() else None


def reload_instance_config(instance_id: str) -> str:
    """Envia 'reload config' via SOAP a una instancia habilitada y devuelve la salida.

    Fijo a ese comando exacto (no un ejecutor generico) para que un plugin
    pueda aplicar cambios de configuracion sin abrir una via de ejecucion
    arbitraria de comandos GM.
    """
    driver = get_manager().get_driver(instance_id)
    if not driver or not driver.config.enabled:
        raise RuntimeError("Instancia no encontrada o deshabilitada.")
    try:
        return driver.execute_soap_command("reload config")
    except SoapError as exc:
        raise RuntimeError(f"No se pudo recargar la configuracion via SOAP: {exc}") from exc


def get_current_user_ws(token: str | None, db: Session) -> models.User | None:
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()
