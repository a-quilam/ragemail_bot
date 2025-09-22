"""
Команда для очистки кэша псевдонимов
"""
import logging
from aiogram import types
from app.core.config import settings

logger = logging.getLogger(__name__)

async def cmd_clear_alias_cache(m: types.Message, role: str = "user"):
    """
    Очистить кэш псевдонимов для применения морфологических исправлений
    
    Эта команда принудительно очищает все кэши псевдонимов, что заставляет
    систему генерировать новые псевдонимы с применением обновленной морфологии.
    """
    # Проверяем права суперадмина
    is_superadmin = settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID
    
    if not is_superadmin:
        await m.answer("❌ Эта команда доступна только суперадмину.")
        return
    
    try:
        # Получаем AliasService из контекста
        from app.services.alias_service import AliasService
        from app.infra.repo.aliases_repo import AliasesRepo
        from app.infra.repo.alias_words_repo import AliasWordsRepo
        from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
        from zoneinfo import ZoneInfo
        
        # Создаем временный экземпляр для очистки кэша
        # В реальном боте это должно быть через dependency injection
        tz = ZoneInfo("Europe/Moscow")
        
        # Получаем соединение с БД из контекста сообщения
        # Это упрощенная версия - в реальности нужно получить БД из middleware
        import aiosqlite
        db_path = "queue.db"  # Путь к базе данных
        
        async with aiosqlite.connect(db_path) as db:
            aliases_repo = AliasesRepo(db)
            words_repo = AliasWordsRepo(db)
            blocks_repo = AliasBlocksRepo(db)
            
            alias_service = AliasService(aliases_repo, tz, words_repo, blocks_repo)
            
            # Очищаем кэш
            alias_service.clear_cache()
            
            logger.info(f"Admin {m.from_user.id} cleared alias cache")
            
            await m.answer(
                "✅ <b>Кэш псевдонимов очищен!</b>\n\n"
                "🔄 Теперь будут генерироваться новые псевдонимы с применением "
                "обновленной морфологии.\n\n"
                "📝 <b>Что изменилось:</b>\n"
                "• Прилагательные теперь склоняются по роду существительных\n"
                "• \"роговообманковый обезьяна\" → \"роговообманковая обезьяна\"\n"
                "• \"феррьеритовый лама\" → \"феррьеритовая лама\"\n\n"
                "🎯 <b>Следующие псевдонимы будут грамматически правильными!</b>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Error clearing alias cache: {e}")
        await m.answer(
            "❌ <b>Ошибка при очистке кэша</b>\n\n"
            f"Детали: {str(e)}\n\n"
            "💡 Попробуйте перезапустить бота для применения изменений.",
            parse_mode="HTML"
        )
