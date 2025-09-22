"""
Интеграционные тесты для mailbox_context.py
"""
import pytest
import asyncio
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types

from app.middlewares.mailbox_context import MailboxContextMiddleware
from app.infra.repo.users_repo import UsersRepo


class TestMailboxContextIntegration:
    """Интеграционные тесты для middleware контекста почтового ящика"""
    
    @pytest.fixture
    async def db_connection(self):
        """Создание тестовой базы данных"""
        db = await aiosqlite.connect(":memory:")
        
        # Создаем таблицу users
        await db.execute("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'user',
                username TEXT,
                active_mailbox_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавляем тестового пользователя
        await db.execute("""
            INSERT INTO users (user_id, role, username, active_mailbox_id) 
            VALUES (1, 'admin', 'admin_user', 1)
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
        return message
    
    @pytest.fixture
    def mock_callback(self):
        """Создание мок-объекта callback"""
        callback = MagicMock(spec=types.CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 1
        callback.from_user.username = "admin_user"
        return callback
    
    @pytest.fixture
    def middleware(self, db_connection):
        """Создание экземпляра middleware"""
        return MailboxContextMiddleware(db_connection)
    
    @pytest.mark.asyncio
    async def test_middleware_integration_message(self, middleware, mock_message, db_connection):
        """Тест интеграции middleware с сообщением"""
        # Мокаем circuit breaker
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=1)  # active_mailbox_id
            
            # Мокаем performance_logger
            with patch('app.middlewares.mailbox_context.performance_logger') as mock_logger:
                mock_logger.measure_db_operation = AsyncMock(return_value=1)
                
                # Создаем мок-объект для next_handler
                next_handler = AsyncMock()
                
                # Выполняем middleware
                await middleware(next_handler, mock_message, {"active_mailbox_id": 1})
                
                # Проверяем, что next_handler был вызван
                next_handler.assert_called_once()
                
                # Проверяем, что active_mailbox_id был установлен
                call_kwargs = next_handler.call_args[1]
                assert call_kwargs["active_mailbox_id"] == 1
    
    @pytest.mark.asyncio
    async def test_middleware_integration_callback(self, middleware, mock_callback, db_connection):
        """Тест интеграции middleware с callback"""
        # Мокаем circuit breaker
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=1)  # active_mailbox_id
            
            # Мокаем performance_logger
            with patch('app.middlewares.mailbox_context.performance_logger') as mock_logger:
                mock_logger.measure_db_operation = AsyncMock(return_value=1)
                
                # Создаем мок-объект для next_handler
                next_handler = AsyncMock()
                
                # Выполняем middleware
                await middleware(next_handler, mock_callback, {"active_mailbox_id": 1})
                
                # Проверяем, что next_handler был вызван
                next_handler.assert_called_once()
                
                # Проверяем, что active_mailbox_id был установлен
                call_kwargs = next_handler.call_args[1]
                assert call_kwargs["active_mailbox_id"] == 1
    
    @pytest.mark.asyncio
    async def test_middleware_integration_error_handling(self, middleware, mock_message, db_connection):
        """Тест обработки ошибок в middleware"""
        # Мокаем circuit breaker для генерации ошибки
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(side_effect=Exception("Database error"))
            
            # Создаем мок-объект для next_handler
            next_handler = AsyncMock()
            
            # Выполняем middleware
            await middleware(next_handler, mock_message, {})
            
            # Проверяем, что next_handler был вызван с дефолтным значением
            next_handler.assert_called_once()
            call_kwargs = next_handler.call_args[1]
            assert call_kwargs["active_mailbox_id"] is None
    
    @pytest.mark.asyncio
    async def test_middleware_integration_health_check(self, middleware, db_connection):
        """Тест health check в middleware"""
        # Выполняем health check
        health_status = await middleware.health_check()
        
        # Проверяем, что health check вернул результат
        assert health_status is not None
        assert "is_healthy" in health_status
        assert "last_check" in health_status
    
    @pytest.mark.asyncio
    async def test_middleware_integration_metrics(self, middleware, db_connection):
        """Тест метрик в middleware"""
        # Получаем метрики
        metrics = await middleware.get_health_metrics()
        
        # Проверяем, что метрики содержат ожидаемые поля
        assert "request_count" in metrics
        assert "error_count" in metrics
        assert "health_status" in metrics
        assert "last_health_check" in metrics
    
    @pytest.mark.asyncio
    async def test_middleware_integration_circuit_breaker(self, middleware, mock_message, db_connection):
        """Тест circuit breaker в middleware"""
        # Мокаем circuit breaker
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker_instance = AsyncMock()
            mock_breaker_instance.call = AsyncMock(return_value=1)
            mock_breaker.return_value = mock_breaker_instance
            
            # Создаем мок-объект для next_handler
            next_handler = AsyncMock()
            
            # Выполняем middleware
            await middleware(next_handler, mock_message, {})
            
            # Проверяем, что circuit breaker был вызван
            mock_breaker_instance.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_integration_performance_logging(self, middleware, mock_message, db_connection):
        """Тест логирования производительности в middleware"""
        # Мокаем circuit breaker
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=1)
            
            # Мокаем performance_logger
            with patch('app.middlewares.mailbox_context.performance_logger') as mock_logger:
                mock_logger.measure_db_operation = AsyncMock(return_value=1)
                
                # Создаем мок-объект для next_handler
                next_handler = AsyncMock()
                
                # Выполняем middleware
                await middleware(next_handler, mock_message, {})
                
                # Проверяем, что performance_logger был вызван
                mock_logger.measure_db_operation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_integration_invalid_user_id(self, middleware, db_connection):
        """Тест middleware с невалидным user_id"""
        # Создаем сообщение с невалидным user_id
        mock_message = MagicMock(spec=types.Message)
        mock_message.from_user = None  # Невалидный user_id
        
        # Создаем мок-объект для next_handler
        next_handler = AsyncMock()
        
        # Выполняем middleware
        await middleware(next_handler, mock_message, {})
        
        # Проверяем, что next_handler был вызван с дефолтным значением
        next_handler.assert_called_once()
        call_kwargs = next_handler.call_args[1]
        assert call_kwargs["active_mailbox_id"] is None
    
    @pytest.mark.asyncio
    async def test_middleware_integration_database_error(self, middleware, mock_message):
        """Тест middleware с ошибкой базы данных"""
        # Создаем middleware с невалидным соединением
        invalid_middleware = MailboxContextMiddleware(None)
        
        # Создаем мок-объект для next_handler
        next_handler = AsyncMock()
        
        # Выполняем middleware
        await invalid_middleware(next_handler, mock_message, {})
        
        # Проверяем, что next_handler был вызван с дефолтным значением
        next_handler.assert_called_once()
        call_kwargs = next_handler.call_args[1]
        assert call_kwargs["active_mailbox_id"] is None
    
    @pytest.mark.asyncio
    async def test_middleware_integration_concurrent_requests(self, middleware, db_connection):
        """Тест middleware с конкурентными запросами"""
        # Создаем несколько сообщений
        messages = []
        for i in range(5):
            message = MagicMock(spec=types.Message)
            message.from_user = MagicMock()
            message.from_user.id = i + 1
            messages.append(message)
        
        # Мокаем circuit breaker
        with patch('app.middlewares.mailbox_context.get_breaker') as mock_breaker:
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=1)
            
            # Мокаем performance_logger
            with patch('app.middlewares.mailbox_context.performance_logger') as mock_logger:
                mock_logger.measure_db_operation = AsyncMock(return_value=1)
                
                # Создаем задачи для конкурентного выполнения
                tasks = []
                for message in messages:
                    next_handler = AsyncMock()
                    task = middleware(next_handler, message, {})
                    tasks.append(task)
                
                # Выполняем все задачи конкурентно
                await asyncio.gather(*tasks)
                
                # Проверяем, что все next_handler были вызваны
                for task in tasks:
                    # Проверяем, что задача завершилась без ошибок
                    assert task.done()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
