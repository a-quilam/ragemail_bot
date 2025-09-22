"""
Unit тесты для ChannelTracker
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import tempfile
import os
import sys

# Добавляем путь к боту
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

import aiosqlite
from app.infra.db import connect
from app.services.channel_tracker import ChannelTracker
from app.infra.repo.mailboxes_repo import MailboxesRepo

class TestChannelTracker(unittest.IsolatedAsyncioTestCase):
    """Тесты для ChannelTracker"""
    
    async def asyncSetUp(self):
        """Настройка тестовой базы данных"""
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Подключаемся к базе данных
        self.db = await connect(self.temp_db.name)
        
        # Создаем репозитории
        self.mailboxes_repo = MailboxesRepo(self.db)
        
        # Создаем ChannelTracker
        self.tracker = ChannelTracker(self.db)
        
        # Мокаем бота
        self.mock_bot = AsyncMock()
        self.mock_bot.get_chat = AsyncMock()
        self.mock_bot.get_me = AsyncMock()
    
    async def asyncTearDown(self):
        """Очистка после тестов"""
        await self.db.close()
        os.unlink(self.temp_db.name)
    
    async def test_get_user_available_channels_empty(self):
        """Тест получения доступных каналов когда их нет"""
        # Мокаем bot_is_admin чтобы возвращать False
        with patch('app.services.channel_tracker.bot_is_admin', return_value=False):
            channels = await self.tracker.get_user_available_channels(self.mock_bot, 12345)
            self.assertEqual(channels, [])
    
    async def test_get_user_available_channels_with_existing_mailbox(self):
        """Тест получения доступных каналов с существующим ящиком"""
        # Создаем тестовый ящик
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=-1001234567890,
            creator_id=67890  # Другой пользователь
        )
        
        # Мокаем bot_is_admin и get_chat
        with patch('app.services.channel_tracker.bot_is_admin', return_value=True):
            mock_chat = MagicMock()
            mock_chat.title = "Test Channel"
            self.mock_bot.get_chat.return_value = mock_chat
            
            channels = await self.tracker.get_user_available_channels(self.mock_bot, 12345)
            
            # Пользователь 12345 должен видеть канал, так как у него нет ящика в этом канале
            self.assertEqual(len(channels), 1)
            self.assertEqual(channels[0]["id"], -1001234567890)
            self.assertEqual(channels[0]["title"], "Test Channel")
            self.assertTrue(channels[0]["existing"])
    
    async def test_get_user_available_channels_user_already_has_mailbox(self):
        """Тест когда у пользователя уже есть ящик в канале"""
        # Создаем тестовый ящик для пользователя 12345
        mailbox_id = await self.mailboxes_repo.create(
            title="User Mailbox",
            channel_id=-1001234567890,
            creator_id=12345  # Тот же пользователь
        )
        
        # Мокаем bot_is_admin и get_chat
        with patch('app.services.channel_tracker.bot_is_admin', return_value=True):
            mock_chat = MagicMock()
            mock_chat.title = "Test Channel"
            self.mock_bot.get_chat.return_value = mock_chat
            
            channels = await self.tracker.get_user_available_channels(self.mock_bot, 12345)
            
            # Пользователь не должен видеть канал, так как у него уже есть ящик
            self.assertEqual(len(channels), 0)
    
    async def test_get_user_available_channels_bot_not_admin(self):
        """Тест когда бот не админ в канале"""
        # Создаем тестовый ящик
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=-1001234567890,
            creator_id=67890
        )
        
        # Мокаем bot_is_admin чтобы возвращать False
        with patch('app.services.channel_tracker.bot_is_admin', return_value=False):
            channels = await self.tracker.get_user_available_channels(self.mock_bot, 12345)
            
            # Канал не должен быть доступен, так как бот не админ
            self.assertEqual(len(channels), 0)
    
    async def test_get_user_available_channels_error_handling(self):
        """Тест обработки ошибок"""
        # Создаем тестовый ящик
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=-1001234567890,
            creator_id=67890
        )
        
        # Мокаем bot_is_admin чтобы вызывать исключение
        with patch('app.services.channel_tracker.bot_is_admin', side_effect=Exception("API Error")):
            channels = await self.tracker.get_user_available_channels(self.mock_bot, 12345)
            
            # Должен вернуться пустой список при ошибке
            self.assertEqual(channels, [])
    
    async def test_track_channel_addition_success(self):
        """Тест успешного отслеживания добавления бота в канал"""
        channel_id = -1001234567890
        user_id = 12345
        
        # Мокаем bot_is_admin и get_chat
        with patch('app.services.channel_tracker.bot_is_admin', return_value=True):
            mock_chat = MagicMock()
            mock_chat.title = "New Channel"
            self.mock_bot.get_chat.return_value = mock_chat
            
            # Вызываем функцию
            await self.tracker.track_channel_addition(self.mock_bot, channel_id, user_id)
            
            # Проверяем, что функции были вызваны
            self.mock_bot.get_chat.assert_called_once_with(channel_id)
    
    async def test_track_channel_addition_bot_not_admin(self):
        """Тест когда бот не админ в канале"""
        channel_id = -1001234567890
        user_id = 12345
        
        # Мокаем bot_is_admin чтобы возвращать False
        with patch('app.services.channel_tracker.bot_is_admin', return_value=False):
            # Вызываем функцию
            await self.tracker.track_channel_addition(self.mock_bot, channel_id, user_id)
            
            # get_chat не должен быть вызван
            self.mock_bot.get_chat.assert_not_called()
    
    async def test_track_channel_addition_error_handling(self):
        """Тест обработки ошибок при отслеживании"""
        channel_id = -1001234567890
        user_id = 12345
        
        # Мокаем bot_is_admin чтобы вызывать исключение
        with patch('app.services.channel_tracker.bot_is_admin', side_effect=Exception("API Error")):
            # Функция не должна вызывать исключение
            await self.tracker.track_channel_addition(self.mock_bot, channel_id, user_id)

if __name__ == '__main__':
    unittest.main()
