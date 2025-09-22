"""
Тест полного flow deeplink для проверки работы привязки ящиков
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.types import User, Message

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../bot'))

from app.features.bind.start_payload import cmd_start_payload
from app.features.admin.cmd_postpin import cmd_postpin, on_postpin_text
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo


class TestDeeplinkFlow(unittest.IsolatedAsyncioTestCase):
    """Тест полного flow deeplink"""

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
        self.message.answer = AsyncMock()
        self.message.bot = self.bot

    @patch('app.features.admin.cmd_postpin.can_manage_mailbox')
    @patch('app.infra.repo.mailboxes_repo.MailboxesRepo')
    async def test_deeplink_creation_flow(self, mock_mailboxes_repo_class, mock_can_manage_mailbox):
        """Тест создания deeplink поста"""
        
        # Настраиваем моки
        mock_can_manage_mailbox.return_value = True
        
        # Мокаем mailbox
        mock_mailbox = (1, "Test Mailbox", -1001234567890, 12345, None, None)
        mock_mailboxes_repo = AsyncMock()
        mock_mailboxes_repo.get.return_value = mock_mailbox
        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
        
        # Мокаем бота
        mock_me = MagicMock()
        mock_me.username = "testbot"
        self.bot.get_me.return_value = mock_me
        self.bot.send_message = AsyncMock()
        self.bot.pin_chat_message = AsyncMock()
        
        # Тестируем создание deeplink поста
        self.message.text = "📌 Закрепить пост"
        active_mailbox_id = 1
        
        # Шаг 1: Админ нажимает "Закрепить пост"
        await cmd_postpin(self.message, active_mailbox_id, self.db)
        
        # Проверяем, что админ получил инструкцию
        self.message.answer.assert_called_with("Пришлите текст закрепа. Я добавлю deeplink и закреплю в канале.")
        
        # Шаг 2: Админ отправляет текст
        self.message.text = "Добро пожаловать в наш анонимный ящик!"
        await on_postpin_text(self.message, self.db)
        
        # Проверяем, что пост был отправлен в канал
        self.bot.send_message.assert_called_once()
        call_args = self.bot.send_message.call_args
        
        # Проверяем параметры вызова
        self.assertEqual(call_args[0][0], -1001234567890)  # channel_id (первый позиционный аргумент)
        self.assertEqual(call_args[0][1], "Добро пожаловать в наш анонимный ящик!")  # text (второй позиционный аргумент)
        self.assertTrue(call_args[1]['disable_web_page_preview'])
        
        # Проверяем, что была создана кнопка с deeplink
        reply_markup = call_args[1]['reply_markup']
        self.assertIsNotNone(reply_markup)
        self.assertEqual(len(reply_markup.inline_keyboard), 1)
        self.assertEqual(len(reply_markup.inline_keyboard[0]), 1)
        
        button = reply_markup.inline_keyboard[0][0]
        self.assertEqual(button.text, "✍️ Написать")
        self.assertEqual(button.url, "https://t.me/testbot?start=1")
        
        # Проверяем, что пост был закреплен
        self.bot.pin_chat_message.assert_called_once()

    @patch('app.features.bind.start_payload.UsersRepo')
    @patch('app.features.bind.start_payload.MailboxesRepo')
    @patch('app.features.bind.start_payload.user_is_member')
    @patch('app.utils.mailbox_permissions.can_manage_mailbox')
    async def test_deeplink_usage_flow(self, mock_can_manage_mailbox, mock_user_is_member, mock_mailboxes_repo_class, mock_users_repo_class):
        """Тест использования deeplink обычным пользователем"""
        
        # Настраиваем моки
        mock_user_is_member.return_value = True
        mock_can_manage_mailbox.return_value = False  # Обычный пользователь не может управлять ящиком
        
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
        
        # Тестируем переход по deeplink
        self.message.text = "/start 1"
        
        await cmd_start_payload(self.message, self.db, self.bot)
        
        # Проверяем, что пользователь был создан
        mock_users_repo.upsert.assert_called_once_with(12345, username="testuser")
        
        # Проверяем, что активный ящик был установлен
        mock_users_repo.set_active_mailbox.assert_called_once_with(12345, 1)
        
        # Проверяем, что было отправлено сообщение об успешной привязке
        self.message.answer.assert_called_once()
        call_args = self.message.answer.call_args[0][0]
        self.assertIn("✅ <b>Привязка выполнена!</b>", call_args)
        self.assertIn("Теперь вы пишете в этот ящик по умолчанию", call_args)

    async def test_deeplink_format_validation(self):
        """Тест валидации формата deeplink"""
        
        # Тестируем различные форматы deeplink
        test_cases = [
            ("/start 123", True, 123),      # Валидный
            ("/start 0", True, 0),          # Валидный (edge case)
            ("/start abc", False, None),    # Невалидный (не число)
            ("/start", False, None),        # Невалидный (нет payload)
            ("/start 123 456", True, 123),  # Валидный (дополнительные параметры игнорируются)
        ]
        
        for text, should_process, expected_mailbox_id in test_cases:
            with self.subTest(text=text):
                # Сбрасываем моки
                self.message.answer.reset_mock()
                self.message.text = text
                
                # Мокаем репозитории для каждого теста
                with patch('app.features.bind.start_payload.UsersRepo') as mock_users_repo_class, \
                     patch('app.features.bind.start_payload.MailboxesRepo') as mock_mailboxes_repo_class, \
                     patch('app.features.bind.start_payload.user_is_member') as mock_user_is_member, \
                     patch('app.utils.mailbox_permissions.can_manage_mailbox') as mock_can_manage_mailbox:
                    
                    if should_process:
                        # Настраиваем моки для успешной обработки
                        mock_user_is_member.return_value = True
                        mock_can_manage_mailbox.return_value = False  # Обычный пользователь
                        mock_mailbox = (expected_mailbox_id, "Test Mailbox", -1001234567890, 12345, None, None)
                        mock_mailboxes_repo = AsyncMock()
                        mock_mailboxes_repo.get.return_value = mock_mailbox
                        mock_mailboxes_repo_class.return_value = mock_mailboxes_repo
                        
                        mock_users_repo = AsyncMock()
                        mock_users_repo.get.return_value = None
                        mock_users_repo.get_role.return_value = "user"
                        mock_users_repo_class.return_value = mock_users_repo
                        
                        await cmd_start_payload(self.message, self.db, self.bot)
                        
                        # Проверяем, что сообщение было отправлено
                        self.message.answer.assert_called()
                    else:
                        # Для невалидных случаев не должно быть вызовов
                        await cmd_start_payload(self.message, self.db, self.bot)
                        
                        # Проверяем, что сообщение НЕ было отправлено
                        self.message.answer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
