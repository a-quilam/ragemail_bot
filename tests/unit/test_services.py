"""
Unit тесты для сервисов
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

# Импорты сервисов
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from app.services.alias_service import AliasService
from app.services.background_tasks import BackgroundTaskService, TaskStatus
from app.services.heavy_operations import bulk_user_operations, generate_statistics_report
from app.core.permissions import PermissionManager, Role, Permission
from app.validators.db_validators import DatabaseValidator, ValidationResult

class TestAliasService(unittest.IsolatedAsyncioTestCase):
    """Тесты для AliasService"""
    
    def setUp(self):
        """Настройка тестов"""
        self.mock_repo = AsyncMock()
        self.mock_words_repo = AsyncMock()
        self.mock_blocks_repo = AsyncMock()
        self.tz = ZoneInfo("UTC")
        
        self.service = AliasService(
            repo=self.mock_repo,
            tz=self.tz,
            words_repo=self.mock_words_repo,
            blocks_repo=self.mock_blocks_repo
        )
    
    async def test_get_or_issue_existing_alias(self):
        """Тест получения существующего псевдонима"""
        # Настраиваем мок
        self.mock_repo.get_for_today.return_value = "🐱 милый котик"
        
        # Выполняем тест
        result = await self.service.get_or_issue(12345)
        
        # Проверяем результат
        self.assertEqual(result, "🐱 милый котик")
        self.mock_repo.get_for_today.assert_called_once_with(12345, self.service._today_key())
    
    async def test_get_or_issue_new_alias(self):
        """Тест создания нового псевдонима"""
        # Настраиваем мок
        self.mock_repo.get_for_today.return_value = None
        self.mock_repo.set_for_today.return_value = None
        self.mock_words_repo.add_used_words.return_value = None
        
        # Мокаем генерацию псевдонима
        with patch.object(self.service, '_rand_alias', return_value="🐶 добрый пёсик"):
            result = await self.service.get_or_issue(12345)
        
        # Проверяем результат
        self.assertEqual(result, "🐶 добрый пёсик")
        self.mock_repo.set_for_today.assert_called_once()
        self.mock_words_repo.add_used_words.assert_called_once_with("🐶 добрый пёсик")
    
    async def test_today_key_format(self):
        """Тест формата ключа дня"""
        today_key = self.service._today_key()
        self.assertRegex(today_key, r'^\d{4}-\d{2}-\d{2}$')

class TestBackgroundTaskService(unittest.IsolatedAsyncioTestCase):
    """Тесты для BackgroundTaskService"""
    
    def setUp(self):
        """Настройка тестов"""
        self.service = BackgroundTaskService(max_concurrent_tasks=2)
    
    async def test_submit_task(self):
        """Тест отправки задачи"""
        # Мокаем функцию
        mock_func = AsyncMock(return_value="test_result")
        
        # Отправляем задачу
        task_id = await self.service.submit_task("test_task", mock_func)
        
        # Проверяем, что задача создана
        self.assertIsNotNone(task_id)
        self.assertIn(task_id, self.service.tasks)
        
        task = self.service.tasks[task_id]
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.status, TaskStatus.PENDING)
    
    async def test_task_execution(self):
        """Тест выполнения задачи"""
        # Мокаем функцию
        mock_func = AsyncMock(return_value="test_result")
        
        # Отправляем задачу
        task_id = await self.service.submit_task("test_task", mock_func)
        
        # Ждем выполнения
        await asyncio.sleep(0.1)
        
        # Проверяем результат
        task = self.service.tasks[task_id]
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.result, "test_result")
    
    async def test_task_failure(self):
        """Тест обработки ошибки в задаче"""
        # Мокаем функцию с ошибкой
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Отправляем задачу
        task_id = await self.service.submit_task("test_task", mock_func)
        
        # Ждем выполнения
        await asyncio.sleep(0.1)
        
        # Проверяем результат
        task = self.service.tasks[task_id]
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertIsNotNone(task.error)
        self.assertEqual(str(task.error), "Test error")
    
    async def test_cancel_task(self):
        """Тест отмены задачи"""
        # Мокаем долгую функцию
        async def long_task():
            await asyncio.sleep(10)
            return "result"
        
        # Отправляем задачу
        task_id = await self.service.submit_task("long_task", long_task)
        
        # Отменяем задачу
        result = await self.service.cancel_task(task_id)
        
        # Проверяем результат
        self.assertTrue(result)
        task = self.service.tasks[task_id]
        self.assertEqual(task.status, TaskStatus.CANCELLED)

class TestHeavyOperations(unittest.IsolatedAsyncioTestCase):
    """Тесты для тяжелых операций"""
    
    async def test_bulk_user_operations(self):
        """Тест массовых операций с пользователями"""
        user_ids = [1, 2, 3, 4, 5]
        progress_calls = []
        
        def progress_callback(task_id, progress, message):
            progress_calls.append((task_id, progress, message))
        
        # Выполняем операцию
        result = await bulk_user_operations(
            user_ids, 
            "test_operation", 
            progress_callback=progress_callback
        )
        
        # Проверяем результат
        self.assertEqual(result["total_users"], 5)
        self.assertEqual(result["processed"], 5)
        self.assertEqual(result["success_rate"], 100.0)
        self.assertEqual(len(result["errors"]), 0)
        
        # Проверяем вызовы progress callback
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(progress_calls[-1][1], 100.0)  # Последний вызов должен быть 100%
    
    async def test_generate_statistics_report(self):
        """Тест генерации отчета статистики"""
        progress_calls = []
        
        def progress_callback(task_id, progress, message):
            progress_calls.append((task_id, progress, message))
        
        # Выполняем операцию
        result = await generate_statistics_report(
            days=30,
            progress_callback=progress_callback
        )
        
        # Проверяем результат
        self.assertEqual(result["period_days"], 30)
        self.assertIn("total_users", result)
        self.assertIn("active_users", result)
        self.assertIn("generated_at", result)
        
        # Проверяем вызовы progress callback
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(progress_calls[-1][1], 100.0)

class TestPermissionManager(unittest.TestCase):
    """Тесты для PermissionManager"""
    
    def test_role_permissions(self):
        """Тест разрешений ролей"""
        # Проверяем разрешения пользователя
        self.assertFalse(PermissionManager.has_permission(Role.USER, Permission.MANAGE_USERS))
        self.assertTrue(PermissionManager.has_permission(Role.USER, Permission.CREATE_MAILBOX))
        
        # Проверяем разрешения администратора
        self.assertTrue(PermissionManager.has_permission(Role.ADMIN, Permission.MANAGE_USERS))
        self.assertTrue(PermissionManager.has_permission(Role.ADMIN, Permission.ADD_ADMIN))
        
        # Проверяем разрешения суперадмина
        self.assertTrue(PermissionManager.has_permission(Role.SUPERADMIN, Permission.SYSTEM_SETTINGS))
        self.assertTrue(PermissionManager.has_permission(Role.SUPERADMIN, Permission.TRANSFER_ADMIN))
    
    def test_mailbox_access(self):
        """Тест доступа к ящикам"""
        from app.core.permissions import AccessContext
        
        # Обычный пользователь - создатель ящика
        context = AccessContext(
            user_id=1,
            user_role=Role.USER,
            is_mailbox_creator=True
        )
        self.assertTrue(PermissionManager.can_access_mailbox(context))
        
        # Обычный пользователь - не создатель ящика
        context.is_mailbox_creator = False
        self.assertFalse(PermissionManager.can_access_mailbox(context))
        
        # Администратор
        context.user_role = Role.ADMIN
        self.assertTrue(PermissionManager.can_access_mailbox(context))
        
        # Суперадмин
        context.user_role = Role.SUPERADMIN
        self.assertTrue(PermissionManager.can_access_mailbox(context))

class TestDatabaseValidator(unittest.TestCase):
    """Тесты для DatabaseValidator"""
    
    def setUp(self):
        """Настройка тестов"""
        self.validator = DatabaseValidator()
    
    def test_user_validation(self):
        """Тест валидации данных пользователя"""
        # Валидные данные
        valid_data = {
            "user_id": 12345,
            "role": "user",
            "username": "test_user"
        }
        result = self.validator.validate_user_data(valid_data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Невалидные данные
        invalid_data = {
            "user_id": "not_a_number",
            "role": "invalid_role",
            "username": "ab"  # Слишком короткий
        }
        result = self.validator.validate_user_data(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_mailbox_validation(self):
        """Тест валидации данных ящика"""
        # Валидные данные
        valid_data = {
            "title": "Test Mailbox",
            "channel_id": -1001234567890
        }
        result = self.validator.validate_mailbox_data(valid_data)
        self.assertTrue(result.is_valid)
        
        # Невалидные данные
        invalid_data = {
            "title": "ab",  # Слишком короткий
            "channel_id": 12345  # Положительный ID
        }
        result = self.validator.validate_mailbox_data(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_post_validation(self):
        """Тест валидации данных поста"""
        # Валидные данные
        valid_data = {
            "text": "Test message",
            "alias": "🐱 милый котик",
            "ttl": 3600
        }
        result = self.validator.validate_post_data(valid_data)
        self.assertTrue(result.is_valid)
        
        # Невалидные данные
        invalid_data = {
            "text": "x" * 2001,  # Слишком длинный
            "alias": "",
            "ttl": 30  # Слишком короткий
        }
        result = self.validator.validate_post_data(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

if __name__ == '__main__':
    unittest.main()
