"""
Тесты для улучшенного отображения статистики
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.features.admin.cmd_stats import cmd_stats
from app.features.admin.cmd_statday import cmd_statday
from app.features.admin.cmd_stathour import cmd_stathour


class TestStatsDisplayImprovements:
    """Тесты улучшенного отображения статистики"""
    
    @pytest.fixture
    def mock_message(self):
        """Мок сообщения"""
        message = MagicMock()
        message.text = "📊 Статистика"
        message.from_user.id = 123
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def mock_mailboxes_repo(self):
        """Мок репозитория ящиков"""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_stats_repo(self):
        """Мок репозитория статистики"""
        repo = AsyncMock()
        return repo
    
    @pytest.mark.asyncio
    async def test_stats_display_when_not_configured(self, mock_message, mock_db):
        """Тест отображения статистики когда она не настроена"""
        # Настраиваем мок для ящика без статистики
        mock_box = (1, "Test Mailbox", 12345, None, None, 123)
        
        # Мокаем репозитории
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.features.admin.cmd_stats.MailboxesRepo", lambda db: AsyncMock(get=AsyncMock(return_value=mock_box)))
            m.setattr("app.features.admin.cmd_stats.StatsRepo", lambda db: AsyncMock(get_stats_for_mailbox=AsyncMock(return_value={})))
            m.setattr("app.features.admin.cmd_stats.can_manage_mailbox", AsyncMock(return_value=True))
            
            await cmd_stats(mock_message, mock_db, 1)
            
            # Проверяем, что сообщение содержит правильный текст
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            
            assert "не настроена" in call_args
            assert "/statday 1-7" in call_args
            assert "/stathour HH:MM" in call_args
            assert "не установлен" not in call_args  # Старый текст не должен присутствовать
    
    @pytest.mark.asyncio
    async def test_stats_display_when_configured(self, mock_message, mock_db):
        """Тест отображения статистики когда она настроена"""
        # Настраиваем мок для ящика с настроенной статистикой
        mock_box = (1, "Test Mailbox", 12345, 1, "10:00", 123)
        
        # Мокаем репозитории
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.features.admin.cmd_stats.MailboxesRepo", lambda db: AsyncMock(get=AsyncMock(return_value=mock_box)))
            m.setattr("app.features.admin.cmd_stats.StatsRepo", lambda db: AsyncMock(get_stats_for_mailbox=AsyncMock(return_value={})))
            m.setattr("app.features.admin.cmd_stats.can_manage_mailbox", AsyncMock(return_value=True))
            
            await cmd_stats(mock_message, mock_db, 1)
            
            # Проверяем, что сообщение содержит правильный текст
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            
            assert "понедельник" in call_args
            assert "10:00" in call_args
            assert "не настроена" not in call_args
    
    @pytest.mark.asyncio
    async def test_statday_command_improved_messages(self, mock_db):
        """Тест улучшенных сообщений команды /statday"""
        # Тест неверного формата
        message = MagicMock()
        message.text = "/statday invalid"
        message.answer = AsyncMock()
        
        await cmd_statday(message, mock_db, 1)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Неверный формат команды" in call_args
        assert "Примеры:" in call_args
        
        # Тест неверного дня
        message.text = "/statday 8"
        message.answer.reset_mock()
        
        await cmd_statday(message, mock_db, 1)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Неверный день недели" in call_args
        assert "1 - понедельник" in call_args
    
    @pytest.mark.asyncio
    async def test_stathour_command_improved_messages(self, mock_db):
        """Тест улучшенных сообщений команды /stathour"""
        # Тест неверного формата
        message = MagicMock()
        message.text = "/stathour invalid"
        message.answer = AsyncMock()
        
        await cmd_stathour(message, mock_db, 1)
        
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Неверный формат команды" in call_args
        assert "Примеры:" in call_args
        assert "10:00" in call_args
