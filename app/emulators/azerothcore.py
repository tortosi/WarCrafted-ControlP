import pymysql

from app.emulators.base import BaseEmulatorDriver


class AzerothCoreDriver(BaseEmulatorDriver):
    """Driver para instancias AzerothCore estandar."""

    def get_online_players(self) -> int | None:
        cfg = self.config
        try:
            conn = pymysql.connect(
                host=cfg.db_host,
                port=cfg.db_port,
                user=cfg.db_user,
                password=cfg.db_pass,
                database=cfg.db_characters,
                connect_timeout=3,
            )
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM characters WHERE online = 1")
                    row = cursor.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            return None
