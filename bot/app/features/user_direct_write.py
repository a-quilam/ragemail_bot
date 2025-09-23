from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from app.texts.prompts import PROMPT_INPUT
from app.infra.repo.users_repo import UsersRepo
from app.core.config import settings
from datetime import datetime
import logging

async def is_admin_db(message, db) -> bool:
    """Проверка, является ли пользователь админом"""
    try:
        role = await UsersRepo(db).get_role(message.from_user.id)
    except Exception:
        role = "user"
    return role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and message.from_user.id == settings.SUPERADMIN_ID)

async def handle_user_message(m: types.Message, state: FSMContext, db, active_mailbox_id: int):
    """Обработка сообщений от обычных пользователей как писем"""
    
    # Проверяем, что пользователь не админ
    if await is_admin_db(m, db):
        return False  # Не обрабатываем сообщения админов
    
    # Проверяем кулдаун пользователя
    from app.infra.repo.user_cooldowns_repo import UserCooldownsRepo
    cooldowns_repo = UserCooldownsRepo(db)
    cooldown_info = await cooldowns_repo.is_user_on_cooldown(m.from_user.id, active_mailbox_id)
    
    if cooldown_info:
        cooldown_until = cooldown_info['cooldown_until']
        time_left = cooldown_until - datetime.now()
        hours_left = int(time_left.total_seconds() / 3600)
        minutes_left = int((time_left.total_seconds() % 3600) / 60)
        
        reason_text = f"\n📝 <b>Причина:</b> {cooldown_info['reason']}" if cooldown_info['reason'] else ""
        
        await m.answer(
            f"⏰ <b>Вы на кулдауне</b>\n\n"
            f"🚫 <b>Псевдоним:</b> {cooldown_info['alias']}\n"
            f"⏱️ <b>Осталось:</b> {hours_left}ч {minutes_left}м{reason_text}\n\n"
            f"💡 Обратитесь к администратору для снятия кулдауна.",
            parse_mode="HTML"
        )
        return True
    
    # Проверяем блокировки слов в сообщении
    from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
    from app.utils.message_blocking import check_message_for_blocked_words, get_blocked_message_response, get_blocked_message_keyboard
    
    blocks_repo = AliasBlocksRepo(db)
    blocked_info = await check_message_for_blocked_words(m.text, blocks_repo, active_mailbox_id)
    
    if blocked_info:
        # Отправляем сообщение о блокировке с кнопкой
        await m.answer(
            get_blocked_message_response(blocked_info, m.text, active_mailbox_id),
            parse_mode="HTML",
            reply_markup=get_blocked_message_keyboard()
        )
        
        return True
    
    # Проверяем, что у пользователя есть активный ящик
    if not active_mailbox_id:
        await m.answer(
            "❌ <b>Ящик не настроен</b>\n\n"
            "Для отправки писем необходимо привязаться к почтовому ящику.\n\n"
            "💡 <b>Как привязаться:</b>\n"
            "1. Получите deeplink-ссылку от администратора\n"
            "2. Подпишитесь на канал ящика\n"
            "3. Перейдите по deeplink-ссылке\n\n"
            "После привязки вы сможете отправлять анонимные сообщения.",
            parse_mode="HTML"
        )
        return True
    
    # Проверяем, что пользователь не в процессе написания письма
    current_state = await state.get_state()
    if current_state == WriteStates.INPUT_TEXT:
        return False  # Уже обрабатывается другим хендлером
    
    # Если это команда или специальное сообщение, не обрабатываем
    if m.text and (m.text.startswith('/') or m.text in ['⚙️ Настройки', '📊 Статистика', '📌 Закрепить пост', '🔄 Обновить']):
        return False
    
    # Начинаем процесс написания письма
    logging.info(f"User {m.from_user.id} started direct write with message: {m.text[:50]}...")
    
    await state.clear()
    await state.set_state(WriteStates.INPUT_TEXT)
    
    # Сохраняем текст сообщения
    await state.update_data(text=m.text)
    
    # Показываем TTL клавиатуру
    from app.keyboards.write_flow import ttl_kb
    await m.answer(
        "✅ <b>Письмо получено!</b>\n\n"
        "📝 <b>Ваш текст:</b>\n"
        f"<i>{m.text}</i>\n\n"
        "⏰ <b>Выберите время жизни поста:</b>",
        reply_markup=ttl_kb(),
        parse_mode="HTML"
    )
    
    return True
