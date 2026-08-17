from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.deps import get_current_user_ws
from app.emulators.manager import get_manager
from app.soap.client import SoapError

router = APIRouter(tags=["console"])


@router.websocket("/ws/console/{instance_id}")
async def console_ws(websocket: WebSocket, instance_id: str):
    token = websocket.cookies.get("access_token")
    db = SessionLocal()
    try:
        user = get_current_user_ws(token, db)
    finally:
        db.close()

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
