from aiogram import types
from aiogram.enums import ChatType
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo
from app.infra.repo.stats_repo import StatsRepo
from app.services.stats_service import StatsService
from zoneinfo import ZoneInfo
import logging

async def handle_reply(m: types.Message, db, bot, tz: ZoneInfo):
    """Обработка реплаев на сообщения анонимного чата"""
    
    # Проверяем, что это приватный чат и есть реплай
    if m.chat.type != ChatType.PRIVATE or not m.reply_to_message:
        return False
    
    # Проверяем, что есть текст
    if not (m.text and m.text.strip()):
        return False
    
    # Пропускаем команды
    if m.text.startswith('/'):
        return False
    
    logging.info(f"REPLY HANDLER: Processing reply from user {m.from_user.id} to message {m.reply_to_message.message_id}: '{m.text[:50]}...'")
    
    # Пытаемся обработать как реплай в анонимном чате
    ok = await RelayService(bot, RelaysRepo(db)).handle_reply(
        m.from_user.id, 
        m.reply_to_message.message_id, 
        m.text
    )
    
    if ok:
        try:
            await StatsService(StatsRepo(db), tz).inc("relay_msg")
        except Exception:
            pass
        return True
    
    return False
