from aiogram import types
from aiogram.exceptions import TelegramAPIError
import logging
from app.utils.mailbox_permissions import can_manage_mailbox

_postpin_wait: dict[int, int] = {}

def clear_postpin_wait(user_id: int):
    """Очищает состояние ожидания постпина для пользователя"""
    if user_id in _postpin_wait:
        del _postpin_wait[user_id]

async def cmd_postpin(m: types.Message, active_mailbox_id: int = None, db=None):
    if not m.text or m.text not in ["/postpin", "📌 Закрепить пост"]:
        return
    if not active_mailbox_id:
        await m.answer("Ящик не выбран")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, active_mailbox_id):
        await m.answer("❌ У вас нет прав для создания постов в этом ящике.")
        return
    
    _postpin_wait[m.from_user.id] = active_mailbox_id
    await m.answer("Пришлите текст закрепа. Я добавлю deeplink и закреплю в канале.")

async def on_postpin_text(m: types.Message, db):
    logging.info(f"🚨 POSTPIN FILTER CHECK: User {m.from_user.id}, text: '{m.text}', in _postpin_wait: {m.from_user.id in _postpin_wait}")
    
    if m.from_user.id not in _postpin_wait:
        return
    
    logging.info(f"🚨 POSTPIN HANDLER: User {m.from_user.id} in _postpin_wait, text: '{m.text}'")
    
    # Проверяем, что это не команда
    if m.text and m.text.startswith('/'):
        return
    
    # Проверяем, что сообщение содержит текст
    if not m.text or not m.text.strip():
        await m.answer("Пожалуйста, отправьте текст для закрепа.")
        return
    
    mailbox_id = _postpin_wait.pop(m.from_user.id)

    # Получаем канал ящика
    from app.infra.repo.mailboxes_repo import MailboxesRepo
    box = await MailboxesRepo(db).get(mailbox_id)
    if not box:
        await m.answer("Не найден ящик.")
        return
    _, _, channel_id, _, _, _ = box

    # Генерируем deeplink (payload = mailbox_id)
    try:
        me = await m.bot.get_me()
        username = me.username
        payload = str(mailbox_id)
        deeplink = f"https://t.me/{username}?start={payload}"

        # Создаем кнопку с deeplink
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Написать", url=deeplink)]
        ])
        
        # Публикуем в канал и закрепляем
        text_to_post = f"{m.text}"
        msg = await m.bot.send_message(channel_id, text_to_post, reply_markup=keyboard, disable_web_page_preview=True)
        try:
            await m.bot.pin_chat_message(channel_id, msg.message_id)
        except TelegramAPIError:
            pass  # Игнорируем ошибки закрепления
        else:
            try:
                await m.bot.delete_message(channel_id, msg.message_id + 1)
            except TelegramAPIError:
                pass  # Игнорируем ошибки удаления сервисного сообщения
        await m.answer("Готово: пост отправлен и закреплён.")
    except TelegramAPIError as e:
        await m.answer(f"❌ Ошибка при отправке поста: {e}")
