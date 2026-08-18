from fastapi import APIRouter, Depends, HTTPException, Request, status

from app import models, schemas
from app.config import get_settings
from app.deps import get_current_user
from app.plugins import store
from app.plugins.loader import load_single_plugin

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


def _require_admin(current_user: models.User) -> None:
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Requiere permisos de administrador")


def _plugin_summary(slug: str, metadata) -> dict:
    return {
        "slug": slug,
        "name": metadata.name,
        "version": metadata.version,
        "has_ui": metadata.has_ui,
        "title": metadata.ui_title or metadata.name,
        "route": metadata.ui_route,
        "icon": metadata.icon,
    }


@router.get("")
@router.get("/")
def list_plugins(request: Request, current_user: models.User = Depends(get_current_user)):
    """Lista los plugins activos y sus metadatos, para que la navbar arme el menu."""
    return [_plugin_summary(slug, metadata) for slug, _router, metadata in request.app.state.plugins]


@router.post("/setup-token")
def setup_token(payload: schemas.GithubTokenRequest, current_user: models.User = Depends(get_current_user)):
    """Valida un token de GitHub contra el repo de plugins y lo guarda en .env."""
    _require_admin(current_user)
    repo = get_settings().github_plugin_repo
    store.verify_token(payload.token, repo)
    store.write_token(payload.token)
    return {"success": True, "message": "Token guardado correctamente"}


@router.get("/catalog")
def get_catalog(current_user: models.User = Depends(get_current_user)):
    """Lista el catalogo de plugins del repo de GitHub, indicando cuales ya estan instalados."""
    settings = get_settings()
    if not settings.github_plugin_token:
        return {"configured": False, "plugins": []}
    plugins = store.fetch_catalog(settings.github_plugin_token, settings.github_plugin_repo)
    return {"configured": True, "plugins": plugins}


@router.post("/install/{plugin_name}")
def install_plugin(plugin_name: str, request: Request, current_user: models.User = Depends(get_current_user)):
    """Descarga un plugin del catalogo y lo monta en caliente en la app activa, sin reiniciar el panel."""
    _require_admin(current_user)
    settings = get_settings()
    if not settings.github_plugin_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No hay un token de GitHub configurado")

    store.install_plugin(settings.github_plugin_token, settings.github_plugin_repo, plugin_name)

    loaded = load_single_plugin(plugin_name)
    if not loaded:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"El plugin '{plugin_name}' se descargo pero no expone un router.py valido",
        )

    slug, plugin_router, metadata = loaded
    request.app.include_router(plugin_router, prefix=f"/api/v1/plugins/{slug}", tags=[f"plugin: {metadata.name}"])
    request.app.state.plugins = [*request.app.state.plugins, loaded]

    return {"success": True, "plugin": _plugin_summary(slug, metadata)}
