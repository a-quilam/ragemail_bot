"""
Автоматическое обнаружение каналов через my_chat_member
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramAPIError

router = Router(name=__name__)

ADMIN_STATUSES = {"administrator", "creator"}
JOIN_STATUSES = {"member"}            # на всякий случай, если добавили без прав
LEFT_STATUSES = {"left", "kicked"}

def _chat_label(chat) -> str:
    """Форматирование названия чата"""
    tag = f"@{chat.username}" if chat.username else f"id:{chat.id}"
    return f"«{chat.title}» ({tag})"

@router.my_chat_member(F.chat.type.in_({"channel", "supergroup", "group"}))
async def on_bot_adminized(event: ChatMemberUpdated, bot: Bot):
    """Авто-детект: бота добавили/повысили → уведомить инициатора."""
    old = event.old_chat_member.status
    new = event.new_chat_member.status

    # Интересны случаи, когда бот стал админом (или просто добавлен)
    became_admin = (new in ADMIN_STATUSES) and (old not in ADMIN_STATUSES)
    just_added = (new in JOIN_STATUSES) and (old in LEFT_STATUSES)

    if not (became_admin or just_added):
        return

    # Уточним реальные права бота (бывает, что статус сменился, но прав нет)
    try:
        me = await bot.get_chat_member(event.chat.id, bot.id)
    except TelegramBadRequest:
        return

    is_admin = getattr(me, "status", "") in ADMIN_STATUSES
    try:
        chat = await bot.get_chat(event.chat.id)
    except TelegramAPIError as e:
        logging.error(f"Failed to get chat info for {event.chat.id}: {e}")
        return

    # Кого уведомлять: инициатора изменения статуса (тот, кто добавил/повысил)
    actor = event.from_user
    if not actor:
        return

    # Логируем событие
    logging.info(f"Bot status changed in {_chat_label(chat)}: {old} -> {new}, is_admin: {is_admin}")

    # Логируем информацию о канале
    if is_admin:
        try:
            from app.services.channel_tracker import ChannelTracker
            from app.infra.db_pool import get_db
            db = await get_db()
            tracker = ChannelTracker(db)
            await tracker.track_channel_addition(bot, event.chat.id, actor.id)
        except Exception as e:
            logging.error(f"Error tracking channel addition: {e}")

    # Тексты
    if is_admin:
        text = (
            "✅ Я теперь **админ** в канале/чате {chat}.\n\n"
            "Доступные права:\n"
            "• постинг: {post}\n"
            "• редактирование: {edit}\n"
            "• удаление: {del_}\n"
            "• приглашения: {invite}\n"
            "• закрепление: {pin}\n\n"
            "Теперь вы можете создать почтовый ящик в этом канале!"
        ).format(
            chat=_chat_label(chat),
            post=getattr(me, "can_post_messages", False),
            edit=getattr(me, "can_edit_messages", False),
            del_=getattr(me, "can_delete_messages", False),
            invite=getattr(me, "can_invite_users", False),
            pin=getattr(me, "can_pin_messages", False),
        )
    else:
        text = (
            "ℹ️ Меня добавили в {chat}, но прав администратора пока нет. "
            "Дай права, если нужно публиковать/модерировать."
        ).format(chat=_chat_label(chat))

    # Шлём в личку актору, только если он уже начинал диалог с ботом
    try:
        await bot.send_message(actor.id, text, parse_mode="Markdown")
        logging.info(f"Sent notification to user {actor.id} about channel {chat.id}")
    except TelegramForbiddenError:
        # Пользователь не писал боту — молча игнорируем/логируем
        logging.info(f"Could not send notification to user {actor.id} - bot not started")
        pass
