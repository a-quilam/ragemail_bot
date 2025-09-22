from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from app.keyboards.write_flow import start_kb, start_kb_admin
from app.texts.help_admin import HELP_ADMIN
from app.core.config import settings
from app.core.version import get_version_with_date
from app.infra.repo.users_repo import UsersRepo
from app.utils.error_handler import safe_async, handle_error
import logging

router = Router()

async def is_admin_db(message, db) -> bool:
    try:
        from app.utils.role_cache import get_role_cache
        role_cache = get_role_cache()
        role = await role_cache.get_role(message.from_user.id, UsersRepo(db).get_role)
    except Exception:
        role = "user"
    return role in ("admin", "superadmin") or (settings.SUPERADMIN_ID and message.from_user.id == settings.SUPERADMIN_ID)

@router.message(CommandStart())
async def cmd_start(m: types.Message, state: FSMContext, db) -> None:
    try:
        logging.info(f"START COMMAND RECEIVED from user {m.from_user.id}")
        
        # Проверяем, есть ли параметры в команде /start
        if m.text and len(m.text.split()) > 1:
            # Если есть параметры, это deeplink - пропускаем обработку
            # bind_router должен обработать это
            logging.info(f"START COMMAND with payload detected, skipping: '{m.text}'")
            return
        
        await state.clear()
        
        # Создаем пользователя в базе данных если его нет (не сбрасываем роль)
        users_repo = UsersRepo(db)
        # Проверяем, есть ли пользователь в базе
        if not await users_repo.get(m.from_user.id):
            # Создаем только если пользователя нет в базе
            await users_repo.upsert(m.from_user.id, username=m.from_user.username)
        else:
            # Обновляем username если он изменился
            await users_repo.update_username(m.from_user.id, m.from_user.username)
        
        # Логируем ID пользователя для отладки
        logging.info(f"SUPERADMIN_ID from config: {settings.SUPERADMIN_ID}")
        admin_flag = await is_admin_db(m, db)
        logging.info(f"Is admin: {admin_flag}")
        
        kb = start_kb_admin() if admin_flag else start_kb()
        if admin_flag:
            version = get_version_with_date()
            await m.answer(
                f"🤖 <b>{version}</b>\n\n"
                "👋 <b>Привет, админ!</b>\n\n"
                "Добро пожаловать в панель управления ботом «Злое письмо».\n\n"
                "📋 <b>Доступные действия:</b>\n"
                "✍️ <b>Написать письмо</b> — создать анонимное сообщение\n"
                "⚙️ <b>Настройки</b> — управление ящиками и пользователями\n"
                "📊 <b>Статистика</b> — просмотр статистики\n"
                "📌 <b>Закрепить пост</b> — создать deeplink-пост\n"
                "🔄 <b>Обновить</b> — синхронизация с каналом\n\n"
                "💡 <i>Используйте кнопки ниже для навигации</i>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            version = get_version_with_date()
            await m.answer(
                f"🤖 <b>{version}</b>\n\n"
                "👋 <b>Привет!</b>\n\n"
                "Добро пожаловать в бот «Злое письмо»!\n\n"
                "📝 <b>Как это работает:</b>\n"
                "1. Просто напишите ваше сообщение\n"
                "2. Опишите ситуацию анонимно\n"
                "3. Выберите время жизни поста\n"
                "4. Ваше сообщение появится в канале\n\n"
                "🔒 <i>Ваша личность остается полностью анонимной</i>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        logging.info("START COMMAND RESPONSE SENT")
    except Exception as e:
        logging.error(f"ERROR in cmd_start: {e}", exc_info=True)
        await m.answer(f"Ошибка: {e}")

@router.message(Command("help"))
async def cmd_help(m: types.Message, db) -> None:
    is_admin = await is_admin_db(m, db)
    
    if is_admin:
        help_text = (
            "👋 <b>Справка для администратора</b>\n\n"
            "📋 <b>Основные команды:</b>\n"
            "• <code>/start</code> — главное меню\n"
            "• <code>/help</code> — эта справка\n"
            "• <code>/cancel</code> — отмена текущего действия\n\n"
            "⚙️ <b>Админские функции:</b>\n"
            "• <code>/backup</code> — создать резервную копию\n"
            "• <code>/restore</code> — восстановить из бэкапа\n"
            "• <code>/antispam</code> — управление антиспамом\n"
            "• <code>/postpin</code> — закрепить пост с deeplink\n"
            "• <code>/refresh</code> — обновить данные\n\n"
            "🛡️ <b>Антиспам команды:</b>\n"
            "• <code>/block слово [причина] [часы]</code> — заблокировать слово\n"
            "• <code>/unblock слово</code> — разблокировать слово\n"
            "• <code>/blocks</code> — показать все блокировки\n"
            "• <code>/cooldown псевдоним [часы] [причина]</code> — кулдаун\n"
            "• <code>/remove_cooldown user_id</code> — снять кулдаун\n"
            "• <code>/cooldowns</code> — показать кулдауны\n\n"
            "💡 <i>Используйте кнопки в меню для удобной навигации</i>"
        )
    else:
        help_text = (
            "👋 <b>Справка для пользователя</b>\n\n"
            "📋 <b>Основные команды:</b>\n"
            "• <code>/start</code> — главное меню\n"
            "• <code>/help</code> — эта справка\n"
            "• <code>/cancel</code> — отмена текущего действия\n\n"
            "✍️ <b>Как написать анонимное сообщение:</b>\n"
            "1. Просто напишите текст сообщения\n"
            "2. Выберите время жизни поста (15 минут — 24 часа)\n"
            "3. Ваше сообщение появится в канале под псевдонимом\n\n"
            "💬 <b>Анонимное общение:</b>\n"
            "• Нажмите «💬 Поговорить» под любым постом\n"
            "• Диалог будет активен 30 минут\n"
            "• Используйте <code>/end</code> для завершения\n\n"
            "🔒 <b>Ваша анонимность:</b>\n"
            "• Каждый день у вас новый псевдоним\n"
            "• Ваша личность остается полностью скрытой\n"
            "• Сообщения автоматически удаляются\n\n"
            "💡 <i>Просто напишите текст боту, и он отправит его анонимно!</i>"
        )
    
    await m.answer(help_text, parse_mode="HTML")

@router.message(Command("cancel"))
async def cmd_cancel(m: types.Message, state: FSMContext, db) -> None:
    await state.clear()
    kb = start_kb_admin() if await is_admin_db(m, db) else start_kb()
    await m.answer("Действие отменено. Вы в главном меню.", reply_markup=kb)

# Отладочный хендлер удален - теперь сообщения будут обрабатываться другими роутерами
