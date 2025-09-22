from aiogram import types
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.stats_repo import StatsRepo
from app.utils.mailbox_permissions import can_manage_mailbox
import logging
# Safe imports with fallback support
try:
    from app.utils.rate_limiter import get_stats_limiter, check_rate_limit
except ImportError:
    from app.utils import get_stats_limiter, check_rate_limit

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

# Коды ошибок для лучшей диагностики
class ErrorCodes:
    INVALID_MESSAGE_TYPE = "CS001"
    INVALID_STATE_TYPE = "CS002"
    INVALID_DB_TYPE = "CS003"
    INVALID_USER_TYPE = "CS004"
    INVALID_USER_ID = "CS005"
    INVALID_MAILBOX_ID = "CS006"
    MAILBOX_NOT_FOUND = "CS007"
    INVALID_MAILBOX_DATA = "CS008"
    INSUFFICIENT_PERMISSIONS = "CS009"
    DB_CONNECTION_ERROR = "CS010"
    STATS_RETRIEVAL_ERROR = "CS011"
    CRITICAL_ERROR = "CS012"

# Метрики для мониторинга
class Metrics:
    @staticmethod
    def track_stats_request_start(user_id: int, mailbox_id: int):
        """Отслеживает начало запроса статистики"""
        logging.info(f"METRIC: stats_request_start user_id={user_id} mailbox_id={mailbox_id}")
    
    @staticmethod
    def track_stats_request_success(user_id: int, mailbox_id: int, stats_count: int):
        """Отслеживает успешный запрос статистики"""
        logging.info(f"METRIC: stats_request_success user_id={user_id} mailbox_id={mailbox_id} stats_count={stats_count}")
    
    @staticmethod
    def track_stats_request_error(user_id: int, mailbox_id: int, error_code: str):
        """Отслеживает ошибки при запросе статистики"""
        logging.info(f"METRIC: stats_request_error user_id={user_id} mailbox_id={mailbox_id} error_code={error_code}")
    
    @staticmethod
    def track_db_operation_duration(operation: str, duration_ms: float):
        """Отслеживает длительность операций базы данных"""
        logging.info(f"METRIC: db_operation_duration operation={operation} duration_ms={duration_ms}")
    
    @staticmethod
    def track_permission_check(user_id: int, mailbox_id: int, granted: bool):
        """Отслеживает проверки прав доступа"""
        status = "granted" if granted else "denied"
        logging.info(f"METRIC: permission_check user_id={user_id} mailbox_id={mailbox_id} status={status}")
    
    @staticmethod
    def track_mailbox_access(user_id: int, mailbox_id: int, access_type: str):
        """Отслеживает доступ к почтовым ящикам"""
        logging.info(f"METRIC: mailbox_access user_id={user_id} mailbox_id={mailbox_id} access_type={access_type}")
try:
    from app.core.constants import DAYS_OF_WEEK, STAT_TYPE_LABELS
except ImportError:
    # Fallback константы
    DAYS_OF_WEEK = ["", "понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]
    STAT_TYPE_LABELS = {
        "relay_msg": "💬 <b>Сообщений в реле:</b>",
        "posts": "📝 <b>Опубликованных постов:</b>",
        "users": "👥 <b>Активных пользователей:</b>",
        "extend_1h": "⏰ <b>Продлений +1ч:</b>",
        "extend_12h": "⏰ <b>Продлений +12ч:</b>"
    }

async def cmd_stats(m: types.Message, db, active_mailbox_id: int = None):
    """Показать статистику почтового ящика"""
    import time
    
    start_time = time.time()
    resource_manager = get_resource_manager()
    
    try:
        # Проверяем rate limit
        if m and m.from_user and m.from_user.id:
            stats_limiter = get_stats_limiter()
            is_allowed, reason = await check_rate_limit(stats_limiter, str(m.from_user.id), "cmd_stats")
            if not is_allowed:
                await m.answer(f"⚠️ Слишком много запросов статистики. {reason}")
                Metrics.track_stats_request_error(m.from_user.id, ErrorCodes.INSUFFICIENT_PERMISSIONS)
                return
        
        # Отслеживаем начало запроса
        if m and m.from_user and m.from_user.id:
            Metrics.track_stats_request_start(m.from_user.id, active_mailbox_id)
        # Валидация входных параметров
        if not isinstance(m, types.Message):
            logging.error(f"[{ErrorCodes.INVALID_MESSAGE_TYPE}] Invalid message type in cmd_stats")
            return
        if db is None:
            logging.error(f"[{ErrorCodes.INVALID_DB_TYPE}] Database connection is None in cmd_stats")
            return
        # Санитизация и валидация mailbox_id
        sanitized_mailbox_id = InputSanitizer.sanitize_mailbox_id(active_mailbox_id)
        if not sanitized_mailbox_id:
            logging.error(f"[{ErrorCodes.INVALID_MAILBOX_ID}] Invalid active_mailbox_id in cmd_stats: {active_mailbox_id}")
            return
        active_mailbox_id = sanitized_mailbox_id
    except Exception as e:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Error in cmd_stats validation: {e}")
        # Отслеживаем ошибку
        if m and m.from_user and m.from_user.id:
            Metrics.track_stats_request_error(m.from_user.id, active_mailbox_id, ErrorCodes.CRITICAL_ERROR)
        # Мониторинг критических ошибок
        try:
            # Здесь можно добавить отправку алертов в систему мониторинга
            logging.critical(f"[{ErrorCodes.CRITICAL_ERROR}] CRITICAL ERROR in cmd_stats: {e}")
        except Exception as alert_error:
            logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Failed to send alert: {alert_error}")
        return
    
    # Валидация сообщения
    if not m.text:
        logging.error("Empty message text in cmd_stats")
        return
    
    if m.text != "📊 Статистика":
        return
    
    # Валидация и санитизация пользовательского ввода
    if not m.from_user or not m.from_user.id:
        logging.error(f"[{ErrorCodes.INVALID_USER_TYPE}] Invalid user in cmd_stats")
        return
    
    # Санитизация user ID
    sanitized_user_id = InputSanitizer.sanitize_user_id(m.from_user.id)
    if not sanitized_user_id:
        logging.error(f"[{ErrorCodes.INVALID_USER_ID}] Invalid user ID in cmd_stats: {m.from_user.id}")
        return
    
    # Проверка безопасности - предотвращение доступа к чужим ящикам
    if active_mailbox_id and active_mailbox_id != m.from_user.id:
        # Дополнительная проверка прав доступа
        pass
    
    if not active_mailbox_id:
        await m.answer("❌ Активный ящик не выбран. Сначала выберите ящик в настройках.")
        return
    
    # Валидация почтового ящика
    if active_mailbox_id <= 0:
        logging.warning(f"[{ErrorCodes.INVALID_MAILBOX_ID}] Invalid mailbox ID: {active_mailbox_id}")
        await m.answer("❌ Неверный ID почтового ящика.")
        return
    
    # Проверяем права доступа к ящику
    try:
        permission_granted = await can_manage_mailbox(db, m.from_user.id, active_mailbox_id)
        Metrics.track_permission_check(m.from_user.id, active_mailbox_id, permission_granted)
        
        if not permission_granted:
            Metrics.track_mailbox_access(m.from_user.id, active_mailbox_id, "denied")
            await m.answer(
                "❌ <b>Доступ запрещен</b>\n\n"
                "У вас нет прав для просмотра статистики этого ящика.\n"
                "Права управления имеют только создатель ящика и суперадмин.",
                parse_mode="HTML"
            )
            return
        else:
            Metrics.track_mailbox_access(m.from_user.id, active_mailbox_id, "granted")
    except Exception as e:
        logging.error(f"[{ErrorCodes.INSUFFICIENT_PERMISSIONS}] Error checking mailbox permissions: {e}")
        Metrics.track_stats_request_error(m.from_user.id, active_mailbox_id, ErrorCodes.INSUFFICIENT_PERMISSIONS)
        await m.answer("❌ Ошибка при проверке прав доступа к ящику.")
        return
    
    # Получаем информацию о ящике
    try:
        db_start_time = time.time()
        box = await MailboxesRepo(db).get(active_mailbox_id)
        db_duration = (time.time() - db_start_time) * 1000  # в миллисекундах
        Metrics.track_db_operation_duration("get_mailbox", db_duration)
        logging.info(f"Retrieved mailbox info for user {m.from_user.id}, mailbox_id: {active_mailbox_id}")
    except Exception as e:
        logging.error(f"[{ErrorCodes.DB_CONNECTION_ERROR}] Error retrieving mailbox {active_mailbox_id} for user {m.from_user.id}: {e}")
        Metrics.track_stats_request_error(m.from_user.id, active_mailbox_id, ErrorCodes.DB_CONNECTION_ERROR)
        await m.answer("❌ Ошибка при получении информации о ящике")
        return
    
    if not box:
        logging.warning(f"[{ErrorCodes.MAILBOX_NOT_FOUND}] Mailbox {active_mailbox_id} not found for user {m.from_user.id}")
        await m.answer("❌ Ящик не найден")
        return
    
    # Безопасная распаковка кортежа
    if not box or len(box) < 6:
        logging.error(f"[{ErrorCodes.INVALID_MAILBOX_DATA}] Invalid mailbox data: {box}")
        await m.answer("❌ Ошибка: неполные данные ящика")
        return
    
    try:
        mailbox_id, title, channel_id, stat_day, stat_time, creator_id = box
    except (ValueError, TypeError) as e:
        logging.error(f"[{ErrorCodes.INVALID_MAILBOX_DATA}] Failed to unpack mailbox data: {e}")
        await m.answer("❌ Ошибка: некорректные данные ящика")
        return
    
    # Получаем статистику с graceful degradation и оптимизацией
    try:
        stats_repo = StatsRepo(db)
        # Оптимизация: используем более эффективный запрос
        stats_start_time = time.time()
        stats = await stats_repo.get_stats_for_mailbox(mailbox_id)
        stats_duration = (time.time() - stats_start_time) * 1000  # в миллисекундах
        Metrics.track_db_operation_duration("get_stats_for_mailbox", stats_duration)
        logging.info(f"Retrieved stats for mailbox {mailbox_id}: {len(stats) if stats else 0} entries")
    except Exception as e:
        logging.error(f"[{ErrorCodes.STATS_RETRIEVAL_ERROR}] Error retrieving stats for mailbox {mailbox_id}: {e}")
        Metrics.track_stats_request_error(m.from_user.id, mailbox_id, ErrorCodes.STATS_RETRIEVAL_ERROR)
        # Graceful degradation - показываем базовую информацию без статистики
        await m.answer(
            f"📊 <b>Статистика ящика «{safe_title}»</b>\n\n"
            f"🆔 <b>ID:</b> {mailbox_id}\n"
            f"📺 <b>Канал:</b> {safe_channel_id}\n\n"
            f"⚠️ <i>Статистика временно недоступна</i>",
            parse_mode="HTML"
        )
        return
    
    # Валидация и форматирование данных
    safe_title = str(title) if title is not None else "Без названия"
    safe_channel_id = str(channel_id) if channel_id is not None else "Не указан"
    
    # Проверки на None для критических данных
    if mailbox_id is None:
        logging.error("mailbox_id is None in cmd_stats")
        await m.answer("❌ Ошибка: некорректные данные ящика")
        return
    
    # Безопасное форматирование строк
    try:
        text = f"📊 <b>Статистика ящика «{safe_title}»</b>\n\n"
        text += f"🆔 <b>ID:</b> {mailbox_id}\n"
        text += f"📺 <b>Канал:</b> {safe_channel_id}\n"
    except Exception as e:
        logging.error(f"Error formatting stats text: {e}")
        await m.answer("❌ Ошибка при форматировании статистики")
        return
    
    # Проверяем, настроена ли статистика
    if stat_day is not None and stat_time is not None:
        day_name = DAYS_OF_WEEK[stat_day] if isinstance(stat_day, int) and 1 <= stat_day <= 7 else "неизвестный день"
        text += f"📅 <b>Статистика:</b> по {day_name} в {stat_time}\n\n"
    else:
        text += f"📅 <b>Статистика:</b> <i>не настроена</i>\n"
        text += f"💡 <i>Для настройки используйте команды:</i>\n"
        text += f"<code>/statday 1-7</code> - установить день недели\n"
        text += f"<code>/stathour HH:MM</code> - установить время\n\n"
    
    # Обработка статистики с оптимизацией
    if not stats or not isinstance(stats, dict):
        text += "📊 <b>Статистика пока пуста</b>\n\n"
        text += "💡 <i>Активность появится после первых постов</i>"
        
        # Валидация выходного текста
        text_validation = OutputValidator.validate_message_text(text)
        if not text_validation.is_valid:
            logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Invalid stats text: {text_validation.errors}")
            await m.answer("❌ Ошибка при формировании статистики.")
            return
        
        if text_validation.warnings:
            logging.warning(f"Stats text warnings: {text_validation.warnings}")
        
        await m.answer(text_validation.sanitized_data, parse_mode="HTML")
        return
    
    text += f"📈 <b>Активность:</b>\n"
    for stat_type, count in stats.items():
        # Валидация типа и значения
        if not isinstance(stat_type, str) or count is None or not isinstance(count, (int, float)):
            continue
            
        safe_count = int(count)
        
        # Используем словарь меток для оптимизации
        if hasattr(STAT_TYPE_LABELS, '__getitem__') and stat_type in STAT_TYPE_LABELS:
            text += f"{STAT_TYPE_LABELS[stat_type]} {safe_count}\n"
    
    text += f"\n💡 <i>Данные обновляются в реальном времени</i>"
    
    # Отслеживаем успешное завершение
    stats_count = len(stats) if stats else 0
    Metrics.track_stats_request_success(m.from_user.id, mailbox_id, stats_count)
    
    # Валидация финального выходного текста
    final_text_validation = OutputValidator.validate_message_text(text)
    if not final_text_validation.is_valid:
        logging.error(f"[{ErrorCodes.CRITICAL_ERROR}] Invalid final stats text: {final_text_validation.errors}")
        await m.answer("❌ Ошибка при формировании финальной статистики.")
        return
    
    if final_text_validation.warnings:
        logging.warning(f"Final stats text warnings: {final_text_validation.warnings}")
    
    await m.answer(final_text_validation.sanitized_data, parse_mode="HTML")
    
    # Очистка ресурсов
    try:
        duration_ms = (time.time() - start_time) * 1000
        if duration_ms > 3000:  # Логируем медленные операции
            logging.warning(f"Slow operation: cmd_stats took {duration_ms:.1f}ms")
        
        # Периодическая очистка памяти для длительных операций
        if duration_ms > 15000:  # Если операция заняла больше 15 секунд
            await MemoryManager.cleanup_memory()
    except Exception as cleanup_error:
        logging.error(f"Error during resource cleanup: {cleanup_error}")
