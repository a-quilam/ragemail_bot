from aiogram import types
from aiogram.fsm.context import FSMContext
from app.fsm.write_states import WriteStates
from zoneinfo import ZoneInfo
import time
import logging
from app.texts.previews import build_ttl_preview
from app.keyboards.ttl_selection import ttl_selection_kb
from app.keyboards.common import preview_kb

DEFAULT_TTL = 20 * 60  # 20 минут
MAX_TTL = 48 * 60 * 60

async def on_ttl_add(cb: types.CallbackQuery, state: FSMContext, tz: ZoneInfo):
    try:
        seconds_to_add = int(cb.data.split(":")[1])
        data = await state.get_data()
        current_ttl = data.get("current_ttl", DEFAULT_TTL)
        new_ttl = min(current_ttl + seconds_to_add, MAX_TTL)
        
        # Округляем до 5 минут
        current_time = int(time.time())
        rounded_time = (current_time // 300) * 300  # 300 секунд = 5 минут
        delete_at = rounded_time + new_ttl
        await state.update_data(current_ttl=new_ttl, delete_at=delete_at)

        preview = build_ttl_preview(data.get("alias", ""), data.get("text", ""), delete_at, tz)
        await cb.message.edit_text(preview, reply_markup=ttl_selection_kb(new_ttl, MAX_TTL, tz))
        await cb.answer()
    except Exception as e:
        import logging
        logging.error(f"Error in on_ttl_add: {e}", exc_info=True)
        await cb.answer("Ошибка при выборе времени", show_alert=True)

async def on_ttl_done(cb: types.CallbackQuery, state: FSMContext, tz: ZoneInfo):
    try:
        data = await state.get_data()
        draft_id = int(time.time()*1000) % 10**9
        await state.update_data(draft_id=draft_id)
        await state.set_state(WriteStates.PREVIEW)
        await cb.message.edit_reply_markup(reply_markup=preview_kb(draft_id))
        await cb.answer("Время выбрано!")
    except Exception as e:
        import logging
        logging.error(f"Error in on_ttl_done: {e}", exc_info=True)
        await cb.answer("Ошибка при завершении выбора времени", show_alert=True)

async def on_ttl_reset(cb: types.CallbackQuery, state: FSMContext, tz: ZoneInfo):
    try:
        data = await state.get_data()
        # Округляем до 5 минут
        current_time = int(time.time())
        rounded_time = (current_time // 300) * 300  # 300 секунд = 5 минут
        delete_at = rounded_time + DEFAULT_TTL
        await state.update_data(current_ttl=DEFAULT_TTL, delete_at=delete_at)

        preview = build_ttl_preview(data.get("alias", ""), data.get("text", ""), delete_at, tz)
        await cb.message.edit_text(preview, reply_markup=ttl_selection_kb(DEFAULT_TTL, MAX_TTL, tz))
        await cb.answer("Сброшено к 20 минутам")
    except Exception as e:
        import logging
        logging.error(f"Error in on_ttl_reset: {e}", exc_info=True)
        await cb.answer("Ошибка при сбросе времени", show_alert=True)
