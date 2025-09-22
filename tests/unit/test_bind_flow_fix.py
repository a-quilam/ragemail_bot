"""
Тест для проверки исправления проблемы "Ящик не настроен" для неадминов
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.types import User, Message

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../bot'))

from app.features.bind.start_payload import cmd_start_payload
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo


class TestBindFlowFix(unittest.IsolatedAsyncioTestCase):
    """Тест исправления привязки ящика для неадминов"""

    async def asyncSetUp(self):
        """Настройка тестового окружения"""
        self.db = AsyncMock()
        self.bot = AsyncMock()
        
        # Мокаем репозитории
        self.users_repo = AsyncMock(spec=UsersRepo)
        self.mailboxes_repo = AsyncMock(spec=MailboxesRepo)
        
        # Мокаем пользователя
        self.user = User(
            id=12345,
            is_bot=False,
            first_name="Test",
            username="testuser"
        )
        
        # Мокаем сообщение
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.user
        self.message.text = "/start 1"
        self.message.answer = AsyncMock()

    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    async def test_user_creation_on_deeplink(self, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class):
        """Тест создания пользователя при переходе по deeplink"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = True
        
        # Мокаем mailbox
        mock_mailbox = (1, "Test Mailbox", -1001234567890, 12345, None, None)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем users repo
        mock_users_repo = AsyncMock()
        mock_users_repo.get.return_value = None  # Пользователь не существует
        mock_users_repo.get_role.return_value = "user"
        mock_users_repo_class.return_value = mock_users_repo
        
        # Выполняем тест
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь был создан
        mock_users_repo.upsert.assert_called_once_with(12345, username="testuser")
        
        # Проверяем, что активный ящик был установлен
        mock_users_repo.set_active_mailbox.assert_called_once_with(12345, 1)
        
        # Проверяем, что было отправлено сообщение об успешной привязке
        self.message.answer.assert_called_once()
        call_args = self.message.answer.call_args[0][0]
        self.assertIn("✅ <b>Привязка выполнена!</b>", call_args)

    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    async def test_existing_user_update_on_deeplink(self, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class):
        """Тест обновления существующего пользователя при переходе по deeplink"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = True
        
        # Мокаем mailbox
        mock_mailbox = (1, "Test Mailbox", -1001234567890, 12345, None, None)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем users repo - пользователь уже существует
        mock_users_repo = AsyncMock()
        mock_users_repo.get.return_value = (12345, "user", None, None, "oldusername")
        mock_users_repo.get_role.return_value = "user"
        mock_users_repo_class.return_value = mock_users_repo
        
        # Выполняем тест
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь НЕ был создан заново
        mock_users_repo.upsert.assert_not_called()
        
        # Проверяем, что username был обновлен
        mock_users_repo.update_username.assert_called_once_with(12345, "testuser")
        
        # Проверяем, что активный ящик был установлен
        mock_users_repo.set_active_mailbox.assert_called_once_with(12345, 1)

    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    async def test_user_not_member_of_channel(self, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class):
        """Тест случая, когда пользователь не подписан на канал"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = False  # Пользователь не подписан
        
        # Мокаем mailbox
        mock_mailbox = (1, "Test Mailbox", -1001234567890, 12345, None, None)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем users repo
        mock_users_repo = AsyncMock()
        mock_users_repo_class.return_value = mock_users_repo
        
        # Выполняем тест
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь НЕ был создан
        mock_users_repo.upsert.assert_not_called()
        
        # Проверяем, что активный ящик НЕ был установлен
        mock_users_repo.set_active_mailbox.assert_not_called()
        
        # Проверяем, что было отправлено сообщение об ограничении доступа
        self.message.answer.assert_called_once()
        call_args = self.message.answer.call_args[0][0]
        self.assertIn("❌ <b>Доступ ограничен</b>", call_args)


if __name__ == '__main__':
    unittest.main()
