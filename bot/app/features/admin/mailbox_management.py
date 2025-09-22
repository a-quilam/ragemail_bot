from aiogram import types
from aiogram.fsm.context import FSMContext
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.users_repo import UsersRepo
from app.keyboards.settings import mailbox_management_kb
from app.keyboards.common import confirmation_kb
from app.utils.mailbox_permissions import can_manage_mailbox
from app.utils.admin_logger import log_delete_mailbox
from app.core.config import settings

async def on_mailbox_management(m: types.Message, db, active_mailbox_id: int = None):
    """Показать управление почтовыми ящиками"""
    mailboxes_repo = MailboxesRepo(db)
    users_repo = UsersRepo(db)
    
    # Получаем ящики в зависимости от роли пользователя
    role = await users_repo.get_role(m.from_user.id)
    is_superadmin = bool(settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
    
    if is_superadmin:
        # Суперадмин видит все ящики
        mailboxes = await mailboxes_repo.list_all()
    else:
        # Обычные админы видят только свои ящики
        mailboxes = await mailboxes_repo.get_by_creator(m.from_user.id)
        
        # Если у пользователя нет ящиков, но он админ, показываем пустой список
        if not mailboxes and role not in ("admin", "superadmin"):
            await m.answer("У вас нет прав для управления ящиками.")
            return
    
    if not mailboxes:
        await m.answer("У вас нет созданных почтовых ящиков.")
        return
    
    # Формируем список ящиков
    text = "📦 <b>Управление почтовыми ящиками</b>\n\n"
    for mailbox_id, title, channel_id, stat_day, stat_time, creator_id in mailboxes:
        status = "✅ Активный" if mailbox_id == active_mailbox_id else "⚪ Неактивный"
        text += f"<b>{title}</b> (ID: {mailbox_id})\n"
        text += f"Канал: {channel_id}\n"
        text += f"Статус: {status}\n"
        if stat_day is not None and stat_time is not None:
            text += f"Статистика: день {stat_day}, время {stat_time}\n\n"
        else:
            text += f"Статистика: <i>не настроена</i>\n\n"
    
    text += "Выберите действие:"
    
    await m.answer(text, reply_markup=mailbox_management_kb(mailboxes, active_mailbox_id, m.from_user.id, is_superadmin))

async def update_mailbox_management_interface(c: types.CallbackQuery, db, user_id: int):
    """Обновить интерфейс управления ящиками"""
    from app.infra.repo.users_repo import UsersRepo
    from app.infra.repo.mailboxes_repo import MailboxesRepo
    from app.core.config import settings
    
    # Получаем активный ящик пользователя
    users_repo = UsersRepo(db)
    active_mailbox_id = await users_repo.get_active_mailbox(user_id)
    
    # Получаем все ящики
    mailboxes_repo = MailboxesRepo(db)
    mailboxes = await mailboxes_repo.list_all()
    
    # Проверяем, является ли пользователь суперадмином
    is_superadmin = (settings.SUPERADMIN_ID and user_id == settings.SUPERADMIN_ID)
    
    # Формируем текст
    text = "📦 <b>Управление почтовыми ящиками</b>\n\n"
    
    for mailbox_id, title, channel_id, stat_day, stat_time, _ in mailboxes:
        status = "✅ Активный" if mailbox_id == active_mailbox_id else "⚪ Неактивный"
        text += f"<b>{title}</b> (ID: {mailbox_id})\n"
        text += f"Канал: {channel_id}\n"
        text += f"Статус: {status}\n"
        if stat_day is not None and stat_time is not None:
            text += f"Статистика: день {stat_day}, время {stat_time}\n\n"
        else:
            text += f"Статистика: <i>не настроена</i>\n\n"
    
    text += "Выберите действие:"
    
    await c.message.edit_text(text, reply_markup=mailbox_management_kb(mailboxes, active_mailbox_id, user_id, is_superadmin), parse_mode="HTML")

async def cb_set_active_mailbox(c: types.CallbackQuery, db):
    """Установить активный ящик"""
    if not c.data.startswith("set_active:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ У вас нет прав для работы с этим ящиком.", show_alert=True)
        return
    
    users_repo = UsersRepo(db)
    await users_repo.set_active_mailbox(c.from_user.id, mailbox_id)
    
    # Получаем название ящика
    mailboxes_repo = MailboxesRepo(db)
    mailbox = await mailboxes_repo.get(mailbox_id)
    mailbox_name = mailbox[1] if mailbox and len(mailbox) > 1 else f"Ящик {mailbox_id}"
    
    # Обновляем интерфейс управления ящиками
    await update_mailbox_management_interface(c, db, c.from_user.id)
    await c.answer(f"✅ Активный ящик изменен на: {mailbox_name}")

async def cb_delete_mailbox(c: types.CallbackQuery, db):
    """Удалить ящик"""
    if not c.data.startswith("delete_mailbox:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ У вас нет прав для удаления этого ящика.", show_alert=True)
        return
    
    mailboxes_repo = MailboxesRepo(db)
    
    # Получаем название ящика перед удалением
    mailbox = await mailboxes_repo.get(mailbox_id)
    mailbox_name = mailbox[1] if mailbox and len(mailbox) > 1 else f"Ящик {mailbox_id}"
    
    # Запрашиваем подтверждение
    await c.message.edit_text(
        f"⚠️ <b>Подтверждение удаления ящика</b>\n\n"
        f"Вы действительно хотите удалить ящик <b>«{mailbox_name}»</b>?\n\n"
        f"<i>Это действие нельзя отменить! Все данные ящика будут потеряны!</i>",
        parse_mode="HTML",
        reply_markup=confirmation_kb("delete_mailbox", mailbox_id)
    )
    await c.answer()

async def cb_confirm_delete_mailbox(c: types.CallbackQuery, db):
    """Подтверждение удаления ящика"""
    if not c.data.startswith("confirm:delete_mailbox:"):
        return
    
    mailbox_id = int(c.data.split(":")[2])
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ У вас нет прав для удаления этого ящика.", show_alert=True)
        return
    
    mailboxes_repo = MailboxesRepo(db)
    
    # Получаем название ящика перед удалением
    mailbox = await mailboxes_repo.get(mailbox_id)
    mailbox_name = mailbox[1] if mailbox and len(mailbox) > 1 else f"Ящик {mailbox_id}"
    
    # Удаляем ящик
    await db.execute("DELETE FROM mailboxes WHERE id = ?", (mailbox_id,))
    await db.commit()
    
    # Логируем действие
    log_delete_mailbox(c.from_user.id, mailbox_id, mailbox_name)
    
    await c.message.edit_text(f"🗑️ <b>Ящик удален</b>\n\nЯщик <b>«{mailbox_name}»</b> успешно удален.", parse_mode="HTML")
    await c.answer()

async def cb_cancel_delete_mailbox(c: types.CallbackQuery):
    """Отмена удаления ящика"""
    if not c.data.startswith("cancel:delete_mailbox:"):
        return
    
    await c.message.edit_text("❌ Удаление ящика отменено.")
    await c.answer()

async def cb_back_to_settings(c: types.CallbackQuery, db):
    """Вернуться к настройкам"""
    if c.data != "back_to_settings":
        return
    
    from app.core.config import settings
    from app.infra.repo.users_repo import UsersRepo
    
    # Проверяем роль в БД
    role = await UsersRepo(db).get_role(c.from_user.id)
    is_superadmin = bool(settings.SUPERADMIN_ID and c.from_user.id == settings.SUPERADMIN_ID)
    
    # Отправляем новое сообщение с клавиатурой настроек
    from app.keyboards.settings import settings_kb
    await c.message.edit_text("Привет, админ! Что хочешь сделать?")
    await c.message.answer("Выберите действие:", reply_markup=settings_kb(is_superadmin))
    await c.answer()
