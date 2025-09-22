from aiogram import Bot

async def resolve_channel_id(bot: Bot, kind: str, value: str) -> int:
    if kind == "id":
        return int(value)
    if kind == "internal":
        # -100 + internal id for supergroups/channels
        return int("-100" + value)
    if kind == "username":
        chat = await bot.get_chat("@" + value)
        return chat.id
    raise ValueError("Неизвестный тип ссылки")

async def bot_is_admin(bot: Bot, channel_id: int) -> bool:
    me = await bot.get_me()
    try:
        member = await bot.get_chat_member(channel_id, me.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def user_is_member(bot: Bot, channel_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def user_can_create_mailbox_in_channel(bot: Bot, channel_id: int, user_id: int) -> bool:
    """
    Проверить, может ли пользователь создать ящик в канале.
    Пользователь должен быть администратором или создателем канала.
    """
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
