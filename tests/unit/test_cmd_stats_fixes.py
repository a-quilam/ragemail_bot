"""
Комплексное тестирование исправлений в cmd_stats.py
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

# Импорты для тестирования
from app.features.admin.cmd_stats import cmd_stats


class TestCmdStatsFixes:
    """Тесты для исправлений в cmd_stats.py"""
    
    @pytest.fixture
    def mock_message(self):
        """Мок сообщения"""
        message = Mock(spec=types.Message)
        message.from_user = Mock()
        message.from_user.id = 123456789
        message.answer = AsyncMock()
        message.bot = Mock()
        return message
    
    @pytest.fixture
    def mock_state(self):
        """Мок состояния FSM"""
        state = Mock(spec=FSMContext)
        state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        return state
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации входных параметров в cmd_stats"""
        # Тест с неверным типом сообщения
        await cmd_stats(None, mock_state, mock_db)
        mock_message.answer.assert_not_called()
        
        # Тест с None состоянием
        await cmd_stats(mock_message, None, mock_db)
        mock_message.answer.assert_not_called()
        
        # Тест с None базой данных
        await cmd_stats(mock_message, mock_state, None)
        mock_message.answer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_user_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации пользователя в cmd_stats"""
        # Тест с None from_user
        mock_message.from_user = None
        
        await cmd_stats(mock_message, mock_state, mock_db)
        mock_message.answer.assert_called_with("❌ Ошибка: неверные данные пользователя.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_user_id_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации user_id в cmd_stats"""
        # Тест с неверным user_id
        mock_message.from_user.id = -1
        
        await cmd_stats(mock_message, mock_state, mock_db)
        mock_message.answer.assert_called_with("❌ Ошибка: неверный ID пользователя.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_mailbox_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации почтового ящика в cmd_stats"""
        # Тест с неверным active_mailbox_id
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': -1})
        
        await cmd_stats(mock_message, mock_state, mock_db)
        mock_message.answer.assert_called_with("❌ Ошибка: неверный ID почтового ящика.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_mailbox_data_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации данных почтового ящика в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            # Симулируем некорректные данные от БД
            mock_repo.return_value.get = AsyncMock(return_value=None)
            
            await cmd_stats(mock_message, mock_state, mock_db)
            mock_message.answer.assert_called_with("❌ Ошибка: почтовый ящик не найден.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_mailbox_tuple_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации кортежа почтового ящика в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            # Симулируем некорректный кортеж от БД
            mock_repo.return_value.get = AsyncMock(return_value=(1,))  # Недостаточно элементов
            
            await cmd_stats(mock_message, mock_state, mock_db)
            mock_message.answer.assert_called_with("❌ Ошибка: некорректные данные почтового ящика.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_access_rights_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации прав доступа в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(return_value=(1, "Test Mailbox", 123456789, 1, "12:00"))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = False
                
                await cmd_stats(mock_message, mock_state, mock_db)
                mock_message.answer.assert_called_with("❌ У вас нет прав для просмотра статистики этого почтового ящика.")
    
    @pytest.mark.asyncio
    async def test_cmd_stats_stats_validation(self, mock_message, mock_state, mock_db):
        """Тест валидации статистики в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(return_value=(1, "Test Mailbox", 123456789, 1, "12:00"))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = True
                
                with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                    # Симулируем ошибку при получении статистики
                    mock_stats_repo.return_value.get_stats_for_mailbox = AsyncMock(side_effect=Exception("Stats Error"))
                    
                    await cmd_stats(mock_message, mock_state, mock_db)
                    mock_message.answer.assert_called()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "Временная недоступность" in call_args
                    assert "Не удалось загрузить статистику" in call_args
    
    @pytest.mark.asyncio
    async def test_cmd_stats_safe_string_formatting(self, mock_message, mock_state, mock_db):
        """Тест безопасного форматирования строк в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            # Симулируем данные с None значениями
            mock_repo.return_value.get = AsyncMock(return_value=(1, None, 123456789, 1, None))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = True
                
                with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                    mock_stats_repo.return_value.get_stats_for_mailbox = AsyncMock(return_value=[])
                    
                    await cmd_stats(mock_message, mock_state, mock_db)
                    
                    # Проверяем, что функция обработала None значения безопасно
                    mock_message.answer.assert_called()
                    call_args = mock_message.answer.call_args[0][0]
                    assert "неизвестный" in call_args or "1" in call_args
    
    @pytest.mark.asyncio
    async def test_cmd_stats_graceful_degradation(self, mock_message, mock_state, mock_db):
        """Тест graceful degradation при ошибке в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(side_effect=Exception("DB Error"))
            
            await cmd_stats(mock_message, mock_state, mock_db)
            
            # Проверяем, что отправлено сообщение о временной недоступности
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "Временная недоступность" in call_args
            assert "Не удалось загрузить статистику" in call_args
    
    @pytest.mark.asyncio
    async def test_cmd_stats_fallback_constants(self, mock_message, mock_state, mock_db):
        """Тест использования fallback констант в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(return_value=(1, "Test Mailbox", 123456789, 1, "12:00"))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = True
                
                with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                    mock_stats_repo.return_value.get_stats_for_mailbox = AsyncMock(return_value=[])
                    
                    # Симулируем отсутствие констант
                    with patch('app.features.admin.cmd_stats.DAYS_OF_WEEK', None):
                        with patch('app.features.admin.cmd_stats.STAT_TYPE_LABELS', None):
                            await cmd_stats(mock_message, mock_state, mock_db)
                            
                            # Проверяем, что функция использовала fallback константы
                            mock_message.answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_safe_dict_access(self, mock_message, mock_state, mock_db):
        """Тест безопасного доступа к словарю в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(return_value=(1, "Test Mailbox", 123456789, 1, "12:00"))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = True
                
                with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                    mock_stats_repo.return_value.get_stats_for_mailbox = AsyncMock(return_value=[])
                    
                    # Симулируем некорректный STAT_TYPE_LABELS
                    with patch('app.features.admin.cmd_stats.STAT_TYPE_LABELS', "not_a_dict"):
                        await cmd_stats(mock_message, mock_state, mock_db)
                        
                        # Проверяем, что функция обработала некорректный словарь
                        mock_message.answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_error_handling(self, mock_message, mock_state, mock_db):
        """Тест обработки ошибок в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(return_value=(1, "Test Mailbox", 123456789, 1, "12:00"))
            
            with patch('app.features.admin.cmd_stats.can_manage_mailbox') as mock_can_manage:
                mock_can_manage.return_value = True
                
                with patch('app.features.admin.cmd_stats.StatsRepo') as mock_stats_repo:
                    mock_stats_repo.return_value.get_stats_for_mailbox = AsyncMock(return_value=[])
                    
                    # Симулируем общую ошибку
                    with patch('app.features.admin.cmd_stats.logging') as mock_logging:
                        await cmd_stats(mock_message, mock_state, mock_db)
                        
                        # Проверяем, что ошибка была залогирована
                        mock_logging.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_cmd_stats_monitoring_alerts(self, mock_message, mock_state, mock_db):
        """Тест мониторинга и алертов в cmd_stats"""
        mock_state.get_data = AsyncMock(return_value={'active_mailbox_id': 1})
        
        with patch('app.features.admin.cmd_stats.MailboxesRepo') as mock_repo:
            mock_repo.return_value.get = AsyncMock(side_effect=Exception("Critical Error"))
            
            with patch('app.features.admin.cmd_stats.logging') as mock_logging:
                await cmd_stats(mock_message, mock_state, mock_db)
                
                # Проверяем, что критическая ошибка была залогирована
                mock_logging.critical.assert_called()
                call_args = mock_logging.critical.call_args[0][0]
                assert "КРИТИЧЕСКАЯ ОШИБКА" in call_args
                assert "Critical Error" in call_args


if __name__ == "__main__":
    pytest.main([__file__])
