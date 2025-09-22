import time
from aiogram import types
from aiogram.fsm.context import FSMContext
from zoneinfo import ZoneInfo
from app.keyboards.common import delayed_cancel_kb

async def cb_send_delay(c: types.CallbackQuery, state: FSMContext, db, tz: ZoneInfo, active_mailbox_id: int):
    if not c.data.startswith("send_delay:"):
        return
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if draft_id is None or f"send_delay:{draft_id}" != c.data:
        await c.answer("Черновик устарел.", show_alert=True)
        return
    text = data.get("text","")
    ttl = data.get("ttl", 15*60)
    alias = data.get("alias", "Аноним")
    mailbox_id = active_mailbox_id
    run_at = int(time.time()) + 2*60
    cur = await db.execute(
        "INSERT INTO delayed_queue(user_id, mailbox_id, text, ttl_seconds, alias, run_at) VALUES(?,?,?,?,?,?)",
        (c.from_user.id, mailbox_id, text, ttl, alias, run_at),
    )
    await db.commit()
    item_id = cur.lastrowid
    await c.message.edit_text("Хорошо, отправлю через 2 минуты")
    await c.message.answer("Вы можете отменить отложенную отправку:", reply_markup=delayed_cancel_kb(item_id))
    await c.answer()

async def cb_cancel_delay(c: types.CallbackQuery, db):
    if not c.data.startswith("cancel_delay:"):
        return
    item_id = int(c.data.split(":")[1])
    await db.execute("DELETE FROM delayed_queue WHERE id=?", (item_id,))
    await db.commit()
    await c.message.edit_text("Отложенная отправка отменена и черновик удалён.")
    await c.answer()
