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
    
    logging.info(f"REPLY HANDLER: Received message from user {m.from_user.id}, chat type: {m.chat.type}, has reply: {bool(m.reply_to_message)}")
    
    # Проверяем, что это приватный чат и есть реплай
    if m.chat.type != ChatType.PRIVATE or not m.reply_to_message:
        logging.info(f"REPLY HANDLER: Skipping - not private chat or no reply. Chat type: {m.chat.type}, has reply: {bool(m.reply_to_message)}")
        return False
    
    # Проверяем, что есть текст
    if not (m.text and m.text.strip()):
        logging.info(f"REPLY HANDLER: Skipping - no text content")
        return False
    
    # Пропускаем команды
    if m.text.startswith('/'):
        logging.info(f"REPLY HANDLER: Skipping - command message: {m.text}")
        return False
    
    logging.info(f"REPLY HANDLER: Processing reply from user {m.from_user.id} to message {m.reply_to_message.message_id}: '{m.text[:50]}...'")
    
    # Пытаемся обработать как реплай в анонимном чате
    try:
        ok = await RelayService(bot, RelaysRepo(db)).handle_reply(
            m.from_user.id, 
            m.reply_to_message.message_id, 
            m.text
        )
        
        if ok:
            logging.info(f"REPLY HANDLER: Successfully processed reply from user {m.from_user.id}")
            try:
                await StatsService(StatsRepo(db), tz).inc("relay_msg")
            except Exception as e:
                logging.error(f"REPLY HANDLER: Error updating stats: {e}")
            return True
        else:
            logging.info(f"REPLY HANDLER: No active relay found for user {m.from_user.id} and message {m.reply_to_message.message_id}")
            
    except Exception as e:
        logging.error(f"REPLY HANDLER: Error processing reply from user {m.from_user.id}: {e}")
    
    return False
