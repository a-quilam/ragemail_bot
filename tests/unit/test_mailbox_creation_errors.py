"""
Unit тесты для обработки ошибок при создании ящиков
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
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.users_repo import UsersRepo

class TestMailboxCreationErrors(unittest.IsolatedAsyncioTestCase):
    """Тесты для обработки ошибок при создании ящиков"""
    
    async def asyncSetUp(self):
        """Настройка тестовой базы данных"""
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Подключаемся к базе данных
        self.db = await connect(self.temp_db.name)
        
        # Создаем репозитории
        self.mailboxes_repo = MailboxesRepo(self.db)
        self.users_repo = UsersRepo(self.db)
    
    async def asyncTearDown(self):
        """Очистка после тестов"""
        await self.db.close()
        os.unlink(self.temp_db.name)
    
    async def test_duplicate_channel_creation(self):
        """Тест создания ящика в уже используемом канале"""
        channel_id = -1001234567890
        user_id = 12345
        
        # Создаем первый ящик
        mailbox_id1 = await self.mailboxes_repo.create(
            title="First Mailbox",
            channel_id=channel_id,
            creator_id=user_id
        )
        
        # Пытаемся создать второй ящик в том же канале
        # Это должно вызвать исключение из-за UNIQUE constraint
        with self.assertRaises(Exception):
            await self.mailboxes_repo.create(
                title="Second Mailbox",
                channel_id=channel_id,
                creator_id=67890
            )
    
    async def test_invalid_channel_id_validation(self):
        """Тест валидации неверного ID канала"""
        from app.validators.db_validators import validate_before_insert
        
        # Тестируем положительный ID канала (неверный)
        invalid_data = {
            "title": "Test Mailbox",
            "channel_id": 12345  # Положительный ID
        }
        
        result = validate_before_insert("mailboxes", invalid_data)
        self.assertFalse(result.is_valid)
        self.assertIn("channel_id должен быть отрицательным числом", result.errors)
    
    async def test_invalid_title_validation(self):
        """Тест валидации неверного названия ящика"""
        from app.validators.db_validators import validate_before_insert
        
        # Тестируем слишком короткое название
        invalid_data = {
            "title": "ab",  # Слишком короткий
            "channel_id": -1001234567890
        }
        
        result = validate_before_insert("mailboxes", invalid_data)
        self.assertFalse(result.is_valid)
        self.assertIn("title должен содержать минимум", result.errors)
    
    async def test_empty_title_validation(self):
        """Тест валидации пустого названия"""
        from app.validators.db_validators import validate_before_insert
        
        # Тестируем пустое название
        invalid_data = {
            "title": "",  # Пустое
            "channel_id": -1001234567890
        }
        
        result = validate_before_insert("mailboxes", invalid_data)
        self.assertFalse(result.is_valid)
        self.assertIn("title не может быть пустым", result.errors)
    
    async def test_get_by_channel_id_nonexistent(self):
        """Тест получения ящика по несуществующему ID канала"""
        channel_id = -1009999999999
        
        result = await self.mailboxes_repo.get_by_channel_id(channel_id)
        self.assertIsNone(result)
    
    async def test_get_by_channel_id_existing(self):
        """Тест получения ящика по существующему ID канала"""
        channel_id = -1001234567890
        user_id = 12345
        
        # Создаем ящик
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=channel_id,
            creator_id=user_id
        )
        
        # Получаем ящик по ID канала
        result = await self.mailboxes_repo.get_by_channel_id(channel_id)
        self.assertEqual(result, mailbox_id)
    
    async def test_mailbox_creation_with_invalid_data_types(self):
        """Тест создания ящика с неверными типами данных"""
        # Тестируем передачу строки вместо числа для channel_id
        with self.assertRaises(Exception):
            await self.mailboxes_repo.create(
                title="Test Mailbox",
                channel_id="not_a_number",  # Неверный тип
                creator_id=12345
            )
    
    async def test_mailbox_creation_with_none_values(self):
        """Тест создания ящика с None значениями"""
        # Тестируем передачу None для обязательных полей
        with self.assertRaises(Exception):
            await self.mailboxes_repo.create(
                title=None,  # None значение
                channel_id=-1001234567890,
                creator_id=12345
            )

if __name__ == '__main__':
    unittest.main()
