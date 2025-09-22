from aiogram import types
from aiogram.fsm.context import FSMContext
from zoneinfo import ZoneInfo
from app.fsm.write_states import WriteStates
from app.services.post_service import PostService
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.extensions_repo import ExtensionsRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo

async def cb_send_now(c: types.CallbackQuery, state: FSMContext, db, bot, tz: ZoneInfo, active_mailbox_id: int):
    if not c.data.startswith("send_now:"):
        return
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if draft_id is None or f"send_now:{draft_id}" != c.data:
        await c.answer("Черновик устарел.", show_alert=True)
        return
    text = data.get("text","")
    ttl = data.get("current_ttl", 20*60)  # 20 минут по умолчанию
    alias = data.get("alias", "Аноним")
    if not active_mailbox_id:
        await c.answer("Ящик не настроен.", show_alert=True)
        return
    mbox = await MailboxesRepo(db).get(active_mailbox_id)
    if not mbox:
        await c.answer("Ящик недоступен.", show_alert=True)
        return
    _, _, channel_id, _, _, _ = mbox
    svc = PostService(bot, tz, PostsRepo(db), ExtensionsRepo(db))
    await svc.publish(channel_id, c.from_user.id, alias, text, ttl, active_mailbox_id)
    await state.clear()
    
    # Проверяем, является ли пользователь админом
    from app.infra.repo.users_repo import UsersRepo
    from app.core.config import settings
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(c.from_user.id)
    is_admin = role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and c.from_user.id == settings.SUPERADMIN_ID)
    
    if is_admin:
        # Для админов показываем главное меню
        await c.message.edit_text(
            "✅ <b>Письмо опубликовано в канал!</b>\n\n"
            "Ваше анонимное сообщение успешно отправлено.",
            reply_markup=None
        )
        
        # Отправляем новое сообщение с главным меню
        from app.keyboards.write_flow import start_kb_admin
        kb = start_kb_admin()
        await c.message.answer("🏠 Главное меню", reply_markup=kb)
    else:
        # Для обычных пользователей показываем подробную информацию
        channel_link = f"https://t.me/{channel_id.replace('@', '')}" if str(channel_id).startswith('@') else f"https://t.me/c/{str(channel_id)[4:]}" if str(channel_id).startswith('-100') else f"https://t.me/{channel_id}"
        
        await c.message.edit_text(
            "✅ <b>Письмо опубликовано!</b>\n\n"
            f"📝 <b>Ваш псевдоним:</b> {alias}\n"
            f"⏰ <b>Время жизни:</b> {ttl // 60} минут\n"
            f"📺 <b>Канал:</b> <a href='{channel_link}'>Перейти к посту</a>\n\n"
            "💬 <b>Что дальше?</b>\n"
            "• Ваше сообщение появилось в канале\n"
            "• Читатели могут продлить время жизни поста\n"
            "• Вы можете написать новое сообщение в любое время\n\n"
            "📝 <b>Напишите новое сообщение ниже:</b>",
            reply_markup=None,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    
    await c.answer()
