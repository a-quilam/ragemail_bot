"""
Простая реализация добавления канала для создания почтового ящика
"""
import logging
import re
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from app.fsm.admin_states import CreateBoxStates
from app.infra.tg_api import bot_is_admin, user_can_create_mailbox_in_channel
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.users_repo import UsersRepo
from app.keyboards.settings import confirm_box_kb

async def cb_add_channel_simple(m: types.Message, state: FSMContext, db):
    """Начало процесса добавления канала"""
    logging.info(f"ADD CHANNEL SIMPLE: User {m.from_user.id} starting simple channel add")
    
    try:
        # Очищаем предыдущее состояние
        await state.clear()
        
        text = (
            "📺 <b>Добавление канала</b>\n\n"
            "Для создания почтового ящика отправьте:\n\n"
            "🔗 <b>Ссылку на канал</b> (например: @channel_name или https://t.me/channel_name)\n"
            "🆔 <b>ID канала</b> (например: -1001234567890)\n"
            "📤 <b>Переслать пост</b> из канала\n\n"
            "⚠️ <b>Важно:</b> Бот должен быть добавлен в канал как администратор!"
        )
        
        # Устанавливаем состояние ПЕРЕД отправкой сообщения
        await state.set_state(CreateBoxStates.ADD_CHANNEL)
        logging.info(f"State set to: {CreateBoxStates.ADD_CHANNEL}")
        
        # Проверяем, что состояние действительно установлено
        check_state = await state.get_state()
        logging.info(f"State verification: {check_state}")
        
        await m.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Error in cb_add_channel_simple: {e}")
        await m.answer(f"❌ Ошибка при запуске добавления канала: {str(e)}")

async def on_channel_input(m: types.Message, state: FSMContext, db):
    """Обработка ввода канала (ссылка, ID или пересылка)"""
    logging.info(f"CHANNEL INPUT: User {m.from_user.id} sent channel info: {m.text}")
    logging.info(f"CHANNEL INPUT: Message type: {type(m.text)}")
    logging.info(f"CHANNEL INPUT: Message content: '{m.text}'")
    current_state = await state.get_state()
    logging.info(f"Current state: {current_state}")
    logging.info(f"Expected state: {CreateBoxStates.ADD_CHANNEL}")
    
    # Проверяем, что мы в правильном состоянии
    if current_state != CreateBoxStates.ADD_CHANNEL:
        logging.warning(f"Wrong state! Expected {CreateBoxStates.ADD_CHANNEL}, got {current_state}")
        return
    
    # ИСКЛЮЧАЕМ кнопки главного меню - они должны обрабатываться другими хендлерами
    if m.text in ["✍️ Написать письмо", "⚙️ Настройки", "📊 Статистика", "📌 Закрепить пост", "🔄 Обновить", "➕ Создать почтовый ящик", "📦 Управление ящиками", "👤 Добавить админа", "🗑️ Удалить админа", "🔙 Назад", "🛡️ Антиспам"]:
        logging.info(f"CHANNEL INPUT: Ignoring main menu button: {m.text}")
        return
    
    channel_id = None
    channel_name = None
    
    try:
        # Проверяем, это пересылка?
        if m.forward_from_chat:
            if m.forward_from_chat.type in ['channel', 'supergroup']:
                channel_id = m.forward_from_chat.id
                channel_name = m.forward_from_chat.title or f"Канал {channel_id}"
            else:
                await m.answer("❌ Пересланный чат не является каналом или супергруппой")
                return
        
        # Проверяем, это ссылка или ID?
        elif m.text:
            text = m.text.strip()
            
            # Проверяем ID канала (начинается с -100 или просто отрицательное число)
            if (text.startswith('-100') and text[4:].isdigit()) or (text.startswith('-') and text[1:].isdigit()):
                channel_id = int(text)
                try:
                    chat = await m.bot.get_chat(channel_id)
                    channel_name = chat.title or f"Канал {channel_id}"
                except TelegramAPIError as e:
                    await m.answer(f"❌ Не удалось получить информацию о канале: {e}")
                    return
            
            # Проверяем, это просто число (положительный ID канала)
            elif text.isdigit():
                # Пытаемся получить канал по положительному ID
                try:
                    channel_id = int(text)
                    chat = await m.bot.get_chat(channel_id)
                    if chat.type in ['channel', 'supergroup']:
                        channel_name = chat.title or f"Канал {channel_id}"
                    else:
                        await m.answer("❌ Указанный ID не является каналом")
                        return
                except TelegramAPIError as e:
                    await m.answer(f"❌ Не удалось получить информацию о канале: {e}")
                    return
            
            # Проверяем ссылку на канал
            elif '@' in text or 't.me/' in text:
                # Извлекаем username из ссылки
                username = None
                if '@' in text:
                    parts = text.split('@')[-1].split()
                    username = parts[0] if parts else None
                elif 't.me/' in text:
                    parts = text.split('t.me/')[-1].split('?')[0].split()
                    username = parts[0] if parts else None
                
                if username:
                    try:
                        chat = await m.bot.get_chat(f"@{username}")
                        if chat.type in ['channel', 'supergroup']:
                            channel_id = chat.id
                            channel_name = chat.title or f"Канал {channel_id}"
                        else:
                            await m.answer("❌ Указанный чат не является каналом")
                            return
                    except TelegramAPIError as e:
                        await m.answer(f"❌ Не удалось найти канал: {e}")
                        return
                else:
                    await m.answer("❌ Неверный формат ссылки на канал")
                    return
            else:
                await m.answer("❌ Неверный формат. Отправьте ссылку, ID канала или перешлите пост из канала")
                return
        
        else:
            await m.answer("❌ Отправьте ссылку, ID канала или перешлите пост из канала")
            return
        
        if not channel_id:
            await m.answer("❌ Не удалось определить канал")
            return
        
        # Проверяем, что бот является администратором канала
        if not await bot_is_admin(m.bot, channel_id):
            await m.answer(
                "❌ Бот не является администратором этого канала.\n\n"
                "Добавьте бота в канал как администратора и попробуйте снова."
            )
            return
        
        # Проверяем права пользователя на создание ящика в канале
        if not await user_can_create_mailbox_in_channel(m.bot, channel_id, m.from_user.id):
            await m.answer("❌ У вас нет прав администратора в этом канале")
            return
        
        # Проверяем, что канал не используется в другом ящике
        mailboxes_repo = MailboxesRepo(db)
        existing_mailbox = await mailboxes_repo.get_by_channel_id(channel_id)
        if existing_mailbox is not None:
            await m.answer("❌ Этот канал уже используется в другом ящике")
            return
        
        # Сохраняем данные и переходим к подтверждению
        await state.update_data(
            name=channel_name,
            channel_id=channel_id
        )
        await state.set_state(CreateBoxStates.CONFIRM)
        
        # Показываем подтверждение
        summary = (
            "📦 <b>Создание почтового ящика</b>\n\n"
            f"📺 <b>Канал:</b> {channel_name}\n"
            f"🆔 <b>ID:</b> {channel_id}\n\n"
            "Подтвердить создание?"
        )
        
        await m.answer(summary, reply_markup=confirm_box_kb(), parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Error processing channel input: {e}")
        await m.answer(f"❌ Ошибка при обработке канала: {str(e)}")
