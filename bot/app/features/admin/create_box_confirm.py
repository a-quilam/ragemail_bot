import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.users_repo import UsersRepo
from app.fsm.admin_states import CreateBoxStates

async def cb_box_confirm(cb: types.CallbackQuery, state: FSMContext, db):
    """Подтверждение создания почтового ящика"""
    logging.info(f"BOX CONFIRM: User {cb.from_user.id} confirming mailbox creation")
    
    data = await state.get_data()
    name = data.get("name")
    channel_id = data.get("channel_id")
    if not name or not channel_id:
        await cb.answer("Нет данных для сохранения", show_alert=True)
        return
    
    try:
        # Проверяем права пользователя на создание ящика в канале
        from app.infra.tg_api import user_can_create_mailbox_in_channel
        if not await user_can_create_mailbox_in_channel(cb.bot, channel_id, cb.from_user.id):
            await cb.answer("❌ У вас нет прав администратора в этом канале", show_alert=True)
            return
        
        # Проверяем, что канал не используется в другом ящике
        mailboxes_repo = MailboxesRepo(db)
        existing_mailbox = await mailboxes_repo.get_by_channel_id(channel_id)
        if existing_mailbox is not None:
            await cb.answer("❌ Этот канал уже используется в другом ящике", show_alert=True)
            return
        
        # Создаем ящик
        mailbox_id = await mailboxes_repo.create(name, channel_id, cb.from_user.id)
        
        # Автоматически устанавливаем созданный ящик как активный для пользователя
        users_repo = UsersRepo(db)
        await users_repo.set_active_mailbox(cb.from_user.id, mailbox_id)
        
        await state.clear()
        await cb.message.edit_text(f"✅ Почтовый ящик создан (id={mailbox_id}) и установлен как активный.")
        await cb.answer()
        
    except Exception as e:
        logging.error(f"Error creating mailbox: {e}")
        # Очищаем состояние при ошибке, чтобы пользователь не застрял в CONFIRM
        await state.clear()
        await cb.answer(f"❌ Ошибка создания ящика: {str(e)}", show_alert=True)

async def cb_box_back(cb: types.CallbackQuery, state: FSMContext, db):
    """Возврат к добавлению канала"""
    logging.info(f"BOX BACK: User {cb.from_user.id} going back to channel input")
    
    try:
        # Возвращаемся к состоянию добавления канала
        await state.set_state(CreateBoxStates.ADD_CHANNEL)
        
        # Показываем инструкции для добавления канала
        text = (
            "📺 <b>Добавление канала</b>\n\n"
            "Для создания почтового ящика отправьте:\n\n"
            "🔗 <b>Ссылку на канал</b> (например: @channel_name или https://t.me/channel_name)\n"
            "🆔 <b>ID канала</b> (например: -1001234567890)\n"
            "📤 <b>Переслать пост</b> из канала\n\n"
            "⚠️ <b>Важно:</b> Бот должен быть добавлен в канал как администратор!"
        )
        
        await cb.message.edit_text(text, parse_mode="HTML")
        await cb.answer()
        
    except Exception as e:
        logging.error(f"Error in cb_box_back: {e}")
        await cb.answer("❌ Ошибка при возврате к добавлению канала", show_alert=True)
