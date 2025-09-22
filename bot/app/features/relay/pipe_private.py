from aiogram import types
from aiogram.enums import ChatType
from app.services.relay_service import RelayService
from app.infra.repo.relays_repo import RelaysRepo
from app.infra.repo.stats_repo import StatsRepo
from app.services.stats_service import StatsService
from zoneinfo import ZoneInfo

async def pipe(m: types.Message, db, bot, tz: ZoneInfo):
    if m.chat.type != ChatType.PRIVATE or not (m.text and m.text.strip()):
        return
    # Пропускаем команды
    if m.text.startswith('/'):
        return
    ok = await RelayService(bot, RelaysRepo(db)).pipe(m.from_user.id, m.text)
    if ok:
        try:
            await StatsService(StatsRepo(db), tz).inc("relay_msg")
        except Exception:
            pass
        return
    # иначе — сообщение пойдёт в обработчики write
