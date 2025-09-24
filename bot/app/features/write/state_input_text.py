from aiogram import types
from aiogram.fsm.context import FSMContext
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from app.fsm.write_states import WriteStates
from app.texts.previews import build_ttl_preview
from app.keyboards.ttl_selection import ttl_selection_kb
from app.services.alias_service import AliasService
from app.infra.repo.aliases_repo import AliasesRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
from app.core.constants import MAX_TEXT_LENGTH, DEFAULT_TTL_SECONDS

DEFAULT_TTL = DEFAULT_TTL_SECONDS

async def on_text_input(m: types.Message, state: FSMContext, db, tz: ZoneInfo, active_mailbox_id: Optional[int] = None, **kwargs):
    bot = kwargs.get('bot')
    
    text = (m.text or "").strip()
    if not text:
        logging.info(f"TEXT INPUT: Empty text from user {m.from_user.id}")
        await bot.send_message(m.chat.id, "Пустой текст. Напишите письмо текстом.")
        return
    
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
        
        await bot.send_message(
            m.chat.id,
            f"⏰ <b>Вы на кулдауне</b>\n\n"
            f"🚫 <b>Псевдоним:</b> {cooldown_info['alias']}\n"
            f"⏱️ <b>Осталось:</b> {hours_left}ч {minutes_left}м{reason_text}\n\n"
            f"💡 Обратитесь к администратору для снятия кулдауна.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Проверяем блокировки слов в сообщении
    from app.utils.message_blocking import check_message_for_blocked_words, get_blocked_message_response, get_blocked_message_keyboard
    
    blocks_repo = AliasBlocksRepo(db)
    blocked_info = await check_message_for_blocked_words(text, blocks_repo, active_mailbox_id)
    
    if blocked_info:
        # Отправляем сообщение о блокировке с кнопкой
        await bot.send_message(
            m.chat.id,
            get_blocked_message_response(blocked_info, text, active_mailbox_id),
            parse_mode="HTML",
            reply_markup=get_blocked_message_keyboard()
        )
        
        await state.clear()
        return
    
    # Валидация длины текста
    if len(text) > MAX_TEXT_LENGTH:
        await bot.send_message(
            m.chat.id,
            f"❌ <b>Слишком длинное сообщение</b>\n\n"
            f"Максимальная длина: {MAX_TEXT_LENGTH} символов\n"
            f"Ваше сообщение: {len(text)} символов\n\n"
            f"Попробуйте сократить текст.",
            parse_mode="HTML"
        )
        return

    await state.update_data(text=text)
    await state.set_state(WriteStates.CHOOSE_TTL)

    # Оптимизированная генерация псевдонима с логированием
    from app.utils.performance_logger import performance_logger
    alias = await performance_logger.measure_db_operation(
        "alias_generation",
        AliasService(AliasesRepo(db), tz, AliasWordsRepo(db), AliasBlocksRepo(db)).get_or_issue,
        m.from_user.id,
        active_mailbox_id
    )
    # Округляем до 5 минут в меньшую сторону
    current_time = int(time.time())
    rounded_time = (current_time // 300) * 300  # 300 секунд = 5 минут
    delete_at = rounded_time + DEFAULT_TTL
    await state.update_data(
        alias=alias,
        delete_at=delete_at,
        current_ttl=DEFAULT_TTL
    )
    preview = build_ttl_preview(alias, text=text, delete_at=delete_at, tz=tz)
    await bot.send_message(m.chat.id, preview, reply_markup=ttl_selection_kb(DEFAULT_TTL, 48*60*60, tz))
    logging.info(f"TEXT INPUT: Successfully processed text from user {m.from_user.id}, alias: {alias}")
