from fastapi import APIRouter, Depends, HTTPException, status

from app import models, schemas
from app.deps import get_current_user
from app.emulators.base import BaseEmulatorDriver, ProcessControlError
from app.emulators.manager import EmulatorManager, get_manager
from app.soap.client import SoapError

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("", response_model=list[schemas.ServerSummary])
def list_servers(
    current_user: models.User = Depends(get_current_user),
    manager: EmulatorManager = Depends(get_manager),
):
    summaries = []
    for driver in manager.list_drivers():
        info = (
            driver.get_status()
            if driver.config.enabled
            else {
                "online": False,
                "pid": None,
                "cpu_percent": None,
                "cpu_percent_host": None,
                "memory_mb": None,
                "players_online": None,
            }
        )
        summaries.append(
            schemas.ServerSummary(
                id=driver.config.id,
                name=driver.config.name,
                type=driver.config.type,
                enabled=driver.config.enabled,
                online=info["online"],
                pid=info["pid"],
                cpu_percent=info["cpu_percent"],
                cpu_percent_host=info["cpu_percent_host"],
                memory_mb=info["memory_mb"],
                players_online=info["players_online"],
            )
        )

    for config, message in manager.list_invalid():
        summaries.append(
            schemas.ServerSummary(
                id=config.id,
                name=config.name,
                type=config.type,
                enabled=config.enabled,
                online=False,
                error=message,
            )
        )

    return summaries


def _get_driver_or_404(instance_id: str, manager: EmulatorManager) -> BaseEmulatorDriver:
    driver = manager.get_driver(instance_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
    return driver


@router.post("/{instance_id}/start")
def start_server(
    instance_id: str,
    current_user: models.User = Depends(get_current_user),
    manager: EmulatorManager = Depends(get_manager),
):
    driver = _get_driver_or_404(instance_id, manager)
    try:
        return driver.start()
    except ProcessControlError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/{instance_id}/stop")
def stop_server(
    instance_id: str,
    current_user: models.User = Depends(get_current_user),
    manager: EmulatorManager = Depends(get_manager),
):
    driver = _get_driver_or_404(instance_id, manager)
    try:
        return driver.stop()
    except ProcessControlError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{instance_id}/log", response_model=schemas.LogTail)
def get_server_log(
    instance_id: str,
    lines: int = 300,
    current_user: models.User = Depends(get_current_user),
    manager: EmulatorManager = Depends(get_manager),
):
    driver = _get_driver_or_404(instance_id, manager)
    return schemas.LogTail(content=driver.get_recent_log(max(1, min(lines, 2000))))


@router.post("/{instance_id}/command", response_model=schemas.CommandResult)
def run_command(
    instance_id: str,
    payload: schemas.CommandRequest,
    current_user: models.User = Depends(get_current_user),
    manager: EmulatorManager = Depends(get_manager),
):
    driver = _get_driver_or_404(instance_id, manager)
    try:
        output = driver.execute_soap_command(payload.command)
    except SoapError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return schemas.CommandResult(output=output)
