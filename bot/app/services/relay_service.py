import time
from typing import Optional
from aiogram import Bot
from app.infra.repo.relays_repo import RelaysRepo

class RelayService:
    def __init__(self, bot: Bot, relays: RelaysRepo):
        self.bot = bot
        self.relays = relays

    async def open_dialog(self, author_id: int, requester_id: int, author_alias: str, requester_alias: str) -> bool:
        expires = int(time.time()) + 30*60
        await self.relays.create(author_id, requester_id, author_alias, requester_alias, expires)
        txt_a = ("🔒 Анонимный диалог открыт на 30 минут.\n"
                 f"Собеседник: «{requester_alias}». Пишите сюда.\n"
                 "/end — завершить.")
        txt_b = ("🔒 Анонимный диалог открыт на 30 минут.\n"
                 f"Собеседник: «{author_alias}». Пишите сюда.\n"
                 "/end — завершить.")
        ok = True
        try:
            await self.bot.send_message(author_id, txt_a)
        except Exception:
            ok = False
        try:
            await self.bot.send_message(requester_id, txt_b)
        except Exception:
            pass
        return ok

    async def pipe(self, sender_id: int, text: str) -> bool:
        now = int(time.time())
        row = await self.relays.get_active_for(sender_id, now)
        if not row:
            return False
        _, a_id, b_id, a_alias, b_alias, _ = row
        if sender_id == a_id:
            peer_id, sender_alias = b_id, a_alias
        else:
            peer_id, sender_alias = a_id, b_alias
        try:
            await self.bot.send_message(peer_id, f"{sender_alias}: {text}")
        except Exception:
            pass
        return True

    async def end_for(self, user_id: int) -> None:
        # Получаем активные диалоги перед закрытием
        now = int(time.time())
        active_relays = await self.relays.get_active_for(user_id, now)
        
        # Закрываем диалоги
        await self.relays.close_all_for(user_id, now)
        
        # Уведомляем второго участника
        if active_relays:
            _, a_id, b_id, a_alias, b_alias, _ = active_relays
            if user_id == a_id:
                peer_id, peer_alias = b_id, b_alias
            else:
                peer_id, peer_alias = a_id, a_alias
            
            try:
                await self.bot.send_message(peer_id, f"🔒 Диалог с «{peer_alias}» завершен.")
            except Exception:
                pass
