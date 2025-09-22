from aiogram import types
from aiogram.fsm.context import FSMContext

async def cb_delete_draft(c: types.CallbackQuery, state: FSMContext):
    if not c.data.startswith("delete_draft:"):
        return
    await state.clear()
    await c.message.edit_text("Черновик удалён. Нажмите «Написать письмо», чтобы начать заново.")
    await c.answer()
