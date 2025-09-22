"""
Унифицированный обработчик для всех extend операций
"""
from aiogram import types
from app.services.extend_service import ExtendService
from app.infra.repo.extensions_repo import ExtensionsRepo
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.services.post_service import PostService
from app.infra.repo.stats_repo import StatsRepo
from app.services.stats_service import StatsService
from zoneinfo import ZoneInfo

async def cb_extend_unified(c: types.CallbackQuery, db, bot, tz: ZoneInfo):
    """
    Унифицированный обработчик для всех extend операций.
    
    Обрабатывает callback данные вида "ext:15m", "ext:30m", "ext:1h", etc.
    """
    # Извлекаем время из callback data (например: "ext:30m" -> "30m")
    extend_time = c.data.split(":")[1] if ":" in c.data else None
    
    if not extend_time:
        await c.answer("❌ Неверный формат команды", show_alert=True)
        return
    
    # Валидируем поддерживаемые времена
    valid_times = ["15m", "30m", "1h", "2h", "3h", "6h", "12h", "24h"]
    if extend_time not in valid_times:
        await c.answer(f"❌ Неподдерживаемое время: {extend_time}", show_alert=True)
        return
    
    try:
        # Создаем сервис для работы с расширениями
        svc = ExtendService(ExtensionsRepo(db), PostsRepo(db))
        
        # Применяем расширение времени
        ok, msg = await svc.toggle_with_rule(
            c.message.chat.id, 
            c.message.message_id, 
            c.from_user.id, 
            extend_time
        )
        
        if not ok:
            await c.answer(msg, show_alert=True)
            return
        
        # Получаем mailbox_id по channel_id
        mailboxes_repo = MailboxesRepo(db)
        mailbox_id = await mailboxes_repo.get_by_channel_id(c.message.chat.id)
        
        # Обновляем пост с новыми расширениями
        await PostService(
            bot, tz, PostsRepo(db), ExtensionsRepo(db)
        ).apply_extensions_and_update(
            c.message.chat.id, 
            c.message.message_id, 
            mailbox_id
        )
        
        # Обновляем статистику
        try:
            await StatsService(StatsRepo(db), tz).inc(f"extend_{extend_time}")
        except Exception:
            # Игнорируем ошибки статистики
            pass
        
        await c.answer("✅ Время обновлено")
        
    except Exception as e:
        # Логируем ошибку и отвечаем пользователю
        print(f"Error in extend handler: {e}")
        await c.answer("❌ Произошла ошибка при обновлении времени", show_alert=True)
