from aiogram import types
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.tg_api import user_is_member
from app.utils.mailbox_permissions import can_manage_mailbox
from app.core.config import settings

async def cmd_refresh(m: types.Message, db, active_mailbox_id: int = None, bot=None):
    if not m.text or m.text not in ["/refresh", "🔄 Обновить"]:
        return
    if not active_mailbox_id:
        await m.answer("❌ Ящик не выбран")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, active_mailbox_id):
        await m.answer("❌ У вас нет прав для обновления этого ящика.")
        return
    
    box = await MailboxesRepo(db).get(active_mailbox_id)
    if not box:
        await m.answer("❌ Ящик не найден")
        return
    _, _, channel_id, _, _, _ = box

    # Получаем всех пользователей с активными ящиками
    users_repo = UsersRepo(db)
    users_with_mailboxes = await users_repo.get_users_with_active_mailboxes()
    
    checked_count = 0
    removed_count = 0
    
    for user_id in users_with_mailboxes:
        try:
            # Суперадмин не проверяется на подписку к каналу
            if settings.SUPERADMIN_ID and user_id == settings.SUPERADMIN_ID:
                checked_count += 1
                continue
                
            is_member = await user_is_member(bot, channel_id, user_id)
            if not is_member:
                # Убираем активный ящик у пользователя, который не подписан на канал
                await users_repo.set_active_mailbox(user_id, None)
                removed_count += 1
            checked_count += 1
        except Exception:
            # Игнорируем ошибки при проверке отдельных пользователей
            pass
    
    await m.answer(
        f"✅ <b>Сверка завершена</b>\n\n"
        f"📊 Проверено пользователей: {checked_count}\n"
        f"🗑️ Удалено привязок: {removed_count}\n\n"
        f"Пользователи, не подписанные на канал, больше не смогут писать в этот ящик."
    )
