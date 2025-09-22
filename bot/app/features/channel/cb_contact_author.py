from aiogram import types
from app.infra.repo.posts_repo import PostsRepo
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo
from app.services.alias_service import AliasService
from app.infra.repo.aliases_repo import AliasesRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
from app.infra.repo.stats_repo import StatsRepo
from app.services.stats_service import StatsService

async def cb_contact(c: types.CallbackQuery, db, bot, tz):
    rec = await PostsRepo(db).get(c.message.chat.id, c.message.message_id)
    if not rec:
        await c.answer("Автор неизвестен.", show_alert=True)
        return
    _, _, author_id, author_alias, _, _, _ = rec
    if c.from_user.id == author_id:
        await c.answer("Нечего писать самому себе 🙂", show_alert=True)
        return
    
    # Сразу перебрасываем в чат с ботом
    try:
        await c.answer("💬 Переходим в чат с ботом...")
        
        # Отправляем сообщение в чат с ботом
        await bot.send_message(
            c.from_user.id,
            f"💬 <b>Анонимный чат</b>\n\n"
            f"Вы хотите связаться с автором поста под псевдонимом <b>{author_alias}</b>.\n\n"
            f"🔒 <b>Ваш псевдоним:</b> {await AliasService(AliasesRepo(db), tz, AliasWordsRepo(db), AliasBlocksRepo(db)).get_or_issue(c.from_user.id, active_mailbox_id)}\n\n"
            f"⏰ Чат будет активен 30 минут.\n\n"
            f"📝 <b>Напишите ваше сообщение ниже:</b>",
            parse_mode="HTML"
        )
        
        # Открываем диалог
        requester_alias = await AliasService(AliasesRepo(db), tz, AliasWordsRepo(db), AliasBlocksRepo(db)).get_or_issue(c.from_user.id, active_mailbox_id)
        ok = await RelayService(bot, RelaysRepo(db)).open_dialog(author_id, c.from_user.id, author_alias, requester_alias)
        
        if ok:
            try:
                await StatsService(StatsRepo(db), tz).inc("relay_start")
            except Exception:
                pass
        else:
            await bot.send_message(c.from_user.id, "❌ Автор недоступен для связи.")
            
    except Exception as e:
        await c.answer("❌ Ошибка при переходе в чат.", show_alert=True)
