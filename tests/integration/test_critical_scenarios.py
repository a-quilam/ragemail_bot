"""
Интеграционные тесты для критических сценариев
"""
import unittest
import asyncio
import tempfile
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Добавляем путь к боту
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

import aiosqlite
from app.infra.db import connect
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.stats_repo import StatsRepo
from app.services.alias_service import AliasService
from app.services.post_service import PostService
from app.services.relay_service import RelayService
from app.utils.backup import BackupManager
from app.core.permissions import PermissionManager, Role
from app.validators.db_validators import validate_before_insert

class TestCriticalScenarios(unittest.IsolatedAsyncioTestCase):
    """Интеграционные тесты критических сценариев"""
    
    async def asyncSetUp(self):
        """Настройка тестовой базы данных"""
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Подключаемся к базе данных
        self.db = await connect(self.temp_db.name)
        
        # Создаем репозитории
        self.users_repo = UsersRepo(self.db)
        self.mailboxes_repo = MailboxesRepo(self.db)
        self.posts_repo = PostsRepo(self.db)
        self.stats_repo = StatsRepo(self.db)
        
        # Создаем сервисы
        self.tz = ZoneInfo("UTC")
        self.alias_service = AliasService(self.users_repo, self.tz)
        
        # Мокаем бота для PostService
        self.mock_bot = AsyncMock()
        self.post_service = PostService(self.mock_bot, self.tz, self.posts_repo, AsyncMock())
        
        # Мокаем бота для RelayService
        self.relay_service = RelayService(self.mock_bot, self.tz, AsyncMock())
    
    async def asyncTearDown(self):
        """Очистка после тестов"""
        await self.db.close()
        os.unlink(self.temp_db.name)
    
    async def test_user_registration_flow(self):
        """Тест полного потока регистрации пользователя"""
        user_id = 12345
        username = "test_user"
        
        # 1. Регистрация пользователя
        await self.users_repo.upsert(user_id, role="user", username=username)
        
        # 2. Проверяем, что пользователь создан
        user = await self.users_repo.get(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user[0], user_id)
        self.assertEqual(user[1], "user")
        self.assertEqual(user[4], username)
        
        # 3. Создаем ящик для пользователя
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=-1001234567890,
            creator_id=user_id
        )
        
        # 4. Устанавливаем активный ящик
        await self.users_repo.set_active_mailbox(user_id, mailbox_id)
        
        # 5. Проверяем, что ящик создан и назначен
        active_mailbox = await self.users_repo.get_active_mailbox(user_id)
        self.assertEqual(active_mailbox, mailbox_id)
        
        # 6. Проверяем права доступа
        is_creator = await self.mailboxes_repo.is_creator(mailbox_id, user_id)
        self.assertTrue(is_creator)
    
    async def test_post_creation_and_management(self):
        """Тест создания и управления постами"""
        user_id = 12345
        channel_id = -1001234567890
        
        # 1. Создаем пользователя и ящик
        await self.users_repo.upsert(user_id, role="user")
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=channel_id,
            creator_id=user_id
        )
        
        # 2. Создаем пост
        alias = "🐱 милый котик"
        text = "Тестовое сообщение"
        base_delete_at = int((datetime.now() + timedelta(hours=1)).timestamp())
        delete_at = base_delete_at
        
        await self.posts_repo.add(
            chat_id=channel_id,
            message_id=1,
            author_id=user_id,
            alias=alias,
            base_text=text,
            base_delete_at=base_delete_at,
            delete_at=delete_at
        )
        
        # 3. Проверяем, что пост создан
        post = await self.posts_repo.get(channel_id, 1)
        self.assertIsNotNone(post)
        self.assertEqual(post[2], user_id)
        self.assertEqual(post[3], alias)
        self.assertEqual(post[4], text)
        
        # 4. Обновляем время удаления
        new_delete_at = int((datetime.now() + timedelta(hours=2)).timestamp())
        await self.posts_repo.set_delete_at(channel_id, 1, new_delete_at)
        
        # 5. Проверяем обновление
        updated_post = await self.posts_repo.get(channel_id, 1)
        self.assertEqual(updated_post[6], new_delete_at)
        
        # 6. Удаляем пост
        await self.posts_repo.delete(channel_id, 1)
        
        # 7. Проверяем, что пост удален
        deleted_post = await self.posts_repo.get(channel_id, 1)
        self.assertIsNone(deleted_post)
    
    async def test_alias_generation_and_caching(self):
        """Тест генерации псевдонимов и кэширования"""
        user_id = 12345
        
        # 1. Создаем пользователя
        await self.users_repo.upsert(user_id, role="user")
        
        # 2. Генерируем псевдоним
        alias1 = await self.alias_service.get_or_issue(user_id)
        self.assertIsNotNone(alias1)
        self.assertIsInstance(alias1, str)
        self.assertGreater(len(alias1), 0)
        
        # 3. Получаем тот же псевдоним (должен быть кэширован)
        alias2 = await self.alias_service.get_or_issue(user_id)
        self.assertEqual(alias1, alias2)
        
        # 4. Проверяем, что псевдоним сохранен в БД
        day = self.alias_service._today_key()
        saved_alias = await self.alias_service.repo.get_for_today(user_id, day)
        self.assertEqual(saved_alias, alias1)
    
    async def test_statistics_collection(self):
        """Тест сбора статистики"""
        # 1. Добавляем статистику
        await self.stats_repo.inc("2024-01-01", "posts_created")
        await self.stats_repo.inc("2024-01-01", "posts_created")
        await self.stats_repo.inc("2024-01-01", "users_registered")
        await self.stats_repo.inc("2024-01-02", "posts_created")
        
        # 2. Получаем статистику за период
        stats = await self.stats_repo.last_7_days("2024-01-01")
        self.assertGreater(len(stats), 0)
        
        # 3. Проверяем агрегированную статистику
        aggregated = await self.stats_repo.get_aggregated_stats("2024-01-01", "day")
        self.assertIn("2024-01-01", aggregated)
        self.assertIn("2024-01-02", aggregated)
        
        # 4. Проверяем топ ключей
        top_keys = await self.stats_repo.get_top_keys("2024-01-01", limit=5)
        self.assertGreater(len(top_keys), 0)
        # posts_created должен быть на первом месте (2 записи)
        self.assertEqual(top_keys[0][0], "posts_created")
        self.assertEqual(top_keys[0][1], 3)  # 2 + 1 = 3
    
    async def test_backup_and_restore(self):
        """Тест резервного копирования и восстановления"""
        # 1. Создаем тестовые данные
        await self.users_repo.upsert(12345, role="admin", username="admin")
        await self.users_repo.upsert(67890, role="user", username="user")
        
        mailbox_id = await self.mailboxes_repo.create(
            title="Test Mailbox",
            channel_id=-1001234567890,
            creator_id=12345
        )
        
        # 2. Создаем бэкап
        backup_manager = BackupManager(self.db)
        backup_data = await backup_manager.export_data()
        
        # 3. Проверяем структуру бэкапа
        self.assertIn("users", backup_data)
        self.assertIn("mailboxes", backup_data)
        self.assertIn("checksum", backup_data)
        
        # 4. Проверяем целостность
        is_valid = backup_manager.verify_backup_integrity(backup_data)
        self.assertTrue(is_valid)
        
        # 5. Проверяем структуру
        structure_errors = backup_manager.validate_backup_structure(backup_data)
        self.assertEqual(len(structure_errors), 0)
    
    async def test_permission_system(self):
        """Тест системы разрешений"""
        from app.core.permissions import AccessContext
        
        # 1. Тестируем разрешения для разных ролей
        user_context = AccessContext(user_id=1, user_role=Role.USER)
        admin_context = AccessContext(user_id=2, user_role=Role.ADMIN)
        superadmin_context = AccessContext(user_id=3, user_role=Role.SUPERADMIN)
        
        # 2. Проверяем базовые разрешения
        self.assertFalse(PermissionManager.has_permission(Role.USER, Permission.MANAGE_USERS))
        self.assertTrue(PermissionManager.has_permission(Role.ADMIN, Permission.MANAGE_USERS))
        self.assertTrue(PermissionManager.has_permission(Role.SUPERADMIN, Permission.SYSTEM_SETTINGS))
        
        # 3. Проверяем доступ к ящикам
        user_context.is_mailbox_creator = True
        self.assertTrue(PermissionManager.can_access_mailbox(user_context))
        
        user_context.is_mailbox_creator = False
        self.assertFalse(PermissionManager.can_access_mailbox(user_context))
        
        self.assertTrue(PermissionManager.can_access_mailbox(admin_context))
        self.assertTrue(PermissionManager.can_access_mailbox(superadmin_context))
    
    async def test_data_validation(self):
        """Тест валидации данных"""
        # 1. Валидные данные пользователя
        valid_user_data = {
            "user_id": 12345,
            "role": "user",
            "username": "valid_user"
        }
        result = validate_before_insert("users", valid_user_data)
        self.assertTrue(result.is_valid)
        
        # 2. Невалидные данные пользователя
        invalid_user_data = {
            "user_id": "not_a_number",
            "role": "invalid_role",
            "username": "ab"  # Слишком короткий
        }
        result = validate_before_insert("users", invalid_user_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        
        # 3. Валидные данные ящика
        valid_mailbox_data = {
            "title": "Valid Mailbox",
            "channel_id": -1001234567890
        }
        result = validate_before_insert("mailboxes", valid_mailbox_data)
        self.assertTrue(result.is_valid)
        
        # 4. Невалидные данные ящика
        invalid_mailbox_data = {
            "title": "ab",  # Слишком короткий
            "channel_id": 12345  # Положительный ID
        }
        result = validate_before_insert("mailboxes", invalid_mailbox_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    async def test_concurrent_operations(self):
        """Тест конкурентных операций"""
        # 1. Создаем несколько пользователей одновременно
        user_ids = [1001, 1002, 1003, 1004, 1005]
        
        async def create_user(user_id):
            await self.users_repo.upsert(user_id, role="user", username=f"user_{user_id}")
            return user_id
        
        # 2. Выполняем операции параллельно
        tasks = [create_user(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks)
        
        # 3. Проверяем результаты
        self.assertEqual(len(results), len(user_ids))
        
        # 4. Проверяем, что все пользователи созданы
        for user_id in user_ids:
            user = await self.users_repo.get(user_id)
            self.assertIsNotNone(user)
            self.assertEqual(user[0], user_id)
    
    async def test_error_handling_and_recovery(self):
        """Тест обработки ошибок и восстановления"""
        # 1. Тестируем обработку невалидных данных
        try:
            await self.users_repo.upsert("invalid_id", role="user")
            self.fail("Should have raised an exception")
        except Exception:
            # Ожидаем ошибку
            pass
        
        # 2. Тестируем восстановление после ошибки
        # Создаем валидного пользователя после ошибки
        await self.users_repo.upsert(99999, role="user", username="recovery_user")
        
        user = await self.users_repo.get(99999)
        self.assertIsNotNone(user)
        self.assertEqual(user[0], 99999)
        
        # 3. Тестируем транзакционность
        try:
            # Начинаем транзакцию
            await self.db.execute("BEGIN TRANSACTION")
            
            # Создаем пользователя
            await self.users_repo.upsert(88888, role="user", username="transaction_user")
            
            # Имитируем ошибку
            raise Exception("Simulated error")
            
        except Exception:
            # Откатываем транзакцию
            await self.db.rollback()
        
        # Проверяем, что пользователь не создан
        user = await self.users_repo.get(88888)
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()
