"""
Тесты для проверки очистки FSM состояния при ошибках создания ящика
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.features.admin.create_box_confirm import cb_box_confirm
from app.features.admin.simple_channel_add import on_channel_input
from app.features.admin.create_box_step0 import cb_create_box
from app.features.write.auto_text_handler import on_auto_text_input
from app.fsm.admin_states import CreateBoxStates


class TestCreateBoxStateCleanup:
    """Тесты для проверки очистки состояния при ошибках создания ящика"""
    
    @pytest.mark.asyncio
    async def test_cb_box_confirm_clears_state_on_error(self):
        """Тест: cb_box_confirm очищает состояние при ошибке создания ящика"""
        # Arrange
        callback = AsyncMock(spec=types.CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 12345
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.edit_text = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={"name": "test", "channel_id": -1001234567890})
        state.clear = AsyncMock()
        
        db = AsyncMock()
        
        # Мокаем функцию проверки прав, чтобы она вызвала исключение
        with patch('app.infra.tg_api.user_can_create_mailbox_in_channel') as mock_check:
            mock_check.side_effect = Exception("Test error")
            
            # Act
            await cb_box_confirm(callback, state, db)
            
            # Assert
            state.clear.assert_called_once()
            callback.answer.assert_called_once()
            # Проверяем, что сообщение об ошибке было отправлено
            assert "❌ Ошибка создания ящика" in str(callback.answer.call_args)
    
    @pytest.mark.asyncio
    async def test_on_channel_input_clears_state_on_error(self):
        """Тест: on_channel_input очищает состояние при ошибке обработки канала"""
        # Arrange
        message = AsyncMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 12345
        message.text = "@test_channel"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value=CreateBoxStates.ADD_CHANNEL)
        state.clear = AsyncMock()
        
        db = AsyncMock()
        
        # Мокаем функцию проверки бота, чтобы она вызвала исключение
        with patch('app.features.admin.simple_channel_add.bot_is_admin') as mock_check:
            mock_check.side_effect = Exception("Test error")
            
            # Act
            await on_channel_input(message, state, db)
            
            # Assert
            state.clear.assert_called_once()
            message.answer.assert_called_once()
            # Проверяем, что сообщение об ошибке было отправлено
            assert "❌ Ошибка при обработке канала" in str(message.answer.call_args)
    
    @pytest.mark.asyncio
    async def test_cb_create_box_clears_state_on_error(self):
        """Тест: cb_create_box очищает состояние при ошибке запуска создания ящика"""
        # Arrange
        message = AsyncMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 12345
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value=None)
        state.clear = AsyncMock()
        
        db = AsyncMock()
        
        # Мокаем функцию добавления канала, чтобы она вызвала исключение
        with patch('app.features.admin.simple_channel_add.cb_add_channel_simple', side_effect=Exception("Test error")):
            # Act
            await cb_create_box(message, state, db)
            
            # Assert
            state.clear.assert_called_once()
            message.answer.assert_called_once()
            # Проверяем, что сообщение об ошибке было отправлено
            assert "❌ Ошибка при запуске создания ящика" in str(message.answer.call_args)
    
    @pytest.mark.asyncio
    async def test_auto_text_handler_clears_stuck_admin_state(self):
        """Тест: auto_text_handler очищает застрявшее состояние админа"""
        # Arrange
        message = AsyncMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 12345
        message.text = "test message"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value=CreateBoxStates.CONFIRM)
        state.clear = AsyncMock()
        
        db = AsyncMock()
        active_mailbox_id = 1
        tz = None
        
        # Мокаем репозиторий пользователей, чтобы пользователь был админом
        with patch('app.features.write.auto_text_handler.UsersRepo') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_role = AsyncMock(return_value="admin")
            mock_repo_class.return_value = mock_repo
            
            # Act
            result = await on_auto_text_input(message, state, db, active_mailbox_id, tz)
            
            # Assert
            assert result is False  # Админ должен быть пропущен
            state.clear.assert_called_once()  # Состояние должно быть очищено
            message.answer.assert_called_once()
            # Проверяем, что сообщение о сбросе состояния было отправлено
            assert "🔄 Состояние сброшено" in str(message.answer.call_args)
    
    @pytest.mark.asyncio
    async def test_auto_text_handler_does_not_clear_write_states(self):
        """Тест: auto_text_handler не очищает состояния WriteStates для админов"""
        # Arrange
        message = AsyncMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 12345
        message.text = "test message"
        message.answer = AsyncMock()
        
        state = AsyncMock(spec=FSMContext)
        state.get_state = AsyncMock(return_value="WriteStates:INPUT_TEXT")
        state.clear = AsyncMock()
        
        db = AsyncMock()
        active_mailbox_id = 1
        tz = None
        
        # Мокаем репозиторий пользователей, чтобы пользователь был админом
        with patch('app.features.write.auto_text_handler.UsersRepo') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_role = AsyncMock(return_value="admin")
            mock_repo_class.return_value = mock_repo
            
            # Act
            result = await on_auto_text_input(message, state, db, active_mailbox_id, tz)
            
            # Assert
            assert result is False  # Админ должен быть пропущен
            state.clear.assert_not_called()  # Состояние WriteStates не должно очищаться
            message.answer.assert_not_called()  # Сообщение не должно отправляться
