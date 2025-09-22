from aiogram import types
import logging
from app.infra.repo.posts_repo import PostsRepo
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo
from app.services.alias_service import AliasService
from app.infra.repo.aliases_repo import AliasesRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo

async def cb_contact(c: types.CallbackQuery, db, bot, tz, active_mailbox_id: int = None):
    rec = await PostsRepo(db).get(c.message.chat.id, c.message.message_id)
    if not rec:
        await c.answer("Автор неизвестен.", show_alert=True)
        return
    _, _, author_id, author_alias, _, _, _ = rec
    if c.from_user.id == author_id:
        await c.answer("Нечего писать самому себе 🙂", show_alert=True)
        return
    
    # Проверяем наличие активного ящика
    if not active_mailbox_id:
        await c.answer("❌ Активный ящик не настроен. Обратитесь к администратору.", show_alert=True)
        return
    
    # Сразу перебрасываем в чат с ботом
    try:
        await c.answer("💬 Переходим в чат с ботом...")
        
        # Создаем сервис для работы с псевдонимами (один раз)
        alias_service = AliasService(AliasesRepo(db), tz, AliasWordsRepo(db), AliasBlocksRepo(db))
        requester_alias = await alias_service.get_or_issue(c.from_user.id, active_mailbox_id)
        
        # Открываем диалог (он сам отправит сообщения пользователям)
        ok = await RelayService(bot, RelaysRepo(db)).open_dialog(author_id, c.from_user.id, author_alias, requester_alias)
        
        if not ok:
            await bot.send_message(c.from_user.id, "❌ Автор недоступен для связи.")
            
    except Exception as e:
        logging.error(f"Error in cb_contact for user {c.from_user.id}: {e}")
        await c.answer("❌ Ошибка при переходе в чат.", show_alert=True)
