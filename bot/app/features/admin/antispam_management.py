from aiogram import types
from aiogram.fsm.context import FSMContext
import logging
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.user_cooldowns_repo import UserCooldownsRepo
from app.core.config import settings
from app.infra.repo.users_repo import UsersRepo
from app.utils.mailbox_permissions import can_manage_mailbox
from app.fsm.admin_states import AntispamStates
from datetime import datetime

async def is_admin_db(message, db) -> bool:
    """Проверка, является ли пользователь админом"""
    try:
        role = await UsersRepo(db).get_role(message.from_user.id)
    except Exception:
        role = "user"
    return role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and message.from_user.id == settings.SUPERADMIN_ID)

async def get_user_owned_mailboxes(db, user_id: int) -> list:
    """Получить список ящиков, которыми владеет пользователь"""
    mailboxes_repo = MailboxesRepo(db)
    all_mailboxes = await mailboxes_repo.list_all()
    
    owned_mailboxes = []
    for mailbox_id, title, channel_id, _, _, creator_id in all_mailboxes:
        # Суперадмин владеет всеми ящиками
        if settings.SUPERADMIN_ID and user_id == settings.SUPERADMIN_ID:
            owned_mailboxes.append((mailbox_id, title, channel_id, creator_id))
        # Обычный пользователь владеет только своими ящиками
        elif creator_id == user_id:
            owned_mailboxes.append((mailbox_id, title, channel_id, creator_id))
    
    return owned_mailboxes

async def cmd_antispam(m: types.Message, state: FSMContext, db, active_mailbox_id: int = None):
    """Показать меню управления антиспамом"""
    import logging
    logging.info(f"ANTISPAM: User {m.from_user.id} clicked antispam button")
    
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен. Только админы могут управлять антиспамом.")
        return
    
    # Получаем ящики, которыми владеет пользователь
    owned_mailboxes = await get_user_owned_mailboxes(db, m.from_user.id)
    
    if not owned_mailboxes:
        await m.answer("❌ У вас нет ящиков для управления антиспамом.")
        return
    
    # Определяем целевой ящик для антиспама
    target_mailbox_id = None
    
    if len(owned_mailboxes) == 1:
        # Если у пользователя только 1 ящик - используем его
        target_mailbox_id = owned_mailboxes[0][0]
    else:
        # Если несколько ящиков
        if active_mailbox_id and await can_manage_mailbox(db, m.from_user.id, active_mailbox_id):
            # Активный ящик принадлежит пользователю - используем его
            target_mailbox_id = active_mailbox_id
        else:
            # Активный ящик не принадлежит пользователю - показываем выбор
            await show_mailbox_selection(m, state, db, owned_mailboxes)
            return
    
    # Сохраняем выбранный ящик в состоянии
    await state.set_state(AntispamStates.MAILBOX_SELECTED)
    await state.update_data(antispam_mailbox_id=target_mailbox_id)
    
    # Показываем меню антиспама для выбранного ящика
    await show_antispam_menu(m, state, db, target_mailbox_id)

async def show_mailbox_selection(m: types.Message, state: FSMContext, db, owned_mailboxes: list):
    """Показать выбор ящика для антиспама"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    text = "🛡️ <b>Выберите ящик для управления антиспамом</b>\n\n"
    text += "У вас несколько ящиков. Выберите, для какого настроить антиспам:\n\n"
    
    buttons = []
    for mailbox_id, title, channel_id, creator_id in owned_mailboxes:
        text += f"• <b>{title}</b> (ID: {mailbox_id})\n"
        buttons.append([InlineKeyboardButton(
            text=f"🛡️ {title}",
            callback_data=f"antispam_mailbox:{mailbox_id}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await m.answer(text, reply_markup=keyboard, parse_mode="HTML")

async def show_antispam_menu(m: types.Message, state: FSMContext, db, mailbox_id: int):
    """Показать меню антиспама для конкретного ящика"""
    # Получаем информацию о ящике
    mailboxes_repo = MailboxesRepo(db)
    box = await mailboxes_repo.get(mailbox_id)
    if not box:
        await m.answer("❌ Ящик не найден.")
        return
    
    _, title, channel_id, _, _, _ = box
    
    blocks_repo = AliasBlocksRepo(db)
    blocks = await blocks_repo.get_blocked_words(mailbox_id)
    
    text = f"🛡️ <b>Антиспам для ящика «{title}»</b>\n\n"
    text += f"🆔 <b>ID:</b> {mailbox_id}\n"
    text += f"📺 <b>Канал:</b> {channel_id}\n\n"
    
    if blocks:
        text += "🚫 <b>Заблокированные слова:</b>\n"
        for block in blocks[:10]:  # Показываем только первые 10
            expires_info = f" (до {block['expires_at'][:16]})" if block['expires_at'] else " (навсегда)"
            text += f"• <code>{block['word']}</code>{expires_info}\n"
            if block['reason']:
                text += f"  <i>Причина: {block['reason']}</i>\n"
        
        if len(blocks) > 10:
            text += f"\n... и еще {len(blocks) - 10} блокировок\n"
    else:
        text += "✅ <b>Заблокированных слов нет</b>\n"
    
    # Показываем активные кулдауны
    cooldowns_repo = UserCooldownsRepo(db)
    cooldowns = await cooldowns_repo.get_all_cooldowns(mailbox_id)
    
    if cooldowns:
        text += f"\n⏰ <b>Активные кулдауны ({len(cooldowns)}):</b>\n"
        for cooldown in cooldowns[:3]:  # Показываем только первые 3
            time_left = cooldown['cooldown_until'] - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            text += f"• {cooldown['alias']} ({hours_left}ч осталось)\n"
        if len(cooldowns) > 3:
            text += f"... и еще {len(cooldowns) - 3} кулдаунов\n"
    
    text += "\n💡 <b>Команды блокировки слов:</b>\n"
    text += "• <code>/block слово</code> - заблокировать слово\n"
    text += "• <code>/unblock слово</code> - разблокировать слово\n"
    text += "• <code>/blocks</code> - показать все блокировки\n\n"
    text += "💡 <b>Команды кулдаунов:</b>\n"
    text += "• <code>/cooldown псевдоним [часы] [причина]</code> - кулдаун по псевдониму\n"
    text += "• <code>/remove_cooldown user_id</code> - снять кулдаун\n"
    text += "• <code>/cooldowns</code> - показать все кулдауны"
    
    await m.answer(text, parse_mode="HTML")
    
    # Очищаем состояние после показа меню
    await state.clear()

async def cb_antispam_mailbox_selection(c: types.CallbackQuery, state: FSMContext, db):
    """Обработчик выбора ящика для антиспама"""
    if not c.data.startswith("antispam_mailbox:"):
        return
    
    mailbox_id = int(c.data.split(":")[1])
    
    # Проверяем права доступа
    if not await can_manage_mailbox(db, c.from_user.id, mailbox_id):
        await c.answer("❌ Доступ запрещен.", show_alert=True)
        return
    
    # Сохраняем выбранный ящик в состоянии
    await state.set_state(AntispamStates.MAILBOX_SELECTED)
    await state.update_data(antispam_mailbox_id=mailbox_id)
    
    # Показываем меню антиспама для выбранного ящика
    await show_antispam_menu(c.message, state, db, mailbox_id)
    await c.answer()

async def cmd_block_word(m: types.Message, state: FSMContext, db):
    """Заблокировать слово"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    # Парсим команду: /block слово [причина] [время_в_часах]
    parts = m.text.split(maxsplit=3)
    if len(parts) < 2:
        await m.answer(
            "🚫 <b>Блокировка слова</b>\n\n"
            "Использование: <code>/block слово [причина] [время_в_часах]</code>\n\n"
            "Примеры:\n"
            "• <code>/block спам</code>\n"
            "• <code>/block реклама Нарушение правил</code>\n"
            "• <code>/block флуд Спам 24</code>",
            parse_mode="HTML"
        )
        return
    
    word = parts[1].lower()
    reason = parts[2] if len(parts) > 2 else ""
    duration_hours = 24  # По умолчанию 24 часа
    
    if len(parts) > 3:
        try:
            duration_hours = int(parts[3])
        except ValueError:
            duration_hours = 24
    
    blocks_repo = AliasBlocksRepo(db)
    success = await blocks_repo.block_user_by_alias_word(word, m.from_user.id, mailbox_id, reason, duration_hours)
    
    if success:
        duration_text = f"на {duration_hours} часов" if duration_hours > 0 else "навсегда"
        reason_text = f"\n📝 <b>Причина:</b> {reason}" if reason else ""
        
        await m.answer(
            f"✅ <b>Слово заблокировано</b>\n\n"
            f"🚫 <b>Слово:</b> <code>{word}</code>\n"
            f"⏰ <b>Время:</b> {duration_text}{reason_text}",
            parse_mode="HTML"
        )
    else:
        await m.answer("❌ Ошибка при блокировке слова.")

async def cmd_unblock_word(m: types.Message, state: FSMContext, db):
    """Разблокировать слово"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer(
            "🔓 <b>Разблокировка слова</b>\n\n"
            "Использование: <code>/unblock слово</code>\n\n"
            "Пример: <code>/unblock спам</code>",
            parse_mode="HTML"
        )
        return
    
    word = parts[1].lower()
    blocks_repo = AliasBlocksRepo(db)
    success = await blocks_repo.unblock_user_by_alias_word(word, mailbox_id)
    
    if success:
        await m.answer(
            f"✅ <b>Слово разблокировано</b>\n\n"
            f"🔓 <b>Слово:</b> <code>{word}</code>",
            parse_mode="HTML"
        )
    else:
        await m.answer("❌ Слово не было заблокировано или ошибка при разблокировке.")

async def cmd_show_blocks(m: types.Message, state: FSMContext, db):
    """Показать все блокировки"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    blocks_repo = AliasBlocksRepo(db)
    blocks = await blocks_repo.get_blocked_words(mailbox_id)
    
    if not blocks:
        await m.answer("✅ <b>Заблокированных слов нет</b>", parse_mode="HTML")
        return
    
    text = f"🚫 <b>Все блокировки ({len(blocks)})</b>\n\n"
    
    for i, block in enumerate(blocks, 1):
        expires_info = f"до {block['expires_at'][:16]}" if block['expires_at'] else "навсегда"
        reason_info = f" - {block['reason']}" if block['reason'] else ""
        text += f"{i}. <code>{block['word']}</code> ({expires_info}){reason_info}\n"
        
        if len(text) > 3500:  # Ограничение длины сообщения
            text += f"\n... и еще {len(blocks) - i} блокировок"
            break
    
    await m.answer(text, parse_mode="HTML")

async def cmd_cooldown_user(m: types.Message, state: FSMContext, db):
    """Установить кулдаун для пользователя по псевдониму"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    # Парсим команду: /cooldown псевдоним [время_в_часах] [причина]
    parts = m.text.split(maxsplit=3)
    if len(parts) < 2:
        await m.answer(
            "⏰ <b>Установка кулдауна по псевдониму</b>\n\n"
            "💡 <b>Использование:</b>\n"
            "• <code>/cooldown псевдоним</code> - кулдаун на 24 часа\n"
            "• <code>/cooldown псевдоним 12</code> - кулдаун на 12 часов\n"
            "• <code>/cooldown псевдоним 6 причина</code> - кулдаун на 6 часов с причиной\n\n"
            "🔍 <b>Пример:</b>\n"
            "<code>/cooldown 🐱 Тестовый автор 12 спам</code>",
            parse_mode="HTML"
        )
        return
    
    alias = parts[1]
    duration_hours = 24  # По умолчанию 24 часа
    reason = ""
    
    if len(parts) >= 3:
        try:
            duration_hours = int(parts[2])
        except ValueError:
            reason = parts[2]
    
    if len(parts) >= 4:
        reason = parts[3]
    
    cooldowns_repo = UserCooldownsRepo(db)
    success = await cooldowns_repo.set_cooldown_by_alias(alias, mailbox_id, duration_hours, reason)
    
    if success:
        await m.answer(
            f"⏰ <b>Кулдаун установлен</b>\n\n"
            f"🏷️ <b>Псевдоним:</b> {alias}\n"
            f"⏱️ <b>Время:</b> {duration_hours} часов\n"
            f"📝 <b>Причина:</b> {reason if reason else 'Не указана'}\n\n"
            f"✅ Все пользователи с этим псевдонимом не смогут писать письма.",
            parse_mode="HTML"
        )
    else:
        await m.answer("❌ Ошибка при установке кулдауна.")

async def cmd_remove_cooldown(m: types.Message, state: FSMContext, db):
    """Снять кулдаун с пользователя"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        await m.answer(
            "🔓 <b>Снятие кулдауна</b>\n\n"
            "💡 <b>Использование:</b>\n"
            "• <code>/remove_cooldown user_id</code> - снять кулдаун с пользователя\n\n"
            "🔍 <b>Пример:</b>\n"
            "<code>/remove_cooldown 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await m.answer("❌ Неверный ID пользователя.")
        return
    
    cooldowns_repo = UserCooldownsRepo(db)
    success = await cooldowns_repo.remove_cooldown(user_id, mailbox_id)
    
    if success:
        await m.answer(f"✅ Кулдаун снят с пользователя {user_id}.")
    else:
        await m.answer("❌ Кулдаун не был установлен или ошибка при снятии.")
    
    # Очищаем состояние после завершения операции
    await state.clear()

async def cmd_show_cooldowns(m: types.Message, state: FSMContext, db):
    """Показать все активные кулдауны"""
    if not await is_admin_db(m, db):
        await m.answer("❌ Доступ запрещен.")
        return
    
    # Получаем выбранный ящик из состояния
    data = await state.get_data()
    mailbox_id = data.get("antispam_mailbox_id")
    
    if not mailbox_id:
        await m.answer("❌ Сначала выберите ящик для антиспама через кнопку 🛡️ Антиспам.")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, mailbox_id):
        await m.answer("❌ Доступ запрещен к этому ящику.")
        return
    
    cooldowns_repo = UserCooldownsRepo(db)
    cooldowns = await cooldowns_repo.get_all_cooldowns(mailbox_id)
    
    if not cooldowns:
        await m.answer("✅ <b>Активных кулдаунов нет</b>")
        await state.clear()
        return
    
    text = f"⏰ <b>Активные кулдауны ({len(cooldowns)})</b>\n\n"
    
    for i, cooldown in enumerate(cooldowns[:10], 1):
        cooldown_until = cooldown['cooldown_until']
        time_left = cooldown_until - datetime.now()
        hours_left = int(time_left.total_seconds() / 3600)
        
        text += f"{i}. <b>ID:</b> {cooldown['user_id']}\n"
        text += f"   <b>Псевдоним:</b> {cooldown['alias']}\n"
        text += f"   <b>Осталось:</b> {hours_left}ч\n"
        if cooldown['reason']:
            text += f"   <b>Причина:</b> {cooldown['reason']}\n"
        text += "\n"
    
    if len(cooldowns) > 10:
        text += f"... и еще {len(cooldowns) - 10} кулдаунов\n"
    
    await m.answer(text, parse_mode="HTML")
    
    # Очищаем состояние после завершения операции
    await state.clear()
