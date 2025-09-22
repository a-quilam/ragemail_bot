from aiogram import types
from app.keyboards.settings import settings_kb
from app.core.config import settings
from app.infra.repo.users_repo import UsersRepo

async def on_settings_button(m: types.Message, db):
    # Проверяем роль в БД
    role = await UsersRepo(db).get_role(m.from_user.id)
    is_superadmin = bool(settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID)
    if role not in ("admin", "superadmin") and not is_superadmin:
        await m.answer("У вас нет доступа к этой функции.")
        return
    await m.answer("Привет, админ! Что хочешь сделать?", reply_markup=settings_kb(is_superadmin))
