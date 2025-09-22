"""
Сервис для отслеживания каналов, где бот является администратором
"""
import logging
from typing import List, Dict, Optional
from aiogram import Bot
from app.infra.tg_api import bot_is_admin

class ChannelTracker:
    def __init__(self, db):
        self.db = db
        self._channels_cache = {}
    
    async def get_user_available_channels(self, bot: Bot, user_id: int) -> List[Dict]:
        """
        Получить список каналов, доступных пользователю для создания ящика.
        Простая проверка каналов где бот админ.
        """
        try:
            # Получаем ID каналов, где у пользователя уже есть ящики
            from app.infra.repo.mailboxes_repo import MailboxesRepo
            mailboxes_repo = MailboxesRepo(self.db)
            existing_mailboxes = await mailboxes_repo.list_all()
            
            user_channel_ids = set()
            for mailbox_id, title, channel_id, stat_day, stat_time, creator_id in existing_mailboxes:
                if creator_id == user_id:
                    user_channel_ids.add(channel_id)
            
            # Получаем каналы где бот админ
            admin_channels = await self._get_all_admin_channels(bot)
            
            # Фильтруем каналы, где у пользователя еще нет ящика
            available_channels = []
            for channel in admin_channels:
                if channel["id"] not in user_channel_ids:
                    available_channels.append(channel)
            
            return available_channels
            
        except Exception as e:
            logging.error(f"Error getting user available channels: {e}")
            return []
    
    async def track_channel_addition(self, bot: Bot, channel_id: int, user_id: int):
        """
        Отслеживать добавление бота в канал
        """
        try:
            if await bot_is_admin(bot, channel_id):
                chat = await bot.get_chat(channel_id)
                logging.info(f"Bot added to channel {channel_id} ({chat.title}) by user {user_id}")
        except Exception as e:
            logging.error(f"Error tracking channel addition: {e}")
    
    async def _get_all_admin_channels(self, bot: Bot) -> List[Dict]:
        """
        Получить ВСЕ каналы, где бот является администратором.
        Простая проверка через getUpdates и конфиг.
        """
        admin_channels = []
        
        try:
            # Получаем обновления для поиска каналов
            updates = await bot.get_updates(limit=100, timeout=1)
            
            # Собираем уникальные ID чатов из обновлений
            chat_ids = set()
            for update in updates:
                if update.message and update.message.chat:
                    chat_ids.add(update.message.chat.id)
                elif update.channel_post and update.channel_post.chat:
                    chat_ids.add(update.channel_post.chat.id)
                elif update.edited_message and update.edited_message.chat:
                    chat_ids.add(update.edited_message.chat.id)
                elif update.edited_channel_post and update.edited_channel_post.chat:
                    chat_ids.add(update.edited_channel_post.chat.id)
            
            logging.info(f"Found {len(chat_ids)} unique chats in updates")
            
            # Проверяем каждый чат на админские права бота
            for chat_id in chat_ids:
                try:
                    # Пропускаем личные чаты
                    chat = await bot.get_chat(chat_id)
                    if chat.type in ['private', 'group']:
                        continue
                    
                    # Проверяем, что бот админ
                    if await bot_is_admin(bot, chat_id):
                        admin_channels.append({
                            "id": chat_id,
                            "title": chat.title or f"Канал {chat_id}",
                            "existing": False
                        })
                        logging.info(f"Found admin channel: {chat_id} ({chat.title})")
                        
                except Exception as e:
                    logging.debug(f"Could not check chat {chat_id}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error getting admin channels: {e}")
        
        # Также проверяем каналы из конфига
        from app.core.config import settings
        if hasattr(settings, 'KNOWN_CHANNELS') and settings.KNOWN_CHANNELS:
            for channel_id in settings.KNOWN_CHANNELS:
                try:
                    if await bot_is_admin(bot, channel_id):
                        chat = await bot.get_chat(channel_id)
                        # Проверяем, что канал еще не добавлен
                        if not any(ch["id"] == channel_id for ch in admin_channels):
                            admin_channels.append({
                                "id": channel_id,
                                "title": chat.title or f"Канал {channel_id}",
                                "existing": False
                            })
                            logging.info(f"Found config admin channel: {channel_id} ({chat.title})")
                except Exception as e:
                    logging.debug(f"Could not check config channel {channel_id}: {e}")
        
        logging.info(f"Total admin channels found: {len(admin_channels)}")
        return admin_channels
    
