import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.deps import get_current_user_ws
from app.emulators.manager import get_manager
from app.soap.client import SoapError

router = APIRouter(tags=["console"])


async def _authenticate_ws(websocket: WebSocket):
    token = websocket.cookies.get("access_token")
    db = SessionLocal()
    try:
        return get_current_user_ws(token, db)
    finally:
        db.close()


@router.websocket("/ws/console/{instance_id}")
async def console_ws(websocket: WebSocket, instance_id: str):
    user = await _authenticate_ws(websocket)
    if not user:
        await websocket.close(code=4401)
        return

    driver = get_manager().get_driver(instance_id)
    if not driver:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await websocket.send_text(f"Conectado a {driver.config.name}. Escribe un comando GM y pulsa Enter.")

    try:
        while True:
            command = (await websocket.receive_text()).strip()
            if not command:
                continue
            try:
                output = driver.execute_soap_command(command)
            except SoapError as exc:
                output = f"[ERROR] {exc}"
            await websocket.send_text(output)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/servers/{instance_id}/logs")
async def server_logs_ws(websocket: WebSocket, instance_id: str):
    user = await _authenticate_ws(websocket)
    if not user:
        await websocket.close(code=4401)
        return

    driver = get_manager().get_driver(instance_id)
    if not driver:
        await websocket.close(code=4404)
        return

    await websocket.accept()

    if driver.find_process() is None:
        await websocket.send_text("[La instancia no esta en ejecucion]")
        await websocket.close()
        return

    log_path = driver.current_console_log()
    if not log_path or not log_path.is_file():
        await websocket.send_text("[No hay log de consola activo]")
        await websocket.close()
        return

    try:
        with log_path.open("r", errors="replace") as log_fh:
            log_fh.seek(0, 2)
            while True:
                line = log_fh.readline()
                if line:
                    await websocket.send_text(line.rstrip("\n"))
                    continue
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=1)
                except asyncio.TimeoutError:
                    pass
    except WebSocketDisconnect:
        return
