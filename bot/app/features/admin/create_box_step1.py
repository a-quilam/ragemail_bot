from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from app.fsm.admin_states import CreateBoxStates
from app.keyboards.settings import confirm_box_kb

async def on_box_channel(m: types.Message, state: FSMContext, db):
    channel_input = (m.text or "").strip()
    channel_id = None

    # Пересланное сообщение из канала
    if m.forward_from_chat and m.forward_from_chat.type in ("channel", "supergroup"):
        channel_id = m.forward_from_chat.id
    # @username канала → получаем через get_chat
    elif channel_input.startswith('@'):
        try:
            chat = await m.bot.get_chat(channel_input)
            if chat and chat.type == 'channel':
                channel_id = chat.id
            else:
                await m.answer("Не удалось получить канал по @username. Пришлите числовой ID или перешлите пост из канала.")
                return
        except TelegramAPIError:
            await m.answer("Не удалось получить канал по @username. Пришлите числовой ID или перешлите пост из канала.")
            return
    # Полный ID канала
    elif channel_input.startswith('-') and channel_input[1:].isdigit():
        channel_id = int(channel_input)
    # Просто число
    elif channel_input.isdigit():
        channel_id = int(channel_input)
    else:
        await m.answer("Не смог определить канал. Пришлите @username, числовой ID или перешлите пост из канала.")
        return

    # Проверяем, что бот админ в канале
    try:
        chat_member = await m.bot.get_chat_member(channel_id, m.bot.id)
        if getattr(chat_member, 'status', None) not in ['administrator', 'creator']:
            await m.answer("Бот не является администратором в указанном канале. Сделайте бота админом и попробуйте снова.")
            return
    except TelegramAPIError as e:
        await m.answer(f"Ошибка при проверке прав бота в канале: {e}")
        return

    # Сохраняем данные и переходим к подтверждению
    data = await state.get_data()
    data['channel_id'] = channel_id
    await state.update_data(data)
    await state.set_state(CreateBoxStates.CONFIRM)

    summary = (
        "📦 Создание почтового ящика\n\n"
        f"Название: {data.get('name', 'Не указано')}\n"
        f"Канал: {channel_id}\n\n"
        "Подтвердить создание?"
    )
    await m.answer(summary, reply_markup=confirm_box_kb())
