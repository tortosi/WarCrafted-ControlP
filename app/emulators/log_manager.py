import re
import shutil
import time
from pathlib import Path

CONSOLE_CATEGORY = "worldserver"

# Vista previa acotada: leer solo el final del archivo evita cargar logs de
# varios MB/GB enteros en memoria y congelar el navegador al renderizarlos.
PREVIEW_MAX_BYTES = 512_000

NATIVE_CATEGORIES: dict[str, str] = {
    "server": "Server.log",
    "errors": "Errors.log",
    "playerbots": "Playerbots.log",
    "gm": "GM.log",
    "chat": "chat.log",
}

_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_([a-z0-9]+)\.log$")


def timestamp_now() -> str:
    return time.strftime("%Y-%m-%d_%H-%M-%S")


def _timestamp_from_mtime(path: Path) -> str:
    return time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(path.stat().st_mtime))


def run_log_filename(category: str, timestamp: str) -> str:
    return f"{timestamp}_{category}.log"


def _parse_run_log_filename(filename: str) -> tuple[str, str] | None:
    match = _FILENAME_RE.match(filename)
    if not match:
        return None
    timestamp, category = match.groups()
    return timestamp, category


def resolve_safe(instance_dir: Path, filename: str) -> Path | None:
    """Resuelve `filename` dentro de `instance_dir`; None si el nombre intenta escapar de ella."""
    base = instance_dir.resolve()
    candidate = (instance_dir / filename).resolve()
    if candidate != base and base not in candidate.parents:
        return None
    return candidate


def archive_native_logs(instance_dir: Path, acore_logs_dir: Path, categories: list[str]) -> None:
    """Copia al historico los ficheros nativos de AzerothCore del run que acaba de terminar.

    AzerothCore sobreescribe estos ficheros (Mode=w) al arrancar, asi que este es el
    unico momento seguro para archivarlos: justo antes de lanzar el proceso nuevo.
    """
    for category in categories:
        native_name = NATIVE_CATEGORIES.get(category)
        if not native_name:
            continue
        native_path = acore_logs_dir / native_name
        if not native_path.is_file():
            continue
        dest = instance_dir / run_log_filename(category, _timestamp_from_mtime(native_path))
        if dest.exists():
            continue
        try:
            shutil.copy2(native_path, dest)
        except OSError:
            continue


def purge_old_logs(instance_dir: Path, retention_days: int, max_runs: int) -> None:
    if not instance_dir.is_dir():
        return
    by_category: dict[str, list[Path]] = {}
    for path in instance_dir.glob("*.log"):
        parsed = _parse_run_log_filename(path.name)
        if not parsed:
            continue
        by_category.setdefault(parsed[1], []).append(path)

    cutoff = time.time() - retention_days * 86400
    for files in by_category.values():
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        survivors = []
        for path in files:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
            else:
                survivors.append(path)
        for path in survivors[max_runs:]:
            path.unlink(missing_ok=True)


def list_runs(instance_dir: Path) -> list[dict]:
    if not instance_dir.is_dir():
        return []
    runs = []
    for path in instance_dir.glob("*.log"):
        parsed = _parse_run_log_filename(path.name)
        if not parsed:
            continue
        timestamp, category = parsed
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        runs.append(
            {
                "filename": path.name,
                "category": category,
                "started_at": timestamp,
                "size_bytes": size_bytes,
            }
        )
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    return runs


def read_preview(path: Path, max_bytes: int = PREVIEW_MAX_BYTES) -> tuple[str, bool, int]:
    """Lee como mucho los ultimos `max_bytes` de `path` sin cargar el archivo entero.

    Devuelve (contenido, truncado, tamano_total_en_bytes). El seek desde el
    final hace que el coste de lectura no dependa del tamano del archivo.
    """
    size = path.stat().st_size
    truncated = size > max_bytes
    with path.open("rb") as fh:
        if truncated:
            fh.seek(size - max_bytes)
        raw = fh.read()
    if truncated:
        # la primera linea puede estar cortada a mitad; se descarta
        newline = raw.find(b"\n")
        if newline != -1:
            raw = raw[newline + 1 :]
    return raw.decode("utf-8", errors="replace"), truncated, size


def tail_file(path: Path, lines: int = 20) -> str:
    if not path.exists():
        return ""
    try:
        content = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])
