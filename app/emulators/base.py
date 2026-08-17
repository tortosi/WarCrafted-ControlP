import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass

import psutil

from app.soap.client import SoapClient


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

    def find_process(self) -> psutil.Process | None:
        target = self.config.world_process.lower()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and target in proc.info["name"].lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def get_process_status(self) -> dict:
        proc = self.find_process()
        if not proc:
            return {"online": False, "pid": None, "cpu_percent": None, "memory_mb": None}
        try:
            with proc.oneshot():
                return {
                    "online": True,
                    "pid": proc.pid,
                    "cpu_percent": proc.cpu_percent(interval=0.1),
                    "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"online": False, "pid": None, "cpu_percent": None, "memory_mb": None}

    def execute_soap_command(self, command: str) -> str:
        return self.soap.execute(command)

    def start(self) -> str:
        if self.find_process():
            return "El servidor ya esta en ejecucion."
        if not self.config.start_cmd:
            return "No hay START_CMD configurado para esta instancia."
        subprocess.Popen(
            [self.config.start_cmd],
            cwd=self.config.workdir or None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return "Comando de inicio enviado."

    def stop(self) -> str:
        try:
            return self.execute_soap_command("server shutdown 5")
        except Exception:
            proc = self.find_process()
            if proc:
                proc.terminate()
                return "Proceso detenido (senal terminate)."
            return "El servidor no estaba en ejecucion."

    @abstractmethod
    def get_online_players(self) -> int | None:
        """Numero de jugadores conectados segun el esquema del emulador."""

    def get_status(self) -> dict:
        status = self.get_process_status()
        status["players_online"] = self.get_online_players() if status["online"] else None
        return status
