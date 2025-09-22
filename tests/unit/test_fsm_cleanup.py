"""
Тесты для проверки очистки FSM состояний
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.utils.fsm_utils import safe_clear_state, handle_fsm_error, ensure_state_cleared_on_exit
from app.utils.fsm_timeout import FSMTimeoutManager, track_fsm_state, untrack_fsm_state


class TestFSMUtils:
    """Тесты для утилит FSM"""
    
    @pytest.mark.asyncio
    async def test_safe_clear_state_success(self):
        """Тест успешной очистки состояния"""
        state = AsyncMock()
        state.get_state.return_value = "AddAdminStates:ASK_USER"
        state.clear = AsyncMock()
        
        result = await safe_clear_state(state, 12345)
        
        assert result is True
        state.get_state.assert_called_once()
        state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_clear_state_no_state(self):
        """Тест очистки когда состояние уже пустое"""
        state = AsyncMock()
        state.get_state.return_value = None
        state.clear = AsyncMock()
        
        result = await safe_clear_state(state, 12345)
        
        assert result is False
        state.get_state.assert_called_once()
        state.clear.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_safe_clear_state_error(self):
        """Тест обработки ошибки при очистке состояния"""
        state = AsyncMock()
        state.get_state.side_effect = Exception("Test error")
        
        result = await safe_clear_state(state, 12345)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_fsm_error_message(self):
        """Тест обработки ошибки с сообщением"""
        message = AsyncMock()
        message.from_user.id = 12345
        message.answer = AsyncMock()
        
        state = AsyncMock()
        state.get_state.return_value = "AddAdminStates:ASK_USER"
        state.clear = AsyncMock()
        
        await handle_fsm_error(message, state, "Test error message")
        
        message.answer.assert_called_once_with("Test error message")
        state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_fsm_error_callback(self):
        """Тест обработки ошибки с callback query"""
        callback = AsyncMock()
        callback.from_user.id = 12345
        callback.answer = AsyncMock()
        
        state = AsyncMock()
        state.get_state.return_value = "AddAdminStates:ASK_USER"
        state.clear = AsyncMock()
        
        await handle_fsm_error(callback, state, "Test error message")
        
        callback.answer.assert_called_once_with("Test error message", show_alert=True)
        state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_state_cleared_on_exit(self):
        """Тест гарантированной очистки состояния при выходе"""
        message = AsyncMock()
        message.from_user.id = 12345
        message.answer = AsyncMock()
        
        state = AsyncMock()
        state.get_state.return_value = "AddAdminStates:ASK_USER"
        state.clear = AsyncMock()
        
        await ensure_state_cleared_on_exit(
            state, 
            message.from_user.id,
            "Success message",
            message
        )
        
        state.clear.assert_called_once()
        message.answer.assert_called_once_with("Success message")


class TestFSMTimeoutManager:
    """Тесты для менеджера таймаутов FSM"""
    
    def test_init(self):
        """Тест инициализации менеджера"""
        manager = FSMTimeoutManager(timeout_minutes=5)
        assert manager.timeout_minutes == 5
        assert len(manager.user_states) == 0
        assert manager._cleanup_task is None
    
    def test_track_user_state(self):
        """Тест отслеживания состояния пользователя"""
        manager = FSMTimeoutManager()
        user_id = 12345
        
        manager.track_user_state(user_id)
        
        assert user_id in manager.user_states
        assert isinstance(manager.user_states[user_id], type(manager.user_states[user_id]))
    
    def test_untrack_user_state(self):
        """Тест прекращения отслеживания состояния пользователя"""
        manager = FSMTimeoutManager()
        user_id = 12345
        
        manager.track_user_state(user_id)
        assert user_id in manager.user_states
        
        manager.untrack_user_state(user_id)
        assert user_id not in manager.user_states
    
    def test_untrack_nonexistent_user(self):
        """Тест прекращения отслеживания несуществующего пользователя"""
        manager = FSMTimeoutManager()
        user_id = 12345
        
        # Не должно вызывать ошибку
        manager.untrack_user_state(user_id)
        assert user_id not in manager.user_states
    
    def test_get_tracked_users_count(self):
        """Тест получения количества отслеживаемых пользователей"""
        manager = FSMTimeoutManager()
        
        assert manager.get_tracked_users_count() == 0
        
        manager.track_user_state(12345)
        assert manager.get_tracked_users_count() == 1
        
        manager.track_user_state(67890)
        assert manager.get_tracked_users_count() == 2
        
        manager.untrack_user_state(12345)
        assert manager.get_tracked_users_count() == 1


@pytest.mark.asyncio
async def test_track_fsm_state():
    """Тест отслеживания FSM состояния"""
    state = AsyncMock()
    state.get_state.return_value = "AddAdminStates:ASK_USER"
    
    await track_fsm_state(12345, state)
    
    state.get_state.assert_called_once()


@pytest.mark.asyncio
async def test_untrack_fsm_state():
    """Тест прекращения отслеживания FSM состояния"""
    state = AsyncMock()
    state.get_state.return_value = "AddAdminStates:ASK_USER"
    state.clear = AsyncMock()
    
    await untrack_fsm_state(12345, state)
    
    state.get_state.assert_called_once()
    state.clear.assert_called_once()
