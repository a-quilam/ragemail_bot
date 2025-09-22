"""
Интеграционные тесты для action_remove_admin.py
"""
import pytest
import asyncio
import aiosqlite
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.features.admin.action_remove_admin import (
    on_remove_admin_start,
    on_remove_admin_input,
    on_remove_admin_confirm,
    on_remove_admin_cancel,
    ErrorCodes,
    Metrics
)
from app.infra.repo.users_repo import UsersRepo
from app.utils.circuit_breaker import get_breaker
from app.utils.rate_limiter import get_admin_limiter
from app.utils.rollback_manager import get_rollback_manager


class TestActionRemoveAdminIntegration:
    """Интеграционные тесты для функций удаления администратора"""
    
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
        
        # Добавляем тестовых пользователей
        await db.execute("INSERT INTO users (user_id, role, username) VALUES (1, 'admin', 'admin_user')")
        await db.execute("INSERT INTO users (user_id, role, username) VALUES (2, 'user', 'regular_user')")
        await db.execute("INSERT INTO users (user_id, role, username) VALUES (3, 'superadmin', 'super_admin')")
        
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
    
    @pytest.fixture
    def mock_callback(self):
        """Создание мок-объекта callback"""
        callback = MagicMock(spec=types.CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 1
        callback.data = "remove_admin_confirm_2"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        return callback
    
    @pytest.fixture
    def mock_state(self):
        """Создание мок-объекта состояния FSM"""
        state = MagicMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value="RemoveAdminStates.INPUT_USERNAME")
        state.update_data = AsyncMock()
        state.get_data = AsyncMock(return_value={"target_user_id": 2, "username": "regular_user"})
        state.clear = AsyncMock()
        return state
    
    @pytest.mark.asyncio
    async def test_on_remove_admin_start_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции функции on_remove_admin_start"""
        # Мокаем rate limiter
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Мокаем circuit breaker
            with patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(return_value=[
                    (2, 'user', None, None, 'regular_user'),
                    (3, 'superadmin', None, None, 'super_admin')
                ])
                
                # Выполняем функцию
                await on_remove_admin_start(mock_message, mock_state, db_connection)
                
                # Проверяем, что сообщение было отправлено
                mock_message.answer.assert_called_once()
                
                # Проверяем, что состояние было обновлено
                mock_state.update_data.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_remove_admin_input_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции функции on_remove_admin_input"""
        # Настраиваем мок состояние
        mock_state.get_state.return_value = "RemoveAdminStates.INPUT_USERNAME"
        mock_state.update_data.return_value = None
        
        # Мокаем rate limiter
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Мокаем circuit breaker для get_by_username
            with patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(return_value=2)  # user_id
                
                # Мокаем circuit breaker для get_chat
                with patch('app.features.admin.action_remove_admin.m.bot.get_chat') as mock_get_chat:
                    mock_get_chat.return_value = MagicMock()
                    mock_get_chat.return_value.username = "regular_user"
                    
                    # Выполняем функцию
                    await on_remove_admin_input(mock_message, mock_state, db_connection)
                    
                    # Проверяем, что состояние было обновлено
                    mock_state.update_data.assert_called()
    
    @pytest.mark.asyncio
    async def test_on_remove_admin_confirm_integration(self, db_connection, mock_callback, mock_state):
        """Тест интеграции функции on_remove_admin_confirm"""
        # Настраиваем мок состояние
        mock_state.get_data.return_value = {
            "target_user_id": 2,
            "username": "regular_user"
        }
        
        # Мокаем rate limiter
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Мокаем circuit breaker
            with patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock()
                
                # Мокаем rollback manager
                with patch('app.features.admin.action_remove_admin.get_rollback_manager') as mock_rollback:
                    mock_rollback.return_value = AsyncMock()
                    mock_rollback.return_value.delete_rollback_operation = AsyncMock()
                    
                    # Мокаем create_admin_removal_rollback
                    with patch('app.features.admin.action_remove_admin.create_admin_removal_rollback') as mock_create_rollback:
                        mock_create_rollback.return_value = "rollback_123"
                        
                        # Выполняем функцию
                        await on_remove_admin_confirm(mock_callback, mock_state, db_connection)
                        
                        # Проверяем, что callback был обработан
                        mock_callback.answer.assert_called_once()
                        
                        # Проверяем, что состояние было очищено
                        mock_state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_remove_admin_cancel_integration(self, mock_callback, mock_state):
        """Тест интеграции функции on_remove_admin_cancel"""
        # Выполняем функцию
        await on_remove_admin_cancel(mock_callback, mock_state)
        
        # Проверяем, что callback был обработан
        mock_callback.answer.assert_called_once()
        
        # Проверяем, что состояние было очищено
        mock_state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, db_connection, mock_message, mock_state):
        """Тест обработки ошибок в интеграции"""
        # Настраиваем мок для генерации ошибки
        mock_state.get_state.side_effect = Exception("Database connection error")
        
        # Мокаем rate limiter
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            # Выполняем функцию и проверяем, что ошибка обработана
            await on_remove_admin_start(mock_message, mock_state, db_connection)
            
            # Проверяем, что функция не упала с исключением
            # (ошибка должна быть залогирована, но функция должна завершиться)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции rate limiting"""
        # Настраиваем rate limiter для отклонения запроса
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(False, "Rate limit exceeded"))
            
            # Выполняем функцию
            await on_remove_admin_start(mock_message, mock_state, db_connection)
            
            # Проверяем, что сообщение об ошибке было отправлено
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "превышен лимит" in call_args.lower() or "rate limit" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции circuit breaker"""
        # Настраиваем circuit breaker для генерации ошибки
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter:
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            with patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker:
                mock_breaker.return_value = AsyncMock()
                mock_breaker.return_value.call = AsyncMock(side_effect=Exception("Database unavailable"))
                
                # Выполняем функцию
                await on_remove_admin_start(mock_message, mock_state, db_connection)
                
                # Проверяем, что функция обработала ошибку gracefully
                mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_operation_integration(self, db_connection, mock_callback, mock_state):
        """Тест интеграции операций отката"""
        # Настраиваем мок состояние
        mock_state.get_data.return_value = {
            "target_user_id": 2,
            "username": "regular_user"
        }
        
        # Мокаем все зависимости
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter, \
             patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker, \
             patch('app.features.admin.action_remove_admin.get_rollback_manager') as mock_rollback, \
             patch('app.features.admin.action_remove_admin.create_admin_removal_rollback') as mock_create_rollback:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock()
            
            mock_rollback.return_value = AsyncMock()
            mock_rollback.return_value.delete_rollback_operation = AsyncMock()
            
            mock_create_rollback.return_value = "rollback_123"
            
            # Выполняем функцию
            await on_remove_admin_confirm(mock_callback, mock_state, db_connection)
            
            # Проверяем, что операция отката была создана
            mock_create_rollback.assert_called_once()
            
            # Проверяем, что callback был обработан
            mock_callback.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_tracking_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции отслеживания метрик"""
        # Мокаем все зависимости
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter, \
             patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=[])
            
            # Мокаем логирование для проверки вызовов метрик
            with patch('app.features.admin.action_remove_admin.logging') as mock_logging:
                # Выполняем функцию
                await on_remove_admin_start(mock_message, mock_state, db_connection)
                
                # Проверяем, что метрики были записаны в лог
                # (метрики записываются через logging.info)
                assert mock_logging.info.called
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_integration(self, db_connection, mock_message, mock_state):
        """Тест интеграции очистки ресурсов"""
        # Мокаем все зависимости
        with patch('app.features.admin.action_remove_admin.get_admin_limiter') as mock_limiter, \
             patch('app.features.admin.action_remove_admin.get_breaker') as mock_breaker, \
             patch('app.features.admin.action_remove_admin.MemoryManager') as mock_memory:
            
            mock_limiter.return_value = AsyncMock()
            mock_limiter.return_value.is_allowed = AsyncMock(return_value=(True, None))
            
            mock_breaker.return_value = AsyncMock()
            mock_breaker.return_value.call = AsyncMock(return_value=[])
            
            mock_memory.cleanup_memory = AsyncMock()
            
            # Выполняем функцию
            await on_remove_admin_start(mock_message, mock_state, db_connection)
            
            # Проверяем, что функция завершилась без ошибок
            # (очистка ресурсов происходит в finally блоке)
            mock_message.answer.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
