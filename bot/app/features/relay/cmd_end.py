from aiogram import types
from aiogram.enums import ChatType
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo

async def cmd_end(m: types.Message, db, bot):
    if m.chat.type == ChatType.PRIVATE:
        await RelayService(bot, RelaysRepo(db)).end_for(m.from_user.id)
        await m.answer("🔒 Диалог завершен.")
