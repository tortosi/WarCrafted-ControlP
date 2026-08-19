import logging
import os

from dotenv import load_dotenv

from app.emulators.azerothcore import AzerothCoreDriver
from app.emulators.base import BaseEmulatorDriver, InstanceConfig
from app.emulators.playerbots import PlayerbotsDriver

logger = logging.getLogger(__name__)

DRIVER_REGISTRY: dict[str, type[BaseEmulatorDriver]] = {
    "azerothcore": AzerothCoreDriver,
    "playerbots": PlayerbotsDriver,
}


def _resolve_driver_class(type_name: str) -> type[BaseEmulatorDriver] | None:
    """Admite variantes de TYPE (p.ej. 'playerbots-acore', 'acore') ademas del valor exacto."""
    normalized = (type_name or "").strip().lower()
    if normalized in DRIVER_REGISTRY:
        return DRIVER_REGISTRY[normalized]
    if "playerbots" in normalized:
        return PlayerbotsDriver
    if "azerothcore" in normalized or normalized == "acore":
        return AzerothCoreDriver
    return None


def _load_instance_configs() -> list[InstanceConfig]:
    indices = set()
    for key in os.environ:
        if key.startswith("INSTANCE_"):
            parts = key.split("_")
            if len(parts) >= 3 and parts[1].isdigit():
                indices.add(parts[1])

    configs = []
    for idx in sorted(indices, key=int):
        prefix = f"INSTANCE_{idx}_"

        def env(name: str, default: str = "") -> str:
            return os.environ.get(prefix + name, default)

        if not env("NAME"):
            continue

        try:
            configs.append(
                InstanceConfig(
                    id=f"instance-{idx}",
                    name=env("NAME"),
                    type=env("TYPE", "azerothcore"),
                    enabled=env("ENABLED", "true").lower() == "true",
                    world_process=env("WORLD_PROCESS", "worldserver"),
                    auth_process=env("AUTH_PROCESS", "authserver"),
                    start_cmd=env("START_CMD"),
                    auth_start_cmd=env("AUTH_START_CMD"),
                    workdir=env("WORKDIR"),
                    soap_host=env("SOAP_HOST", "127.0.0.1"),
                    soap_port=int(env("SOAP_PORT") or "7878"),
                    soap_user=env("SOAP_USER"),
                    soap_pass=env("SOAP_PASS"),
                    db_host=env("DB_HOST", "127.0.0.1"),
                    db_port=int(env("DB_PORT") or "3306"),
                    db_user=env("DB_USER"),
                    db_pass=env("DB_PASS"),
                    db_characters=env("DB_CHARACTERS"),
                    acore_logs_dir=env("ACORE_LOGS_DIR"),
                    log_categories=env("LOG_CATEGORIES"),
                    db_auth=env("DB_AUTH", "acore_auth"),
                )
            )
        except ValueError as exc:
            logger.error("Instancia INSTANCE_%s_ ignorada por configuracion invalida: %s", idx, exc)

    return configs


class EmulatorManager:
    """Registro central de instancias de emulador configuradas via .env.

    Recarga el .env en cada acceso para reflejar cambios de configuracion
    (p.ej. anadir una instancia) sin necesidad de reiniciar el proceso.
    """

    def __init__(self) -> None:
        self._drivers: dict[str, BaseEmulatorDriver] = {}
        self._invalid: dict[str, tuple[InstanceConfig, str]] = {}
        self.reload()

    def reload(self) -> None:
        load_dotenv(override=True)
        drivers: dict[str, BaseEmulatorDriver] = {}
        invalid: dict[str, tuple[InstanceConfig, str]] = {}
        for config in _load_instance_configs():
            driver_cls = _resolve_driver_class(config.type)
            if not driver_cls:
                message = f"Tipo de emulador no reconocido: '{config.type}' (usa azerothcore o playerbots)"
                logger.warning("Instancia '%s' (%s): %s", config.name, config.id, message)
                invalid[config.id] = (config, message)
                continue
            drivers[config.id] = driver_cls(config)
        self._drivers = drivers
        self._invalid = invalid

    def list_drivers(self) -> list[BaseEmulatorDriver]:
        self.reload()
        return list(self._drivers.values())

    def list_invalid(self) -> list[tuple[InstanceConfig, str]]:
        return list(self._invalid.values())

    def get_driver(self, instance_id: str) -> BaseEmulatorDriver | None:
        self.reload()
        return self._drivers.get(instance_id)


_manager: EmulatorManager | None = None


def get_manager() -> EmulatorManager:
    global _manager
    if _manager is None:
        _manager = EmulatorManager()
    return _manager
