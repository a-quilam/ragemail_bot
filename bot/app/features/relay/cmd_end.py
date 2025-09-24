from aiogram import types
from aiogram.enums import ChatType
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo

async def cmd_end(m: types.Message, db, bot):
    if m.chat.type == ChatType.PRIVATE:
        peer_alias = await RelayService(bot, RelaysRepo(db)).end_for(m.from_user.id)
        if peer_alias:
            await m.answer(f"🔒 Диалог с «{peer_alias}» завершен.")
        else:
            await m.answer("🔒 Активных анонимных диалогов не найдено.")
