import pymysql

from app.emulators.base import BaseEmulatorDriver


class PlayerbotsDriver(BaseEmulatorDriver):
    """Driver para instancias AzerothCore + Playerbots.

    Excluye las cuentas de bots del conteo de jugadores online para
    reflejar solo conexiones humanas reales.
    """

    BOT_NAME_PREFIXES = ("rndbot", "bot")

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
            like_clauses = " AND ".join(f"name NOT LIKE '{prefix}%'" for prefix in self.BOT_NAME_PREFIXES)
            query = f"SELECT COUNT(*) FROM characters WHERE online = 1 AND {like_clauses}"
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    row = cursor.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            return None
