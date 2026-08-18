import logging
import shlex
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import psutil

from app.config import DATA_DIR
from app.soap.client import SoapClient, SoapError

logger = logging.getLogger(__name__)

PID_DIR = DATA_DIR / "pids"
LOG_DIR = DATA_DIR / "logs"


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


class BaseEmulatorDriver(ABC):
    """Interfaz comun para todos los drivers de emulador."""

    def __init__(self, config: InstanceConfig):
        self.config = config
        self.soap = SoapClient(
            host=config.soap_host,
            port=config.soap_port,
            username=config.soap_user,
            password=config.soap_pass,
        )
        PID_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _pid_file(self) -> Path:
        return PID_DIR / f"{self.config.id}.pid"

    def _log_file(self) -> Path:
        return LOG_DIR / f"{self.config.id}.log"

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

    def get_recent_log(self, lines: int = 20) -> str:
        log_path = self._log_file()
        if not log_path.exists():
            return ""
        try:
            content = log_path.read_text(errors="replace").splitlines()
        except OSError:
            return ""
        return "\n".join(content[-lines:])

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

        try:
            log_fh = self._log_file().open("a", buffering=1)
        except OSError as exc:
            raise ProcessControlError(f"No se pudo abrir el archivo de log: {exc}") from exc

        try:
            log_fh.write(f"\n--- Inicio {self.config.name} ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
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
            tail = self.get_recent_log()
            message = f"El proceso finalizo inmediatamente (codigo {return_code})."
            if tail:
                message += f" Ultimas lineas del log:\n{tail}"
            logger.error("Fallo al iniciar '%s': %s", self.config.name, message)
            raise ProcessControlError(message)

        self._write_pid(process.pid)
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
