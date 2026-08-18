import base64
import io
import json
import logging
import os
import re
import shutil
import tarfile
from pathlib import Path

import requests
from fastapi import HTTPException, status

from app.config import BASE_DIR, get_settings

logger = logging.getLogger(__name__)

ENV_PATH = BASE_DIR / ".env"
PLUGINS_DIR = BASE_DIR / "app" / "plugins"
GITHUB_API = "https://api.github.com"
PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
REQUEST_TIMEOUT = 15


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def write_token(token: str) -> None:
    """Actualiza (o añade) GITHUB_PLUGIN_TOKEN en .env sin tocar el resto de variables."""
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    new_line = f"GITHUB_PLUGIN_TOKEN={token}"
    for i, line in enumerate(lines):
        if line.startswith("GITHUB_PLUGIN_TOKEN="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)

    tmp_path = ENV_PATH.parent / f"{ENV_PATH.name}.tmp"
    tmp_path.write_text("\n".join(lines) + "\n")
    tmp_path.replace(ENV_PATH)

    os.environ["GITHUB_PLUGIN_TOKEN"] = token
    get_settings.cache_clear()


def verify_token(token: str, repo: str) -> None:
    """Comprueba que el token es valido y da acceso al repo de plugins configurado."""
    try:
        response = requests.get(f"{GITHUB_API}/repos/{repo}", headers=_headers(token), timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"No se pudo contactar con GitHub: {exc}") from exc

    if response.status_code == 401:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Token de GitHub invalido")
    if response.status_code == 404:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"El token es valido pero no tiene acceso al repositorio {repo}",
        )
    if not response.ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub respondio con error {response.status_code} al verificar el token",
        )


def _fetch_manifest(token: str, repo: str, plugin_name: str) -> dict:
    try:
        response = requests.get(
            f"{GITHUB_API}/repos/{repo}/contents/{plugin_name}/manifest.json",
            headers=_headers(token),
            timeout=REQUEST_TIMEOUT,
        )
        if response.ok:
            content = response.json()
            return json.loads(base64.b64decode(content["content"]).decode("utf-8"))
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning(f"No se pudo leer manifest.json de {plugin_name}: {exc}")
    return {}


def fetch_catalog(token: str, repo: str) -> list[dict]:
    """Lista las carpetas de módulo del repo de plugins, marcando cuáles ya están instaladas."""
    try:
        response = requests.get(
            f"{GITHUB_API}/repos/{repo}/contents/", headers=_headers(token), timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"No se pudo contactar con GitHub: {exc}") from exc

    if not response.ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub respondio con error {response.status_code} al listar el catalogo",
        )

    catalog = []
    for entry in response.json():
        if entry.get("type") != "dir" or entry["name"].startswith((".", "_")):
            continue
        name = entry["name"]
        manifest = _fetch_manifest(token, repo, name)
        catalog.append(
            {
                "slug": name,
                "name": manifest.get("name", name),
                "version": manifest.get("version", "0.0.0"),
                "description": manifest.get("description", ""),
                "installed": (PLUGINS_DIR / name).is_dir(),
            }
        )
    return catalog


def install_plugin(token: str, repo: str, plugin_name: str) -> None:
    """Descarga la carpeta `plugin_name` del repo y la extrae limpia en app/plugins/<plugin_name>/."""
    if not PLUGIN_NAME_RE.match(plugin_name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Nombre de plugin invalido")

    target_dir = PLUGINS_DIR / plugin_name
    if target_dir.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"El plugin '{plugin_name}' ya esta instalado")

    try:
        response = requests.get(f"{GITHUB_API}/repos/{repo}/tarball", headers=_headers(token), timeout=60)
    except requests.RequestException as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"No se pudo descargar el plugin: {exc}") from exc

    if not response.ok:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub respondio con error {response.status_code} al descargar el repositorio",
        )

    tmp_dir = target_dir.with_name(f".{plugin_name}.install-tmp")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True)

    try:
        _extract_plugin(response.content, plugin_name, tmp_dir)
        tmp_dir.replace(target_dir)
    except HTTPException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except (tarfile.TarError, OSError) as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Error al extraer el plugin: {exc}") from exc


def _extract_plugin(tarball: bytes, plugin_name: str, tmp_dir: Path) -> None:
    tmp_resolved = tmp_dir.resolve()
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="El archivo descargado esta vacio")

        root_prefix = members[0].name.split("/", 1)[0]
        plugin_prefix = f"{root_prefix}/{plugin_name}/"
        found = False

        for member in members:
            if not member.name.startswith(plugin_prefix):
                continue
            relative = member.name[len(plugin_prefix) :]
            if not relative or not (member.isfile() or member.isdir()):
                continue

            dest_path = (tmp_dir / relative).resolve()
            if dest_path != tmp_resolved and tmp_resolved not in dest_path.parents:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Contenido del archivo no seguro")

            found = True
            if member.isdir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"'{plugin_name}' no existe en el repositorio")
