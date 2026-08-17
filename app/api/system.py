import psutil
from fastapi import APIRouter, Depends

from app import models, schemas
from app.deps import get_current_user

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
