"""
Тест безопасности deeplink - проверяем, что админы не могут управлять чужими ящиками
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.types import User, Message

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../bot'))

from app.features.bind.start_payload import cmd_start_payload


class TestDeeplinkSecurity(unittest.IsolatedAsyncioTestCase):
    """Тест безопасности deeplink"""

    async def asyncSetUp(self):
        """Настройка тестового окружения"""
        self.db = AsyncMock()
        self.bot = AsyncMock()
        
        # Мокаем пользователя-админа
        self.admin_user = User(
            id=12345,
            is_bot=False,
            first_name="Admin",
            username="admin"
        )
        
        # Мокаем сообщение
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.admin_user
        self.message.answer = AsyncMock()
        self.message.bot = self.bot

    @patch('app.utils.mailbox_permissions.can_manage_mailbox')
    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    async def test_admin_cannot_manage_foreign_mailbox(self, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class, mock_can_manage_mailbox):
        """Тест: админ не может управлять чужим ящиком через deeplink"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = True
        mock_can_manage_mailbox.return_value = False  # Админ НЕ может управлять этим ящиком
        
        # Мокаем mailbox (чужой ящик)
        mock_mailbox = (1, "Foreign Mailbox", -1001234567890, 99999, None, 99999)  # creator_id = 99999 (не наш админ)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем users repo (админ)
        mock_users_repo = AsyncMock()
        mock_users_repo.get.return_value = None
        mock_users_repo.get_role.return_value = "admin"  # Пользователь - админ
        mock_users_repo_class.return_value = mock_users_repo
        
        # Тестируем переход по deeplink
        self.message.text = "/start 1"
        
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь был создан
        mock_users_repo.upsert.assert_called_once_with(12345, username="admin")
        
        # Проверяем, что активный ящик был установлен
        mock_users_repo.set_active_mailbox.assert_called_once_with(12345, 1)
        
        # Проверяем, что было отправлено сообщение для ОБЫЧНОГО пользователя (не админа)
        self.message.answer.assert_called_once()
        call_args = self.message.answer.call_args[0][0]
        
        # Должно быть сообщение для обычного пользователя (без админских кнопок)
        self.assertIn("✅ <b>Привязка выполнена!</b>", call_args)
        self.assertIn("Теперь вы пишете в этот ящик по умолчанию", call_args)
        self.assertIn("Просто напишите ваше анонимное сообщение", call_args)
        
        # НЕ должно быть админских функций
        self.assertNotIn("⚙️ <b>Настройки</b>", call_args)
        self.assertNotIn("📊 <b>Статистика</b>", call_args)
        self.assertNotIn("📌 <b>Закрепить пост</b>", call_args)

    @patch('app.utils.mailbox_permissions.can_manage_mailbox')
    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    async def test_admin_can_manage_own_mailbox(self, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class, mock_can_manage_mailbox):
        """Тест: админ может управлять своим ящиком через deeplink"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = True
        mock_can_manage_mailbox.return_value = True  # Админ МОЖЕТ управлять этим ящиком
        
        # Мокаем mailbox (свой ящик)
        mock_mailbox = (1, "Own Mailbox", -1001234567890, 12345, None, 12345)  # creator_id = 12345 (наш админ)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем users repo (админ)
        mock_users_repo = AsyncMock()
        mock_users_repo.get.return_value = None
        mock_users_repo.get_role.return_value = "admin"  # Пользователь - админ
        mock_users_repo_class.return_value = mock_users_repo
        
        # Тестируем переход по deeplink
        self.message.text = "/start 1"
        
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь был создан
        mock_users_repo.upsert.assert_called_once_with(12345, username="admin")
        
        # Проверяем, что активный ящик был установлен
        mock_users_repo.set_active_mailbox.assert_called_once_with(12345, 1)
        
        # Проверяем, что было отправлено сообщение для АДМИНА
        self.message.answer.assert_called_once()
        call_args = self.message.answer.call_args[0][0]
        
        # Должно быть сообщение для админа (с админскими кнопками)
        self.assertIn("✅ <b>Привязка выполнена!</b>", call_args)
        self.assertIn("Теперь вы пишете в этот ящик по умолчанию", call_args)
        self.assertIn("⚙️ <b>Настройки</b>", call_args)
        self.assertIn("📊 <b>Статистика</b>", call_args)
        self.assertIn("📌 <b>Закрепить пост</b>", call_args)
        self.assertIn("🔄 <b>Обновить</b>", call_args)


if __name__ == '__main__':
    unittest.main()
