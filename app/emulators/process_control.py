from pathlib import Path

import psutil


def matches_process(proc: psutil.Process, process_name: str, workdir: str) -> bool:
    """Identifica un proceso por nombre + WORKDIR, no solo por el binario: varias
    instancias pueden compartir el mismo nombre de proceso (p.ej. "worldserver")."""
    target = process_name.lower()
    try:
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False
        name = (proc.name() or "").lower()
        # El "comm" del proceso puede truncarse o ser el del interprete
        # (p.ej. wrappers/scripts); si no coincide, se prueba con cmdline.
        if target not in name and target not in " ".join(proc.cmdline()).lower():
            return False
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

    if workdir:
        try:
            proc_cwd = Path(proc.cwd()).resolve()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
        if proc_cwd != Path(workdir).resolve():
            return False

    return True


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid))


def clear_pid(pid_file: Path) -> None:
    pid_file.unlink(missing_ok=True)


def find_process(pid_file: Path, process_name: str, workdir: str) -> psutil.Process | None:
    pid = read_pid(pid_file)
    if pid is not None:
        if psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                if matches_process(proc, process_name, workdir):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        clear_pid(pid_file)

    for proc in psutil.process_iter():
        if matches_process(proc, process_name, workdir):
            write_pid(pid_file, proc.pid)
            return proc
    return None
