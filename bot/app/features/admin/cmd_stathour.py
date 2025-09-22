from aiogram import types
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.utils.mailbox_permissions import can_manage_mailbox
from app.core.constants import DAYS_OF_WEEK

async def cmd_stathour(m: types.Message, db, active_mailbox_id: int):
    if not m.text or not m.text.startswith("/stathour"):
        return
    parts = m.text.split()
    if len(parts) != 2 or len(parts[1]) != 5 or parts[1][2] != ":":
        await m.answer("❌ <b>Неверный формат команды</b>\n\n📝 <b>Использование:</b> <code>/stathour HH:MM</code>\n\n💡 <b>Примеры:</b>\n<code>/stathour 10:00</code>\n<code>/stathour 14:30</code>", parse_mode="HTML")
        return
    if not active_mailbox_id:
        await m.answer("Ящик не выбран")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, active_mailbox_id):
        await m.answer("❌ У вас нет прав для настройки статистики этого ящика.")
        return
    
    box = await MailboxesRepo(db).get(active_mailbox_id)
    current_day = box[3] if box and len(box) > 3 else 1
    
    # Проверяем, что current_day не None и является валидным индексом
    if current_day is None or not isinstance(current_day, int) or current_day < 1 or current_day > 7:
        current_day = 1  # Устанавливаем понедельник по умолчанию
    
    await MailboxesRepo(db).set_stats_schedule(active_mailbox_id, current_day, parts[1])
    
    # Преобразуем день в название
    day_name = DAYS_OF_WEEK[current_day - 1]  # Индексы в списке начинаются с 0
    
    await m.answer(f"✅ <b>Статистика настроена</b>\n\n📅 День: {day_name}\n⏰ Время: {parts[1]}\n\n💡 <i>Статистика будет автоматически отправляться в канал каждую неделю</i>", parse_mode="HTML")
