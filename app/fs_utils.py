import io
import os
import shutil
import tarfile
from pathlib import Path

from fastapi import HTTPException, status


def extract_tarball(tarball: bytes, dest_dir: Path, subpath: str | None = None) -> bool:
    """Extrae un tarball de GitHub (con su carpeta raiz `owner-repo-sha/`) en dest_dir.

    Si `subpath` se indica, solo extrae lo que hay bajo `<raiz>/<subpath>/`, dejandolo
    directamente en dest_dir (sin ese subpath de por medio). Si es None, extrae todo lo
    que hay bajo `<raiz>/`. Devuelve False si no se encontro nada que extraer.
    """
    dest_resolved = dest_dir.resolve()
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="El archivo descargado esta vacio")

        root_prefix = members[0].name.split("/", 1)[0]
        prefix = f"{root_prefix}/{subpath}/" if subpath else f"{root_prefix}/"
        found = False

        for member in members:
            if not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix) :]
            if not relative or not (member.isfile() or member.isdir()):
                continue

            dest_path = (dest_dir / relative).resolve()
            if dest_path != dest_resolved and dest_resolved not in dest_path.parents:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Contenido del archivo no seguro")

            found = True
            if member.isdir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                # open(..., "wb") crea el archivo con permisos por defecto (sin +x);
                # sin esto, scripts como run.sh pierden el bit de ejecucion al extraerlos.
                os.chmod(dest_path, member.mode & 0o777)

    return found


def overlay_copy(src_dir: Path, dest_dir: Path) -> None:
    """Copia src_dir sobre dest_dir sin tocar nada que ya hubiera en dest_dir y no venga en src_dir."""
    for src_path in src_dir.rglob("*"):
        relative = src_path.relative_to(src_dir)
        dest_path = dest_dir / relative
        if src_path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
