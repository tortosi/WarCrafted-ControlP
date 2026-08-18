from fastapi import APIRouter

router = APIRouter(tags=["example"])


@router.get("/info")
def get_info():
    """Retorna información del plugin de ejemplo."""
    return {
        "plugin": "example",
        "status": "active",
        "message": "Este es un plugin de demostración. Reemplázalo con tu lógica."
    }
