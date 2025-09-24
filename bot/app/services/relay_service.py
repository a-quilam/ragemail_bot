import time
from aiogram import Bot
from app.infra.repo.relays_repo import RelaysRepo

class RelayService:
    def __init__(self, bot: Bot, relays: RelaysRepo):
        self.bot = bot
        self.relays = relays

    async def open_dialog(self, author_id: int, requester_id: int, author_alias: str, requester_alias: str) -> bool:
        import logging
        
        logging.info(f"RELAY SERVICE: open_dialog called for author {author_id} and requester {requester_id}")
        
        expires = int(time.time()) + 30*60
        
        txt_a = ("💬 <b>Анонимный чат</b>\n\n"
                 f"Вы связались с автором поста под псевдонимом <b>{requester_alias}</b>.\n\n"
                 f"🔒 <b>Ваш псевдоним:</b> {author_alias}\n\n"
                 f"⏰ Чат активен 30 минут.\n\n"
                 f"📝 <b>Отвечайте на это сообщение для отправки:</b>\n"
                 f"<code>/end</code> — завершить диалог")
        txt_b = ("💬 <b>Анонимный чат</b>\n\n"
                 f"Вы связались с автором поста под псевдонимом <b>{author_alias}</b>.\n\n"
                 f"🔒 <b>Ваш псевдоним:</b> {requester_alias}\n\n"
                 f"⏰ Чат активен 30 минут.\n\n"
                 f"📝 <b>Отвечайте на это сообщение для отправки:</b>\n"
                 f"<code>/end</code> — завершить диалог")
        
        ok = True
        a_message_id = None
        b_message_id = None
        
        try:
            msg_a = await self.bot.send_message(author_id, txt_a, parse_mode="HTML")
            a_message_id = msg_a.message_id
        except Exception as e:
            import logging
            logging.error(f"Failed to send message to author {author_id}: {e}")
            ok = False
        try:
            msg_b = await self.bot.send_message(requester_id, txt_b, parse_mode="HTML")
            b_message_id = msg_b.message_id
        except Exception as e:
            import logging
            logging.error(f"Failed to send message to requester {requester_id}: {e}")
            ok = False
        
        # Создаем релей с ID сообщений
        relay_id = await self.relays.create(author_id, requester_id, author_alias, requester_alias, expires, a_message_id, b_message_id)
        
        logging.info(f"RELAY SERVICE: Created relay {relay_id} with a_message_id={a_message_id}, b_message_id={b_message_id}")
        logging.info(f"RELAY SERVICE: open_dialog result: {ok}")
        
        return ok

    async def pipe(self, sender_id: int, text: str) -> bool:
        now = int(time.time())
        row = await self.relays.get_active_for(sender_id, now)
        if not row:
            return False
        _, a_id, b_id, a_alias, b_alias, _, _, _ = row
        if sender_id == a_id:
            peer_id, sender_alias = b_id, a_alias
        else:
            peer_id, sender_alias = a_id, b_alias
        try:
            await self.bot.send_message(peer_id, f"{sender_alias}: {text}")
        except Exception:
            pass
        return True

    async def handle_reply(self, sender_id: int, reply_to_message_id: int, text: str) -> bool:
        """Обработка реплая на сообщение анонимного чата"""
        import logging
        
        logging.info(f"RELAY SERVICE: handle_reply called for sender {sender_id}, message_id {reply_to_message_id}")
        
        now = int(time.time())
        row = await self.relays.get_by_message_id(sender_id, reply_to_message_id, now)
        
        if not row:
            logging.info(f"RELAY SERVICE: No active relay found for sender {sender_id} and message_id {reply_to_message_id}")
            return False
        
        logging.info(f"RELAY SERVICE: Found relay: {row}")
        
        _, a_id, b_id, a_alias, b_alias, _, a_msg_id, b_msg_id = row
        
        # Определяем получателя
        if sender_id == a_id:
            peer_id, sender_alias, peer_msg_id = b_id, a_alias, b_msg_id
        else:
            peer_id, sender_alias, peer_msg_id = a_id, b_alias, a_msg_id
        
        logging.info(f"RELAY SERVICE: Sending message from {sender_alias} to {peer_id}, peer_msg_id: {peer_msg_id}")
        
        try:
            # Отправляем сообщение как реплай на сообщение получателя
            if peer_msg_id:
                await self.bot.send_message(peer_id, f"{sender_alias}: {text}", reply_to_message_id=peer_msg_id)
                logging.info(f"RELAY SERVICE: Message sent as reply to {peer_msg_id}")
            else:
                await self.bot.send_message(peer_id, f"{sender_alias}: {text}")
                logging.info(f"RELAY SERVICE: Message sent without reply")
        except Exception as e:
            logging.error(f"RELAY SERVICE: Error sending message: {e}")
            return False
        
        return True

    async def end_for(self, user_id: int) -> None:
        # Получаем активные диалоги перед закрытием
        now = int(time.time())
        active_relays = await self.relays.get_active_for(user_id, now)
        
        # Закрываем диалоги
        await self.relays.close_all_for(user_id, now)
        
        # Уведомляем второго участника
        if active_relays:
            _, a_id, b_id, a_alias, b_alias, _, _, _ = active_relays
            if user_id == a_id:
                peer_id, peer_alias = b_id, b_alias
            else:
                peer_id, peer_alias = a_id, a_alias
            
            try:
                await self.bot.send_message(peer_id, f"🔒 Диалог с «{peer_alias}» завершен.")
            except Exception:
                pass
