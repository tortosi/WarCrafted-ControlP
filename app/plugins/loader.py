import importlib.util
import json
import logging
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent


class PluginMetadata:
    """Metadatos de un plugin cargado."""

    def __init__(self, name: str, version: str = "0.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description


def _load_manifest(plugin_path: Path) -> PluginMetadata:
    """Lee manifest.json si existe, sino retorna metadatos básicos."""
    manifest_path = plugin_path / "manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            return PluginMetadata(
                name=data.get("name", plugin_path.name),
                version=data.get("version", "0.0.0"),
                description=data.get("description", ""),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Error leyendo manifest de {plugin_path.name}: {exc}")
    return PluginMetadata(name=plugin_path.name)


def _load_router(plugin_path: Path) -> APIRouter | None:
    """Importa dinámicamente router.py desde la carpeta del plugin."""
    router_path = plugin_path / "router.py"
    if not router_path.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(f"app.plugins.{plugin_path.name}.router", router_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            router = getattr(module, "router", None)
            if isinstance(router, APIRouter):
                return router
            logger.warning(f"Plugin {plugin_path.name}: router.py no exporta un APIRouter llamado 'router'")
    except Exception as exc:
        logger.error(f"Error cargando router de {plugin_path.name}: {exc}")
    return None


def load_plugins() -> list[tuple[str, APIRouter, PluginMetadata]]:
    """Descubre y carga todos los plugins disponibles.

    Retorna lista de tuplas (plugin_name, router, metadata).
    """
    plugins = []
    if not PLUGINS_DIR.exists():
        return plugins

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
            continue

        metadata = _load_manifest(plugin_dir)
        router = _load_router(plugin_dir)

        if router:
            plugins.append((plugin_dir.name, router, metadata))
            logger.info(f"Plugin '{metadata.name}' v{metadata.version} cargado desde {plugin_dir.name}")
        else:
            logger.debug(f"No se encontró router.py en {plugin_dir.name}, omitido")

    return plugins
