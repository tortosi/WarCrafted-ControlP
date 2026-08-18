import logging
import shlex
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import psutil

from app.config import DATA_DIR, get_settings
from app.emulators import log_manager
from app.soap.client import SoapClient, SoapError

logger = logging.getLogger(__name__)

PID_DIR = DATA_DIR / "pids"


class ProcessControlError(Exception):
    """Error al iniciar o detener el proceso de una instancia."""


@dataclass
class InstanceConfig:
    id: str
    name: str
    type: str
    enabled: bool
    world_process: str
    auth_process: str
    start_cmd: str
    workdir: str
    soap_host: str
    soap_port: int
    soap_user: str
    soap_pass: str
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_characters: str
    acore_logs_dir: str = ""
    log_categories: str = ""


class BaseEmulatorDriver(ABC):
    """Interfaz comun para todos los drivers de emulador."""

    def __init__(self, config: InstanceConfig):
        self.config = config
        settings = get_settings()
        self._logs_root = Path(settings.instances_logs_dir)
        self._retention_days = settings.logs_retention_days
        self._max_runs = settings.logs_max_runs
        self.soap = SoapClient(
            host=config.soap_host,
            port=config.soap_port,
            username=config.soap_user,
            password=config.soap_pass,
        )
        PID_DIR.mkdir(parents=True, exist_ok=True)
        self._log_instance_dir().mkdir(parents=True, exist_ok=True)

    def _pid_file(self) -> Path:
        return PID_DIR / f"{self.config.id}.pid"

    def _log_instance_dir(self) -> Path:
        return self._logs_root / self.config.id

    def _log_categories(self) -> list[str]:
        raw = self.config.log_categories.strip()
        if not raw:
            return []
        return [category.strip().lower() for category in raw.split(",") if category.strip()]

    def current_console_log(self) -> Path | None:
        """Fichero de consola del run activo (el mas reciente), para el streaming en vivo."""
        for run in log_manager.list_runs(self._log_instance_dir()):
            if run["category"] == log_manager.CONSOLE_CATEGORY:
                return self._log_instance_dir() / run["filename"]
        return None

    def list_log_runs(self) -> list[dict]:
        return log_manager.list_runs(self._log_instance_dir())

    def read_log_run(self, filename: str) -> str | None:
        path = log_manager.resolve_safe(self._log_instance_dir(), filename)
        if path is None or not path.is_file():
            return None
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None

    def _read_pid(self) -> int | None:
        pid_file = self._pid_file()
        if not pid_file.exists():
            return None
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return None

    def _write_pid(self, pid: int) -> None:
        self._pid_file().write_text(str(pid))

    def _clear_pid(self) -> None:
        self._pid_file().unlink(missing_ok=True)

    def _matches_this_instance(self, proc: psutil.Process) -> bool:
        """Identifica el proceso de ESTA instancia, no cualquier proceso con el mismo binario.

        Varias instancias pueden compartir WORLD_PROCESS (p.ej. "worldserver"); el
        directorio de trabajo (WORKDIR) es lo unico que las distingue de forma fiable.
        """
        target = self.config.world_process.lower()
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

        if self.config.workdir:
            try:
                proc_cwd = Path(proc.cwd()).resolve()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return False
            if proc_cwd != Path(self.config.workdir).resolve():
                return False

        return True

    def find_process(self) -> psutil.Process | None:
        pid = self._read_pid()
        if pid is not None:
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    if self._matches_this_instance(proc):
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self._clear_pid()

        for proc in psutil.process_iter():
            if self._matches_this_instance(proc):
                self._write_pid(proc.pid)
                return proc
        return None

    def get_process_status(self) -> dict:
        proc = self.find_process()
        if not proc:
            return {"online": False, "pid": None, "cpu_percent": None, "cpu_percent_host": None, "memory_mb": None}
        try:
            # cpu_percent(interval=...) hace una medicion "antes/despues" con sleep real;
            # llamarlo dentro de oneshot() reutiliza el valor "antes" cacheado y siempre da 0%.
            # Esta normalizado a 1 nucleo = 100%, asi que un proceso multihilo puede superar
            # el 100% (ej. 179% con 2 nucleos casi saturados); cpu_percent_host lo reexpresa
            # como % de la capacidad total del host, comparable con el CPU del host del dashboard.
            cpu_percent = proc.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count() or 1
            cpu_percent_host = round(cpu_percent / cpu_count, 1)
            with proc.oneshot():
                memory_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
            return {
                "online": True,
                "pid": proc.pid,
                "cpu_percent": cpu_percent,
                "cpu_percent_host": cpu_percent_host,
                "memory_mb": memory_mb,
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"online": False, "pid": None, "cpu_percent": None, "cpu_percent_host": None, "memory_mb": None}

    def execute_soap_command(self, command: str) -> str:
        return self.soap.execute(command)

    def start(self) -> dict:
        existing = self.find_process()
        if existing:
            return {"success": True, "detail": "El servidor ya esta en ejecucion.", "pid": existing.pid}

        if not self.config.start_cmd:
            raise ProcessControlError("No hay START_CMD configurado para esta instancia.")

        workdir = Path(self.config.workdir) if self.config.workdir else None
        if workdir and not workdir.is_dir():
            raise ProcessControlError(f"El directorio de trabajo (WORKDIR) no existe: {workdir}")

        try:
            args = shlex.split(self.config.start_cmd)
        except ValueError as exc:
            raise ProcessControlError(f"START_CMD invalido: {exc}") from exc

        instance_dir = self._log_instance_dir()
        instance_dir.mkdir(parents=True, exist_ok=True)

        categories = self._log_categories()
        if self.config.acore_logs_dir and categories:
            log_manager.archive_native_logs(instance_dir, Path(self.config.acore_logs_dir), categories)

        console_log_path = instance_dir / log_manager.run_log_filename(
            log_manager.CONSOLE_CATEGORY, log_manager.timestamp_now()
        )
        try:
            log_fh = console_log_path.open("w", buffering=1)
        except OSError as exc:
            raise ProcessControlError(f"No se pudo abrir el archivo de log: {exc}") from exc

        try:
            log_fh.write(f"--- Inicio {self.config.name} ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
            process = subprocess.Popen(
                args,
                cwd=str(workdir) if workdir else None,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            logger.error("Fallo al iniciar '%s': %s", self.config.name, exc)
            raise ProcessControlError(f"No se pudo ejecutar '{self.config.start_cmd}': {exc}") from exc
        finally:
            log_fh.close()

        time.sleep(0.5)
        return_code = process.poll()
        if return_code is not None:
            tail = log_manager.tail_file(console_log_path)
            message = f"El proceso finalizo inmediatamente (codigo {return_code})."
            if tail:
                message += f" Ultimas lineas del log:\n{tail}"
            logger.error("Fallo al iniciar '%s': %s", self.config.name, message)
            raise ProcessControlError(message)

        self._write_pid(process.pid)
        log_manager.purge_old_logs(instance_dir, self._retention_days, self._max_runs)
        logger.info("Instancia '%s' iniciada con PID %s", self.config.name, process.pid)
        return {"success": True, "detail": "Servidor iniciado correctamente.", "pid": process.pid}

    def stop(self) -> dict:
        try:
            output = self.execute_soap_command("server shutdown 5")
            logger.info("Instancia '%s' detenida via SOAP.", self.config.name)
            return {"success": True, "detail": output}
        except SoapError as exc:
            proc = self.find_process()
            if not proc:
                return {"success": False, "detail": f"El servidor no estaba en ejecucion. ({exc})"}
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as term_exc:
                logger.error("Fallo al detener '%s': %s", self.config.name, term_exc)
                raise ProcessControlError(
                    f"No se pudo detener el proceso (PID {proc.pid}): {term_exc}"
                ) from term_exc
            self._clear_pid()
            logger.warning(
                "SOAP fallo para '%s' (%s); proceso PID %s detenido con SIGTERM.", self.config.name, exc, proc.pid
            )
            return {
                "success": True,
                "detail": f"El comando SOAP fallo ({exc}); se envio senal de apagado directamente al proceso (PID {proc.pid}).",
            }

    @abstractmethod
    def get_online_players(self) -> int | None:
        """Numero de jugadores conectados segun el esquema del emulador."""

    def get_status(self) -> dict:
        status = self.get_process_status()
        status["players_online"] = self.get_online_players() if status["online"] else None
        return status
