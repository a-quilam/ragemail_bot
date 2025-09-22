from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from app.fsm.admin_states import TransferAdminStates
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.utils.mailbox_permissions import can_manage_mailbox

async def cb_transfer_admin_start(c: types.CallbackQuery, state: FSMContext, db):
    """Начать процесс передачи админки"""
    if not c.data.startswith("transfer_admin:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ У вас нет прав для передачи админки этого ящика.", show_alert=True)
        await state.clear()
        return
    
    # Сохраняем ID ящика в состоянии
    await state.set_data({"mailbox_id": mailbox_id})
    await state.set_state(TransferAdminStates.ASK_USER)
    
    await c.message.edit_text(
        "🔄 <b>Передача прав на ящик</b>\n\n"
        "Отправьте user_id пользователя цифрами, @username или перешлите его сообщение сюда.\n\n"
        "⚠️ <b>Внимание:</b> После передачи вы потеряете права управления этим ящиком, но сохраните свою роль администратора!",
        parse_mode="HTML"
    )
    await c.answer()

async def on_transfer_admin_input(m: types.Message, state: FSMContext, db):
    """Обработать ввод пользователя для передачи админки"""
    data = await state.get_data()
    mailbox_id = data.get("mailbox_id")
    
    if not mailbox_id:
        await m.answer("Ошибка: не найден ID ящика.")
        await state.clear()
        return
    
    target_user_id = None

    # Пересланное сообщение
    if m.forward_from:
        target_user_id = m.forward_from.id
    # Числовой ID
    elif m.text and m.text.strip().isdigit():
        target_user_id = int(m.text.strip())
    # @username → сначала пробуем через get_chat, потом ищем в базе данных
    elif m.text and m.text.strip().startswith('@'):
        username = m.text.strip()[1:]  # убираем @
        
        # Сначала пробуем через get_chat (работает для всех пользователей Telegram)
        try:
            chat = await m.bot.get_chat(f"@{username}")
            if chat and hasattr(chat, 'id') and chat.id:
                target_user_id = chat.id
                # Сохраняем username в базе для будущих поисков
                users_repo = UsersRepo(db)
                await users_repo.update_username(target_user_id, username)
            else:
                await m.answer("Не удалось получить ID пользователя по @username. Пришлите числовой ID или пересланное сообщение.")
                await state.clear()
                return
        except TelegramAPIError:
            # Если не удалось через get_chat, пробуем найти в базе данных
            users_repo = UsersRepo(db)
            target_user_id = await users_repo.get_by_username(username)
            
            if not target_user_id:
                await m.answer(
                    f"❌ <b>Не удалось найти пользователя</b>\n\n"
                    f"@username не найден или пользователь не существует.\n"
                    f"Для пользователей используйте:\n"
                    f"• Числовой ID (например: 123456789)\n"
                    f"• Пересланное сообщение от пользователя",
                    parse_mode="HTML"
                )
                await state.clear()
                return

    if not target_user_id:
        await m.answer("Не смог определить пользователя. Пришлите user_id цифрами или перешлите его сообщение.")
        await state.clear()
        return

    if target_user_id == m.from_user.id:
        await m.answer("❌ Нельзя передать админку самому себе.")
        await state.clear()
        return

    # Получаем информацию о ящике
    mailboxes_repo = MailboxesRepo(db)
    box = await mailboxes_repo.get(mailbox_id)
    if not box:
        await m.answer("❌ Ящик не найден.")
        await state.clear()
        return
    
    _, title, _, _, _, _ = box

    # Передаем права на ящик: обновляем creator_id в ящике
    await mailboxes_repo.db.execute(
        "UPDATE mailboxes SET creator_id = ? WHERE id = ?",
        (target_user_id, mailbox_id)
    )
    await mailboxes_repo.db.commit()
    
    # Назначаем получателю роль админа (если у него её нет)
    users_repo = UsersRepo(db)
    current_role = await users_repo.get_role(target_user_id)
    was_user = current_role == "user"
    if was_user:
        await users_repo.upsert(target_user_id, role="admin")
    
    # Уведомляем нового владельца ящика
    try:
        from app.keyboards.write_flow import start_kb_admin
        if was_user:
            # Если пользователь стал админом впервые, показываем общее поздравление
            await m.bot.send_message(
                target_user_id,
                f"🎉 <b>Поздравляем!</b>\n\n"
                f"Вы назначены администратором бота «Злое письмо».\n\n"
                f"Теперь у вас есть доступ к панели управления:\n"
                f"✍️ <b>Написать письмо</b> — создать анонимное сообщение\n"
                f"⚙️ <b>Настройки</b> — управление ящиками и пользователями\n"
                f"📊 <b>Статистика</b> — просмотр статистики\n"
                f"📌 <b>Закрепить пост</b> — создать deeplink-пост\n"
                f"🔄 <b>Обновить</b> — синхронизация с каналом",
                reply_markup=start_kb_admin(),
                parse_mode="HTML"
            )
        else:
            # Если пользователь уже был админом, показываем только сообщение о передаче ящика
            await m.bot.send_message(
                target_user_id,
                f"📦 <b>Права на ящик переданы!</b>\n\n"
                f"Вам переданы права администратора ящика «{title}».\n\n"
                f"Теперь вы можете управлять этим ящиком через меню настроек.",
                reply_markup=start_kb_admin(),
                parse_mode="HTML"
            )
    except TelegramAPIError:
        pass  # Пользователь может заблокировать бота

    await state.clear()
    await m.answer(
        f"✅ <b>Права на ящик переданы!</b>\n\n"
        f"Ящик «{title}» теперь принадлежит пользователю {target_user_id}.\n"
        f"Вы сохранили свою роль администратора, но больше не можете управлять этим ящиком.",
        parse_mode="HTML"
    )
