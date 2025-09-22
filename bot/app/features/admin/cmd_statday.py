from aiogram import types
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.utils.mailbox_permissions import can_manage_mailbox
from app.core.constants import DAYS_OF_WEEK

async def cmd_statday(m: types.Message, db, active_mailbox_id: int):
    if not m.text or not m.text.startswith("/statday"):
        return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await m.answer("❌ <b>Неверный формат команды</b>\n\n📝 <b>Использование:</b> <code>/statday 1-7</code>\n\n💡 <b>Примеры:</b>\n<code>/statday 1</code> - понедельник\n<code>/statday 7</code> - воскресенье", parse_mode="HTML")
        return
    day = int(parts[1])
    if day < 1 or day > 7:
        await m.answer("❌ <b>Неверный день недели</b>\n\n📅 <b>Допустимые значения:</b> 1-7\n\n💡 <b>Где:</b>\n1 - понедельник\n7 - воскресенье", parse_mode="HTML")
        return
    if not active_mailbox_id:
        await m.answer("Ящик не выбран")
        return
    
    # Проверяем права доступа к ящику
    if not await can_manage_mailbox(db, m.from_user.id, active_mailbox_id):
        await m.answer("❌ У вас нет прав для настройки статистики этого ящика.")
        return
    
    box = await MailboxesRepo(db).get(active_mailbox_id)
    current_time = box[4] if box and len(box) > 4 else "10:00"
    await MailboxesRepo(db).set_stats_schedule(active_mailbox_id, day, current_time)
    
    # Преобразуем день в название
    day_name = DAYS_OF_WEEK[day]
    
    await m.answer(f"✅ <b>Статистика настроена</b>\n\n📅 День: {day_name}\n⏰ Время: {current_time}\n\n💡 <i>Статистика будет автоматически отправляться в канал каждую неделю</i>", parse_mode="HTML")
