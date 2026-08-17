import os

from app.emulators.azerothcore import AzerothCoreDriver
from app.emulators.base import BaseEmulatorDriver, InstanceConfig
from app.emulators.playerbots import PlayerbotsDriver

DRIVER_REGISTRY: dict[str, type[BaseEmulatorDriver]] = {
    "azerothcore": AzerothCoreDriver,
    "playerbots": PlayerbotsDriver,
}


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

        configs.append(
            InstanceConfig(
                id=f"instance-{idx}",
                name=env("NAME"),
                type=env("TYPE", "azerothcore"),
                enabled=env("ENABLED", "true").lower() == "true",
                world_process=env("WORLD_PROCESS", "worldserver"),
                auth_process=env("AUTH_PROCESS", "authserver"),
                start_cmd=env("START_CMD"),
                workdir=env("WORKDIR"),
                soap_host=env("SOAP_HOST", "127.0.0.1"),
                soap_port=int(env("SOAP_PORT", "7878")),
                soap_user=env("SOAP_USER"),
                soap_pass=env("SOAP_PASS"),
                db_host=env("DB_HOST", "127.0.0.1"),
                db_port=int(env("DB_PORT", "3306")),
                db_user=env("DB_USER"),
                db_pass=env("DB_PASS"),
                db_characters=env("DB_CHARACTERS"),
            )
        )
    return configs


class EmulatorManager:
    """Registro central de instancias de emulador configuradas via .env."""

    def __init__(self) -> None:
        self._drivers: dict[str, BaseEmulatorDriver] = {}
        self.reload()

    def reload(self) -> None:
        self._drivers.clear()
        for config in _load_instance_configs():
            driver_cls = DRIVER_REGISTRY.get(config.type)
            if not driver_cls:
                continue
            self._drivers[config.id] = driver_cls(config)

    def list_drivers(self) -> list[BaseEmulatorDriver]:
        return list(self._drivers.values())

    def get_driver(self, instance_id: str) -> BaseEmulatorDriver | None:
        return self._drivers.get(instance_id)


_manager: EmulatorManager | None = None


def get_manager() -> EmulatorManager:
    global _manager
    if _manager is None:
        _manager = EmulatorManager()
    return _manager
