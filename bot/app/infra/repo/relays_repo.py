import aiosqlite
import logging
from typing import Optional, Tuple

class RelaysRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        self._history_table_ready: Optional[bool] = None
        self._history_table_error_logged = False

    async def create(self, a_user_id: int, b_user_id: int, a_alias: str, b_alias: str, expires_at: int, a_message_id: int = None, b_message_id: int = None) -> int:
        cur = await self.db.execute(
            "INSERT INTO relays(a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id) VALUES(?,?,?,?,?,?,?)",
            (a_user_id, b_user_id, a_alias, b_alias, expires_at, a_message_id, b_message_id),
        )
        await self.db.commit()
        return cur.lastrowid

    async def get_active_for(self, user_id: int, now_ts: int) -> Optional[Tuple[int,int,int,str,str,int,int,int]]:
        return await (await self.db.execute(
            "SELECT id,a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id FROM relays WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ? ORDER BY id DESC LIMIT 1",
            (user_id, user_id, now_ts),
        )).fetchone()

    async def close_all_for(self, user_id: int, now_ts: int) -> None:
        await self.db.execute(
            "UPDATE relays SET expires_at=? WHERE (a_user_id=? OR b_user_id=?) AND expires_at> ?",
            (now_ts, user_id, user_id, now_ts),
        )
        await self.db.commit()

    async def get_by_message_id(self, user_id: int, message_id: int, now_ts: int) -> Optional[Tuple[int,int,int,str,str,int,int,int]]:
        """Получить активный релей по ID сообщения пользователя"""
        logging.info(f"RELAYS REPO: get_by_message_id called for user {user_id}, message_id {message_id}, now_ts {now_ts}")
        
        result = None
        if await self._ensure_history_table():
            try:
                result = await (await self.db.execute(
                    """
                    SELECT r.id, r.a_user_id, r.b_user_id, r.a_alias, r.b_alias, r.expires_at, r.a_message_id, r.b_message_id
                    FROM relays AS r
                    JOIN relay_messages AS rm ON rm.relay_id = r.id
                    WHERE rm.user_id = ? AND rm.message_id = ? AND r.expires_at > ?
                    ORDER BY rm.id DESC
                    LIMIT 1
                    """,
                    (user_id, message_id, now_ts),
                )).fetchone()
            except aiosqlite.OperationalError as err:
                logging.warning(f"RELAYS REPO: History table query failed: {err}")
                self._history_table_ready = False
                result = None

        if not result:
            logging.info("RELAYS REPO: No relay found via history table, falling back to legacy columns")
            result = await (await self.db.execute(
                """
                SELECT id,a_user_id,b_user_id,a_alias,b_alias,expires_at,a_message_id,b_message_id
                FROM relays
                WHERE ((a_user_id=? AND a_message_id=?) OR (b_user_id=? AND b_message_id=?))
                  AND expires_at> ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, message_id, user_id, message_id, now_ts),
            )).fetchone()

        if result:
            logging.info(f"RELAYS REPO: Found relay: {result}")
        else:
            logging.info(f"RELAYS REPO: No relay found for user {user_id} and message_id {message_id}")
            
        return result

    async def purge_expired(self, now_ts: int) -> None:
        await self.db.execute("DELETE FROM relays WHERE expires_at<=?", (now_ts,))
        await self.db.commit()

    async def record_message(self, relay_id: int, user_id: int, message_id: int) -> None:
        if message_id is None:
            return

        history_ready = await self._ensure_history_table()
        if history_ready:
            try:
                await self.db.execute(
                    "INSERT INTO relay_messages(relay_id, user_id, message_id) VALUES(?,?,?)",
                    (relay_id, user_id, message_id),
                )
            except aiosqlite.OperationalError as err:
                logging.warning(f"RELAYS REPO: Failed to record relay message history: {err}")
                self._history_table_ready = False

        await self.db.execute(
            """
            UPDATE relays
            SET a_message_id = CASE WHEN a_user_id = ? THEN ? ELSE a_message_id END,
                b_message_id = CASE WHEN b_user_id = ? THEN ? ELSE b_message_id END
            WHERE id = ?
            """,
            (user_id, message_id, user_id, message_id, relay_id),
        )
        await self.db.commit()

    async def get_last_message_id(self, relay_id: int, user_id: int) -> Optional[int]:
        row = None
        if await self._ensure_history_table():
            try:
                row = await (await self.db.execute(
                    "SELECT message_id FROM relay_messages WHERE relay_id=? AND user_id=? ORDER BY id DESC LIMIT 1",
                    (relay_id, user_id),
                )).fetchone()
            except aiosqlite.OperationalError as err:
                logging.warning(f"RELAYS REPO: Failed to read relay message history: {err}")
                self._history_table_ready = False

        if row:
            return row[0]

        # fallback to legacy columns if история пока не записана
        legacy = await (await self.db.execute(
            "SELECT a_user_id, b_user_id, a_message_id, b_message_id FROM relays WHERE id=?",
            (relay_id,),
        )).fetchone()
        if not legacy:
            return None

        a_user_id, b_user_id, a_message_id, b_message_id = legacy
        if user_id == a_user_id:
            return a_message_id
        if user_id == b_user_id:
            return b_message_id
        return None

    async def _ensure_history_table(self) -> bool:
        """Гарантируем, что таблица relay_messages доступна."""
        if self._history_table_ready:
            return True

        try:
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS relay_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relay_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    FOREIGN KEY(relay_id) REFERENCES relays(id) ON DELETE CASCADE
                )
                """
            )
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_relay_messages_user_message ON relay_messages(user_id, message_id)"
            )
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_relay_messages_relay ON relay_messages(relay_id)"
            )
            await self.db.commit()
            self._history_table_ready = True
            self._history_table_error_logged = False
            return True
        except aiosqlite.OperationalError as err:
            if not self._history_table_error_logged:
                logging.warning(f"RELAYS REPO: Unable to initialize relay message history table: {err}")
                self._history_table_error_logged = True
            self._history_table_ready = False
            return False
