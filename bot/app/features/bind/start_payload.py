from aiogram import types
from aiogram.filters import CommandStart
import logging
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.tg_api import user_is_member

async def cmd_start_payload(m: types.Message, db, bot):
    logging.info(f"START PAYLOAD: user {m.from_user.id}, text: '{m.text}'")
    
    if not m.text:
        return
    parts = m.text.split()
    if len(parts) < 2:
        return
    payload = parts[1]
    if not payload.isdigit():
        return
    
    try:
        mailbox_id = int(payload)
        if mailbox_id <= 0:
            await m.answer("❌ Неверный ID ящика.")
            return
    except (ValueError, OverflowError):
        await m.answer("❌ Неверный формат ID ящика.")
        return
    box = await MailboxesRepo(db).get(mailbox_id)
    if not box:
        await m.answer("Ящик не найден.")
        return
    
    # Безопасная распаковка кортежа
    if len(box) < 6:
        await m.answer("❌ Ошибка: неполные данные ящика.")
        return
    
    _, _, channel_id, _, _, _ = box
    
    # Валидация channel_id
    if not channel_id:
        await m.answer("❌ Ошибка: канал ящика не настроен.")
        return
    
    logging.info(f"START PAYLOAD: checking membership for user {m.from_user.id} in channel {channel_id}")
    if not await user_is_member(bot, channel_id, m.from_user.id):
        await m.answer(
            "❌ <b>Доступ ограничен</b>\n\n"
            "Вы не подписаны на канал этого ящика.\n"
            "Подпишитесь на канал и нажмите ссылку ещё раз.",
            parse_mode="HTML"
        )
        return
    # Создаем пользователя в базе данных если его нет
    users_repo = UsersRepo(db)
    if not await users_repo.get(m.from_user.id):
        # Создаем пользователя если его нет в базе
        await users_repo.upsert(m.from_user.id, username=m.from_user.username)
        logging.info(f"START PAYLOAD: Created new user {m.from_user.id} in database")
    else:
        # Обновляем username если он изменился
        await users_repo.update_username(m.from_user.id, m.from_user.username)
    
    # Устанавливаем активный ящик
    await users_repo.set_active_mailbox(m.from_user.id, mailbox_id)
    logging.info(f"START PAYLOAD: Set active mailbox {mailbox_id} for user {m.from_user.id}")
    
    # Проверяем, может ли пользователь управлять этим ящиком
    from app.core.config import settings
    _, _, _, _, _, creator_id = box
    
    # Оптимизированная проверка прав без дополнительных запросов к БД
    can_manage = False
    if settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID:
        can_manage = True  # Суперадмин
    elif creator_id is not None and isinstance(creator_id, int):
        can_manage = creator_id == m.from_user.id  # Создатель ящика
    else:
        # Для ящиков без создателя - проверяем роль (только если нужно)
        role = await users_repo.get_role(m.from_user.id)
        can_manage = role in ("admin", "superadmin")
    
    logging.info(f"START PAYLOAD: User {m.from_user.id} can_manage_mailbox: {can_manage}")
    
    # Отправляем правильный интерфейс
    from app.keyboards.write_flow import start_kb_admin, start_kb_user
    
    if can_manage:
        kb = start_kb_admin()
        await m.answer(
            "✅ <b>Привязка выполнена!</b>\n\n"
            "Теперь вы пишете в этот ящик по умолчанию.\n\n"
            "Доступные действия:\n"
            "✍️ <b>Написать письмо</b> — создать анонимное сообщение\n"
            "⚙️ <b>Настройки</b> — управление ящиками и пользователями\n"
            "📊 <b>Статистика</b> — просмотр статистики\n"
            "📌 <b>Закрепить пост</b> — создать deeplink-пост\n"
            "🔄 <b>Обновить</b> — синхронизация с каналом",
            reply_markup=kb
        )
    else:
        kb = start_kb_user()
        await m.answer(
            "✅ <b>Привязка выполнена!</b>\n\n"
            "Теперь вы пишете в этот ящик по умолчанию.\n\n"
            "Просто напишите ваше анонимное сообщение, и я отправлю его в канал.",
            reply_markup=kb
        )
