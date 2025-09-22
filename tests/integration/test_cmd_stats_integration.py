"""
Интеграционные тесты для cmd_stats.py
"""
import pytest
import asyncio
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types

from app.features.admin.cmd_stats import cmd_stats, ErrorCodes, Metrics
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.stats_repo import StatsRepo


class TestCmdStatsIntegration:
    """Интеграционные тесты для команды статистики"""
    
    @pytest.fixture
    async def db_connection(self):
        """Создание тестовой базы данных"""
        db = await aiosqlite.connect(":memory:")
        
        # Создаем таблицы
        await db.execute("""
            CREATE TABLE mailboxes (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                channel_id TEXT UNIQUE,
                creator_id INTEGER,
                stats_day INTEGER DEFAULT 1,
                stats_time TEXT DEFAULT '09:00'
            )
        """)
        
        await db.execute("""
            CREATE TABLE stats (
                day INTEGER,
                key TEXT,
                count INTEGER DEFAULT 0,
                mailbox_id INTEGER,
                PRIMARY KEY (day, key, mailbox_id)
            )
        """)
        
        # Добавляем тестовые данные
        await db.execute("""
            INSERT INTO mailboxes (id, title, channel_id, creator_id, stats_day, stats_time) 
            VALUES (1, 'Test Mailbox', '@test_channel', 1, 1, '09:00')
        """)
        
        await db.execute("""
            INSERT INTO stats (day, key, count, mailbox_id) 
            VALUES (1, 'posts', 10, 1), (1, 'users', 5, 1)
        """)
        
        await db.commit()
        yield db
        await db.close()
    
    @pytest.fixture
    def mock_message(self):
        """Создание мок-объекта сообщения"""
        message = MagicMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 1
        message.from_user.username = "admin_user"
        message.answer = AsyncMock()
        return message
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_success(self, db_connection, mock_message):
        """Тест успешного выполнения команды статистики"""
        # Мокаем rate limiter
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Мокаем circuit breaker
            with patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
                
                # Мокаем can_manage_mailbox
                with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
                    mock_permissions.return_value = True
                    
                    # Выполняем функцию
                    await cmd_stats(mock_message, db_connection, 1)
                    
                    # Проверяем, что сообщение было отправлено
                    mock_message.answer.assert_called_once()
                    
                    # Проверяем, что ответ содержит статистику
                    call_args = mock_message.answer.call_args[0][0]
                    assert "📊" in call_args or "статистика" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_no_permissions(self, db_connection, mock_message):
        """Тест выполнения команды без прав доступа"""
        # Мокаем rate limiter
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Мокаем circuit breaker
            with patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
                
                # Мокаем can_manage_mailbox для возврата False
                with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
                    mock_permissions.return_value = False
                    
                    # Выполняем функцию
                    await cmd_stats(mock_message, db_connection, 1)
                    
                    # Проверяем, что сообщение об ошибке было отправлено
                    mock_message.answer.assert_called_once()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "доступ" in call_args.lower() or "permission" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_rate_limit(self, db_connection, mock_message):
        """Тест rate limiting для команды статистики"""
        # Настраиваем rate limiter для отклонения запроса
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(False, "Rate limit exceeded"))
            
            # Выполняем функцию
            await cmd_stats(mock_message, db_connection, 1)
            
            # Проверяем, что сообщение об ошибке было отправлено
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "превышен лимит" in call_args.lower() or "rate limit" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_circuit_breaker(self, db_connection, mock_message):
        """Тест circuit breaker для команды статистики"""
        # Мокаем rate limiter
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Настраиваем circuit breaker для генерации ошибки
            with patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(side_effect=Exception("Database unavailable"))
                
                # Выполняем функцию
                await cmd_stats(mock_message, db_connection, 1)
                
                # Проверяем, что функция обработала ошибку gracefully
                mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_empty_stats(self, db_connection, mock_message):
        """Тест команды статистики с пустыми данными"""
        # Мокаем все зависимости
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter, \
             patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker, \
             patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
            
            mock_permissions.return_value = True
            
            # Мокаем StatsRepo для возврата пустых данных
            with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_stats_for_mailbox.return_value = {}
                mock_stats_repo.return_value = mock_repo_instance
                
                # Выполняем функцию
                await cmd_stats(mock_message, db_connection, 1)
                
                # Проверяем, что сообщение было отправлено
                mock_message.answer.assert_called_once()
                
                # Проверяем, что ответ содержит информацию о пустой статистике
                call_args = mock_message.answer.call_args[0][0]
                assert "пуста" in call_args.lower() or "empty" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_input_sanitization(self, db_connection, mock_message):
        """Тест санитизации входных данных"""
        # Мокаем все зависимости
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter, \
             patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker, \
             patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
            
            mock_permissions.return_value = True
            
            # Мокаем InputSanitizer
            with patch('app.features.admin.cmd_stats.InputSanitizer') as mock_sanitizer:
                mock_sanitizer.sanitize_user_input.return_value = "sanitized_input"
                
                # Выполняем функцию
                await cmd_stats(mock_message, db_connection, 1)
                
                # Проверяем, что санитизация была вызвана
                mock_sanitizer.sanitize_user_input.assert_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_output_validation(self, db_connection, mock_message):
        """Тест валидации выходных данных"""
        # Мокаем все зависимости
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter, \
             patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker, \
             patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
            
            mock_permissions.return_value = True
            
            # Мокаем OutputValidator
            with patch('app.features.admin.cmd_stats.OutputValidator') as mock_validator:
                mock_validation = MagicMock()
                mock_validation.is_valid = True
                mock_validation.sanitized_data = "validated_output"
                mock_validation.warnings = []
                mock_validator.validate_message_text.return_value = mock_validation
                
                # Выполняем функцию
                await cmd_stats(mock_message, db_connection, 1)
                
                # Проверяем, что валидация была вызвана
                mock_validator.validate_message_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_metrics_tracking(self, db_connection, mock_message):
        """Тест отслеживания метрик"""
        # Мокаем все зависимости
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter, \
             patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker, \
             patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
            
            mock_permissions.return_value = True
            
            # Мокаем логирование для проверки вызовов метрик
            with patch('app.features.admin.cmd_stats.logging') as mock_logging:
                # Выполняем функцию
                await cmd_stats(mock_message, db_connection, 1)
                
                # Проверяем, что метрики были записаны в лог
                assert mock_logging.info.called
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_resource_cleanup(self, db_connection, mock_message):
        """Тест очистки ресурсов"""
        # Мокаем все зависимости
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter, \
             patch('app.features.admin.cmd_stats.get_breaker') as mock_breaker, \
             patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_permissions, \
             patch('app.features.admin.cmd_stats.MemoryManager') as mock_memory:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=("Test Mailbox", "@test_channel", 1, "09:00"))
            
            mock_permissions.return_value = True
            mock_memory.cleanup_memory = AsyncMock()
            
            # Выполняем функцию
            await cmd_stats(mock_message, db_connection, 1)
            
            # Проверяем, что функция завершилась без ошибок
            mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_integration_error_handling(self, db_connection, mock_message):
        """Тест обработки ошибок в интеграции"""
        # Мокаем rate limiter
        with patch('app.features.admin.cmd_stats.get_stats_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(side_effect=Exception("Unexpected error"))
            
            # Выполняем функцию и проверяем, что ошибка обработана
            await cmd_stats(mock_message, db_connection, 1)
            
            # Проверяем, что функция не упала с исключением
            # (ошибка должна быть залогирована, но функция должна завершиться)
            mock_message.answer.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
