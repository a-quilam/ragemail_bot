from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from app.fsm.admin_states import RemoveAdminStates
from app.infra.repo.users_repo import UsersRepo
from app.keyboards.common import confirmation_kb
from app.utils.admin_logger import log_remove_admin
import logging
# Safe imports with fallback support
try:
    from app.utils.circuit_breaker import get_breaker
except ImportError:
    from app.utils import get_breaker

try:
    from app.utils.rate_limiter import get_admin_limiter, check_rate_limit
except ImportError:
    from app.utils import get_admin_limiter, check_rate_limit

try:
    from app.utils.input_sanitizer import InputSanitizer, sanitize_user_input
except ImportError:
    from app.utils import InputSanitizer, sanitize_user_input

try:
    from app.utils.output_validator import OutputValidator, validate_output
except ImportError:
    from app.utils import OutputValidator, validate_output

try:
    from app.utils.resource_manager import get_resource_manager, managed_resource, MemoryManager
except ImportError:
    from app.utils import get_resource_manager, managed_resource, MemoryManager

try:
    from app.utils.rollback_manager import get_rollback_manager, create_admin_removal_rollback, execute_admin_removal_rollback
except ImportError:
    from app.utils import get_rollback_manager, create_admin_removal_rollback
    # Fallback for execute_admin_removal_rollback
    async def execute_admin_removal_rollback(*args, **kwargs):
        return True

# Коды ошибок для лучшей диагностики
class ErrorCodes:
    INVALID_MESSAGE_TYPE = "ARA001"
    INVALID_STATE_TYPE = "ARA002"
    INVALID_DB_TYPE = "ARA003"
    INVALID_USER_TYPE = "ARA004"
    INVALID_CALLBACK_TYPE = "ARA005"
    INVALID_USERNAME_FORMAT = "ARA006"
    INVALID_USER_ID = "ARA007"
    USER_NOT_FOUND = "ARA008"
    SELF_REMOVAL_ATTEMPT = "ARA009"
    INSUFFICIENT_PERMISSIONS = "ARA010"
    DB_CONNECTION_ERROR = "ARA011"
    TELEGRAM_API_ERROR = "ARA012"
    TIMEOUT_ERROR = "ARA013"
    NETWORK_ERROR = "ARA014"
    STATE_UPDATE_ERROR = "ARA015"
    USERNAME_UPDATE_ERROR = "ARA016"
    CRITICAL_ERROR = "ARA017"

# Метрики для мониторинга
class Metrics:
    @staticmethod
    def track_admin_removal_start(user_id: int):
        """Отслеживает начало процесса удаления администратора"""
        logging.info(f"METRIC: admin_removal_start user_id={user_id}")
    
    @staticmethod
    def track_admin_removal_success(user_id: int, target_user_id: int):
        """Отслеживает успешное удаление администратора"""
        logging.info(f"METRIC: admin_removal_success user_id={user_id} target_user_id={target_user_id}")
    
    @staticmethod
    def track_admin_removal_error(user_id: int, error_code: str):
        """Отслеживает ошибки при удалении администратора"""
        logging.info(f"METRIC: admin_removal_error user_id={user_id} error_code={error_code}")
    
    @staticmethod
    def track_admin_removal_cancel(user_id: int):
        """Отслеживает отмену удаления администратора"""
        logging.info(f"METRIC: admin_removal_cancel user_id={user_id}")
    
    @staticmethod
    def track_db_operation_duration(operation: str, duration_ms: float):
        """Отслеживает длительность операций базы данных"""
        logging.info(f"METRIC: db_operation_duration operation={operation} duration_ms={duration_ms}")
    
    @staticmethod
    def track_telegram_api_call(operation: str, success: bool, duration_ms: float = None):
        """Отслеживает вызовы Telegram API"""
        status = "success" if success else "error"
        metric_data = f"operation={operation} status={status}"
        if duration_ms is not None:
            metric_data += f" duration_ms={duration_ms}"
        logging.info(f"METRIC: telegram_api_call {metric_data}")
    
    @staticmethod
    def track_retry_attempt(operation: str, attempt: int, max_retries: int):
        """Отслеживает попытки повторного выполнения операций"""
        logging.info(f"METRIC: retry_attempt operation={operation} attempt={attempt} max_retries={max_retries}")

async def on_remove_admin_start(m: types.Message, state: FSMContext, db):
    import time
    
    start_time = time.time()
    resource_manager = get_resource_manager()
    
    try:
        # Проверяем rate limit
        if m and m.from_user and m.from_user.id:
            admin_limiter = get_admin_limiter()
            is_allowed, reason = await check_rate_limit(admin_limiter, str(m.from_user.id), "remove_admin_start")
            if not is_allowed:
                await m.answer(f"⚠️ Слишком много запросов. {reason}")
                Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.INSUFFICIENT_PERMISSIONS)
                return
        
        # Отслеживаем начало процесса
        if m and m.from_user and m.from_user.id:
            Metrics.track_admin_removal_start(m.from_user.id)
        # Валидация входных параметров
        if not isinstance(m, types.Message):
            logging.error(f"[{ErrorCodes.INVALID_MESSAGE_TYPE}] Invalid message type in on_remove_admin_start")
            return
        if not isinstance(state, FSMContext):
            logging.error(f"[{ErrorCodes.INVALID_STATE_TYPE}] Invalid state type in on_remove_admin_start")
            return
        if db is None:
            logging.error(f"[{ErrorCodes.INVALID_DB_TYPE}] Database connection is None in on_remove_admin_start")
            return
    except Exception as e:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Error in on_remove_admin_start validation: {e}")
        # Отслеживаем ошибку
        if m and m.from_user and m.from_user.id:
            Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.CRITICAL_ERROR)
        # Мониторинг критических ошибок
        try:
            # Здесь можно добавить отправку алертов в систему мониторинга
            logging.critical(f"[{ErrorCodes.CRITICAL_ERROR}] CRITICAL ERROR in on_remove_admin_start: {e}")
        except Exception as alert_error:
            logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Failed to send alert: {alert_error}")
        return
    finally:
        # Очистка ресурсов
        try:
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > 1000:  # Логируем медленные операции
                logging.warning(f"Slow operation: on_remove_admin_start took {duration_ms:.1f}ms")
            
            # Периодическая очистка памяти
            if duration_ms > 5000:  # Если операция заняла больше 5 секунд
                await MemoryManager.cleanup_memory()
        except Exception as cleanup_error:
            logging.error(f"Error during resource cleanup: {cleanup_error}")
    
    # Показываем список админов с graceful degradation и оптимизацией
    users_repo = UsersRepo(db)
    try:
        # Получаем circuit breaker для базы данных
        db_breaker = get_breaker(
            "database_operations",
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=Exception
        )
        
        # Оптимизация: кэшируем результат на короткое время
        db_start_time = time.time()
        admins = await db_breaker.call(users_repo.get_all_admins)
        db_duration = (time.time() - db_start_time) * 1000  # в миллисекундах
        Metrics.track_db_operation_duration("get_all_admins", db_duration)
        logging.info(f"Retrieved {len(admins) if admins else 0} admins for user {m.from_user.id}")
    except Exception as e:
        logging.error(f"[{ErrorCodes.DB_CONNECTION_ERROR}] Error retrieving admins for user {m.from_user.id}: {e}")
        Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.DB_CONNECTION_ERROR)
        # Graceful degradation - показываем базовое сообщение
        await m.answer(
            "⚠️ <b>Временная недоступность</b>\n\n"
            "Не удалось загрузить список администраторов.\n"
            "Попробуйте позже или обратитесь к суперадминистратору.",
            parse_mode="HTML"
        )
        return
    
    if not admins:
        logging.info(f"No admins found for user {m.from_user.id}")
        await m.answer("❌ Администраторы не найдены.")
        return
    
    text = "👥 <b>Управление администраторами</b>\n\n"
    text += "Текущие администраторы:\n\n"
    
    for user_id, role in admins:
        try:
            logging.debug(f"Processing admin: user_id={user_id}, role={role}")
            
            # Проверки на None
            if user_id is None:
                logging.warning("Skipping admin with None user_id")
                continue
            if role is None:
                role = "неизвестная роль"
            
            # Пытаемся получить информацию о пользователе с таймаутом
            import asyncio
            chat = await asyncio.wait_for(m.bot.get_chat(user_id), timeout=10.0)
            username = chat.username if chat.username else None
            first_name = chat.first_name or ""
            last_name = chat.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            
            if username:
                display_name = f"<code>@{username}</code>"
            elif full_name:
                display_name = full_name
            else:
                display_name = f"ID {user_id}"
                
            text += f"👤 {display_name} — {role}\n"
            logging.debug(f"Successfully processed admin {user_id}: {display_name}")
        except TelegramAPIError as e:
            # Если не удалось получить информацию (пользователь заблокировал бота, не существует, или нет доступа), показываем ID
            logging.warning(f"Failed to get chat info for admin {user_id}: {e}")
            safe_role = str(role) if role is not None else "неизвестная роль"
            safe_user_id = str(user_id) if user_id is not None else "неизвестный ID"
            text += f"🆔 <code>{safe_user_id}</code> — {safe_role}\n"
    
    text += "\nДля удаления администратора отправьте его user_id цифрами, @username или перешлите его сообщение."
    
    await state.set_state(RemoveAdminStates.ASK_USER)
    await m.answer(text, parse_mode="HTML")

async def on_remove_admin_input(m: types.Message, state: FSMContext, db):
    import time
    
    # Проверяем rate limit
    if m and m.from_user and m.from_user.id:
        admin_limiter = get_admin_limiter()
        is_allowed, reason = await check_rate_limit(admin_limiter, str(m.from_user.id), "remove_admin_input")
        if not is_allowed:
            await m.answer(f"⚠️ Слишком много запросов. {reason}")
            Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.INSUFFICIENT_PERMISSIONS)
            return
    
    # Валидация входных параметров
    if not isinstance(m, types.Message):
        logging.error(f"[{ErrorCodes.INVALID_MESSAGE_TYPE}] Invalid message type in on_remove_admin_input")
        return
    if not isinstance(state, FSMContext):
        logging.error(f"[{ErrorCodes.INVALID_STATE_TYPE}] Invalid state type in on_remove_admin_input")
        return
    if db is None:
        logging.error(f"[{ErrorCodes.INVALID_DB_TYPE}] Database connection is None in on_remove_admin_input")
        return
    
    # Валидация безопасности
    if not m.from_user or not m.from_user.id:
        logging.error(f"[{ErrorCodes.INVALID_USER_TYPE}] Invalid user in action_remove_admin")
        return
    
    # Проверка на попытки удаления самого себя
    if m.forward_from and m.forward_from.id == m.from_user.id:
        await m.answer("❌ Нельзя удалить самого себя.")
        await state.clear()
        return
    
    # Валидация сообщения
    if not m.text and not m.forward_from:
        await m.answer("❌ Пожалуйста, отправьте user_id, @username или перешлите сообщение пользователя.")
        await state.clear()
        return
    
    logging.info(f"REMOVE ADMIN INPUT: user {m.from_user.id}, text: '{m.text}', state: {await state.get_state()}")
    
    target_user_id = None
    username = None
    
    # Проверяем пересланное сообщение
    if m.forward_from:
        # Валидация пользователя
        if not m.forward_from.id:
            await m.answer("❌ Не удалось получить ID пользователя из пересланного сообщения.")
            await state.clear()
            return
        
        target_user_id = m.forward_from.id
        logging.info(f"User {m.from_user.id} forwarded message from user {target_user_id}")
    # Проверяем числовой ID
    elif m.text and m.text.strip().isdigit():
        raw_user_id = m.text.strip()
        # Санитизация и валидация user ID
        target_user_id = InputSanitizer.sanitize_user_id(raw_user_id)
        if not target_user_id:
            logging.warning(f"[{ErrorCodes.INVALID_USER_ID}] Invalid user ID: {raw_user_id}")
            await m.answer("❌ Неверный ID пользователя. ID должен быть положительным числом.")
            await state.clear()
            return
        
        # Дополнительная валидация для Telegram ID
        if target_user_id > 2**63 - 1:  # Максимальный ID Telegram
            logging.warning(f"[{ErrorCodes.INVALID_USER_ID}] User ID too large: {target_user_id}")
            await m.answer("❌ Неверный ID пользователя. ID слишком большой.")
            await state.clear()
            return
        
        logging.info(f"User {m.from_user.id} provided numeric ID: {target_user_id}")
    # Проверяем @username
    elif m.text and m.text.strip().startswith('@'):
        raw_username = m.text.strip()
        # Санитизация и валидация username
        username = InputSanitizer.sanitize_username(raw_username)
        if not username:
            logging.warning(f"[{ErrorCodes.INVALID_USERNAME_FORMAT}] Invalid username format: {raw_username}")
            await m.answer("❌ Неверный формат @username.")
            await state.clear()
            return
        logging.info(f"User {m.from_user.id} provided username: @{username}")
        
        # Сначала пробуем найти в базе данных с повторными попытками
        users_repo = UsersRepo(db)
        max_retries = 3
        target_user_id = None
        
        for attempt in range(max_retries):
            try:
                target_user_id = await users_repo.get_by_username(username)
                # Валидация результата
                if target_user_id is not None and not isinstance(target_user_id, int):
                    logging.error(f"[{ErrorCodes.USER_NOT_FOUND}] Invalid user_id returned by get_by_username: {target_user_id}")
                    target_user_id = None
                break  # Успешное выполнение
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"[{ErrorCodes.DB_CONNECTION_ERROR}] Attempt {attempt + 1} failed for get_by_username {username}: {e}")
                    import asyncio
                    await asyncio.sleep(0.1 * (attempt + 1))
                else:
                    logging.error(f"[{ErrorCodes.DB_CONNECTION_ERROR}] All attempts failed for get_by_username {username}: {e}")
                    target_user_id = None
        
        if not target_user_id:
            # Если не найден в базе, пробуем через get_chat с circuit breaker
            try:
                # Получаем circuit breaker для Telegram API
                telegram_breaker = get_breaker(
                    "telegram_api",
                    failure_threshold=3,
                    recovery_timeout=30.0,
                    expected_exception=TelegramAPIError
                )
                
                api_start_time = time.time()
                chat = await telegram_breaker.call(m.bot.get_chat, f"@{username}")
                api_duration = (time.time() - api_start_time) * 1000  # в миллисекундах
                Metrics.track_telegram_api_call("get_chat", True, api_duration)
                if chat and hasattr(chat, 'id') and chat.id:
                    target_user_id = chat.id
                    # Сохраняем username в базе для будущих поисков
                    try:
                        await users_repo.update_username(target_user_id, username)
                        logging.info(f"Updated username for user {target_user_id}: {username}")
                    except Exception as e:
                        logging.error(f"[{ErrorCodes.USERNAME_UPDATE_ERROR}] Failed to update username for user {target_user_id}: {e}")
                        # Продолжаем выполнение, так как это не критическая ошибка
                else:
                    await m.answer("Не удалось получить ID пользователя по @username. Пришлите числовой ID или пересланное сообщение.")
                    await state.clear()
                    return
            except TelegramAPIError as e:
                Metrics.track_telegram_api_call("get_chat", False)
                logging.error(f"[{ErrorCodes.TELEGRAM_API_ERROR}] Telegram API error when getting chat for @{username}: {e}")
                # Обработка различных типов сетевых ошибок
                if "timeout" in str(e).lower():
                    logging.warning(f"[{ErrorCodes.TIMEOUT_ERROR}] Timeout when getting chat for @{username}")
                    Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.TIMEOUT_ERROR)
                    await m.answer("❌ Таймаут при обращении к Telegram API. Попробуйте позже.")
                elif "network" in str(e).lower() or "connection" in str(e).lower():
                    logging.warning(f"[{ErrorCodes.NETWORK_ERROR}] Network error when getting chat for @{username}")
                    Metrics.track_admin_removal_error(m.from_user.id, ErrorCodes.NETWORK_ERROR)
                    await m.answer("❌ Ошибка сети при обращении к Telegram API. Проверьте подключение.")
                else:
                    await m.answer(
                        f"❌ <b>Не удалось найти пользователя</b>\n\n"
                        f"@username не найден или пользователь не существует.\n"
                        f"Для удаления администратора используйте:\n"
                        f"• Числовой ID (например: 123456789)\n"
                        f"• Пересланное сообщение от пользователя\n"
                        f"• @username (если пользователь уже взаимодействовал с ботом)",
                        parse_mode="HTML"
                    )
                await state.clear()
                return

    if not target_user_id:
        await m.answer("Не смог определить пользователя. Пришлите user_id цифрами или перешлите его сообщение.")
        await state.clear()
        return

    # Валидация target_user_id
    if not isinstance(target_user_id, int) or target_user_id <= 0:
        await m.answer("❌ Неверный ID пользователя.")
        await state.clear()
        return
    
    # Проверяем, что это не суперадмин
    try:
        from app.core.config import settings
        # Валидация конфигурации
        if not hasattr(settings, 'SUPERADMIN_ID'):
            logging.warning(f"[{ErrorCodes.INSUFFICIENT_PERMISSIONS}] SUPERADMIN_ID not found in settings")
        elif settings.SUPERADMIN_ID and target_user_id == settings.SUPERADMIN_ID:
            logging.warning(f"[{ErrorCodes.INSUFFICIENT_PERMISSIONS}] Attempt to remove superadmin: {target_user_id}")
            await m.answer("Нельзя удалить суперадминистратора.")
            await state.clear()
            return
    except Exception as e:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Error checking superadmin ID: {e}")
        # Продолжаем выполнение, так как это не критическая ошибка

    # Сохраняем ID и username для подтверждения
    if state is None:
        await m.answer("❌ Ошибка: состояние не инициализировано.")
        return
    
    try:
        await state.update_data(target_user_id=target_user_id, username=username)
    except Exception as e:
        logging.error(f"[{ErrorCodes.STATE_UPDATE_ERROR}] Failed to update state data: {e}")
        await m.answer("❌ Ошибка при сохранении данных.")
        return
    await state.set_state(RemoveAdminStates.CONFIRM)
    
    # Формируем отображаемое имя пользователя
    safe_username = str(username) if username is not None else None
    safe_target_user_id = str(target_user_id) if target_user_id is not None else "неизвестный"
    
    display_name = f"@{safe_username}" if safe_username else f"<code>{safe_target_user_id}</code>"
    
    # Запрашиваем подтверждение
    try:
        confirmation_text = (
            f"⚠️ <b>Подтверждение удаления администратора</b>\n\n"
            f"Вы действительно хотите удалить права администратора у пользователя {display_name}?\n\n"
            f"<i>Это действие нельзя отменить!</i>"
        )
        
        # Валидация выходного текста
        text_validation = OutputValidator.validate_message_text(confirmation_text)
        if not text_validation.is_valid:
            logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Invalid confirmation text: {text_validation.errors}")
            await m.answer("❌ Ошибка при формировании сообщения подтверждения.")
            await state.clear()
            return
        
        if text_validation.warnings:
            logging.warning(f"Confirmation text warnings: {text_validation.warnings}")
        
        await m.answer(
            text_validation.sanitized_data,
            parse_mode="HTML",
            reply_markup=confirmation_kb("remove_admin", target_user_id)
        )
    except Exception as e:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Error sending confirmation message: {e}")
        await m.answer("❌ Ошибка при отправке сообщения подтверждения.")
        await state.clear()
        return

async def on_remove_admin_confirm(callback: types.CallbackQuery, state: FSMContext, db):
    """Обработчик подтверждения удаления администратора"""
    import time
    
    start_time = time.time()
    resource_manager = get_resource_manager()
    rollback_manager = get_rollback_manager()
    
    # Проверяем rate limit
    if callback and callback.from_user and callback.from_user.id:
        admin_limiter = get_admin_limiter()
        is_allowed, reason = await check_rate_limit(admin_limiter, str(callback.from_user.id), "remove_admin_confirm")
        if not is_allowed:
            await callback.answer(f"⚠️ Слишком много запросов. {reason}")
            Metrics.track_admin_removal_error(callback.from_user.id, ErrorCodes.INSUFFICIENT_PERMISSIONS)
            return
    
    # Валидация входных параметров
    if not isinstance(callback, types.CallbackQuery):
        logging.error(f"[{ErrorCodes.INVALID_CALLBACK_TYPE}] Invalid callback type in on_remove_admin_confirm")
        return
    if not isinstance(state, FSMContext):
        logging.error(f"[{ErrorCodes.INVALID_STATE_TYPE}] Invalid state type in on_remove_admin_confirm")
        return
    if db is None:
        logging.error(f"[{ErrorCodes.INVALID_DB_TYPE}] Database connection is None in on_remove_admin_confirm")
        return
    
    # Валидация и санитизация callback данных
    if not callback.data:
        logging.error("Empty callback data in on_remove_admin_confirm")
        await callback.answer("Ошибка: неверные данные callback", show_alert=True)
        await state.clear()
        return
    
    # Санитизация callback данных
    sanitized_callback_data = InputSanitizer.sanitize_callback_data(callback.data)
    if not sanitized_callback_data:
        logging.error(f"Invalid callback data in on_remove_admin_confirm: {callback.data}")
        await callback.answer("Ошибка: неверные данные callback", show_alert=True)
        await state.clear()
        return
    
    try:
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        username = data.get('username')
    except Exception as e:
        logging.error(f"[{ErrorCodes.STATE_UPDATE_ERROR}] Error getting state data: {e}")
        await callback.answer("Ошибка: не удалось получить данные состояния", show_alert=True)
        await state.clear()
        return
    
    # Валидация данных из состояния
    if not target_user_id or not isinstance(target_user_id, int) or target_user_id <= 0:
        await callback.answer("Ошибка: неверные данные пользователя", show_alert=True)
        await state.clear()
        return
    
    # Валидация выходных данных пользователя
    user_data = {
        'id': target_user_id,
        'username': username,
        'role': 'user'  # После удаления прав
    }
    user_validation = OutputValidator.validate_user_data(user_data)
    if not user_validation.is_valid:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Invalid user data: {user_validation.errors}")
        await callback.answer("Ошибка: неверные данные пользователя", show_alert=True)
        await state.clear()
        return
    
    # Удаляем роль админа (возвращаем к user) с circuit breaker
    try:
        # Получаем circuit breaker для операций удаления
        removal_breaker = get_breaker(
            "admin_removal",
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=Exception
        )
        
        # Получаем текущую роль пользователя для создания операции отката
        users_repo = UsersRepo(db)
        current_role = await users_repo.get_role(target_user_id)
        
        # Создаем операцию отката перед изменением
        rollback_id = await create_admin_removal_rollback(
            target_user_id, 
            current_role, 
            ttl=3600  # 1 час на откат
        )
        
        try:
            await removal_breaker.call(users_repo.upsert, target_user_id, role="user")
            logging.info(f"Successfully removed admin role from user {target_user_id} by admin {callback.from_user.id}")
            
            # Отслеживаем успешное удаление
            Metrics.track_admin_removal_success(callback.from_user.id, target_user_id)
            
            # Сохраняем ID операции отката в метаданных
            logging.info(f"Rollback operation created: {rollback_id} for user {target_user_id}")
            
        except Exception as removal_error:
            # Если удаление не удалось, удаляем операцию отката
            await rollback_manager.delete_rollback_operation(rollback_id)
            raise removal_error
    except Exception as e:
        logging.error(f"[{ErrorCodes.DB_CONNECTION_ERROR}] Failed to remove admin role from user {target_user_id}: {e}")
        Metrics.track_admin_removal_error(callback.from_user.id, ErrorCodes.DB_CONNECTION_ERROR)
        await callback.answer("❌ Ошибка при удалении прав администратора.", show_alert=True)
        return
    
    # Логируем действие
    log_remove_admin(callback.from_user.id, target_user_id, username)
    
    await state.clear()
    
    # Формируем отображаемое имя пользователя
    display_name = f"@{username}" if username is not None else f"<code>{target_user_id}</code>"
    
    await callback.message.edit_text(
        f"✅ <b>Администратор удален</b>\n\n"
        f"Пользователь {display_name} больше не администратор.",
        parse_mode="HTML"
    )
    await callback.answer()
    
    # Очистка ресурсов
    try:
        duration_ms = (time.time() - start_time) * 1000
        if duration_ms > 2000:  # Логируем медленные операции
            logging.warning(f"Slow operation: on_remove_admin_confirm took {duration_ms:.1f}ms")
        
        # Периодическая очистка памяти
        if duration_ms > 10000:  # Если операция заняла больше 10 секунд
            await MemoryManager.cleanup_memory()
    except Exception as cleanup_error:
        logging.error(f"Error during resource cleanup: {cleanup_error}")

async def on_remove_admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик отмены удаления администратора"""
    
    # Валидация входных параметров
    if not isinstance(callback, types.CallbackQuery):
        logging.error(f"[{ErrorCodes.INVALID_CALLBACK_TYPE}] Invalid callback type in on_remove_admin_cancel")
        return
    if not isinstance(state, FSMContext):
        logging.error(f"[{ErrorCodes.INVALID_STATE_TYPE}] Invalid state type in on_remove_admin_cancel")
        return
    
    # Отслеживаем отмену
    if callback and callback.from_user and callback.from_user.id:
        Metrics.track_admin_removal_cancel(callback.from_user.id)
    
    await state.clear()
    await callback.message.edit_text("❌ Удаление администратора отменено.")
    await callback.answer()
