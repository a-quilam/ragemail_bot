from aiogram import types
from aiogram.fsm.context import FSMContext
from app.keyboards.write_flow import start_kb_admin, start_kb
from app.core.config import settings
from app.infra.repo.users_repo import UsersRepo

async def on_back_button(m: types.Message, state: FSMContext, db):
    await state.clear()
    
    # Проверяем роль в базе данных
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(m.from_user.id)
    is_superadmin = bool(settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
    is_admin = role in ("admin", "superadmin") or is_superadmin
    
    if is_admin:
        kb = start_kb_admin()
        await m.answer(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=kb
        )
    else:
        kb = start_kb()
        await m.answer("🏠 Вы в главном меню.", reply_markup=kb)
