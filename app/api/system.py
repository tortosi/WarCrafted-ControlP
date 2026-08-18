import psutil
from fastapi import APIRouter, Depends, HTTPException, status

from app import core_update, models, schemas
from app.config import get_settings
from app.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats", response_model=schemas.SystemStats)
def stats(current_user: models.User = Depends(get_current_user)):
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return schemas.SystemStats(
        cpu_percent=psutil.cpu_percent(interval=0.2),
        memory_percent=memory.percent,
        memory_used_mb=round(memory.used / (1024 * 1024), 1),
        memory_total_mb=round(memory.total / (1024 * 1024), 1),
        disk_percent=disk.percent,
    )


@router.get("/update-check")
def update_check(current_user: models.User = Depends(get_current_user)):
    """Compara la version instalada del panel con la del repositorio de GitHub."""
    settings = get_settings()
    if not settings.github_plugin_token:
        return {"configured": False}
    info = core_update.check_update(settings.github_plugin_token, settings.github_core_repo)
    return {"configured": True, **info}


@router.post("/update")
def update_panel(current_user: models.User = Depends(require_admin)):
    """Descarga la version actual del panel y la fusiona sobre la instalacion activa. No reinicia por si sola."""
    settings = get_settings()
    if not settings.github_plugin_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No hay un token de GitHub configurado")
    result = core_update.apply_update(settings.github_plugin_token, settings.github_core_repo)
    return {"success": True, **result}


@router.post("/restart")
def restart_panel(current_user: models.User = Depends(require_admin)):
    """Reinicia el proceso del panel para aplicar una actualizacion ya descargada.

    Requiere que un supervisor externo (systemd con Restart=always, o equivalente)
    vuelva a levantar el proceso; si no hay uno, el panel queda caido.
    """
    core_update.schedule_restart()
    return {"success": True, "message": "Reiniciando el panel..."}
