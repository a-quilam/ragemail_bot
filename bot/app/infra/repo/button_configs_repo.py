import aiosqlite
import json
from typing import List, Dict, Any, Optional

class ButtonConfigsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_config(self, mailbox_id: int) -> List[Dict[str, Any]]:
        """Получить конфигурацию кнопок для ящика"""
        row = await (await self.db.execute(
            "SELECT button_config FROM mailbox_button_configs WHERE mailbox_id=?", 
            (mailbox_id,)
        )).fetchone()
        
        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return self._get_default_config()
        return self._get_default_config()

    async def set_config(self, mailbox_id: int, config: List[Dict[str, Any]]) -> None:
        """Установить конфигурацию кнопок для ящика"""
        config_json = json.dumps(config, ensure_ascii=False)
        await self.db.execute(
            "INSERT INTO mailbox_button_configs(mailbox_id, button_config) VALUES(?, ?) "
            "ON CONFLICT(mailbox_id) DO UPDATE SET button_config=excluded.button_config",
            (mailbox_id, config_json)
        )
        await self.db.commit()

    def _get_default_config(self) -> List[Dict[str, Any]]:
        """Получить конфигурацию кнопок по умолчанию"""
        return [
            {
                "type": "row",
                "buttons": [
                    {
                        "type": "extend",
                        "text": "➕1 ч",
                        "callback_data": "ext:1h",
                        "enabled": True
                    },
                    {
                        "type": "contact",
                        "text": "💬 Поговорить",
                        "callback_data": "contact",
                        "enabled": True
                    }
                ]
            }
        ]

    async def delete_config(self, mailbox_id: int) -> None:
        """Удалить конфигурацию кнопок для ящика"""
        await self.db.execute(
            "DELETE FROM mailbox_button_configs WHERE mailbox_id=?", 
            (mailbox_id,)
        )
        await self.db.commit()
