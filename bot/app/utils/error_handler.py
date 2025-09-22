"""
Централизованная обработка ошибок
"""
import logging
import asyncio
from typing import Optional, Callable, Any
from aiogram import types
from aiogram.exceptions import TelegramAPIError, TelegramConflictError, TelegramNetworkError

logger = logging.getLogger(__name__)

class BotError(Exception):
    """Базовый класс для ошибок бота"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        self.message = message
        self.user_message = user_message or "Произошла ошибка. Попробуйте позже."
        super().__init__(self.message)

class ValidationError(BotError):
    """Ошибка валидации данных"""
    pass

class PermissionError(BotError):
    """Ошибка прав доступа"""
    def __init__(self, message: str = "У вас нет прав для выполнения этого действия"):
        super().__init__(message, message)

class DatabaseError(BotError):
    """Ошибка базы данных"""
    def __init__(self, message: str):
        super().__init__(message, "Ошибка базы данных. Попробуйте позже.")

class NetworkError(BotError):
    """Ошибка сетевого соединения"""
    
    def __init__(self, message: str):
        super().__init__(message, "Проблемы с сетевым соединением. Попробуйте позже.")

async def handle_error(
    error: Exception, 
    message: Optional[types.Message] = None,
    callback: Optional[types.CallbackQuery] = None,
    context: Optional[str] = None
) -> None:
    """
    Централизованная обработка ошибок
    
    Args:
        error: Исключение
        message: Сообщение пользователя (если есть)
        callback: Callback query (если есть)
        context: Контекст ошибки
    """
    # Логируем ошибку
    error_context = f"Context: {context}" if context else ""
    logger.error(f"Error occurred: {error}", exc_info=True, extra={"context": error_context})
    
    # Определяем сообщение для пользователя
    if isinstance(error, BotError):
        user_message = error.user_message
    elif isinstance(error, TelegramConflictError):
        user_message = "Конфликт с другим экземпляром бота. Попробуйте позже."
        logger.warning("TelegramConflictError detected - possible multiple bot instances")
    elif isinstance(error, TelegramNetworkError):
        user_message = "Проблемы с сетевым соединением. Попробуйте позже."
        logger.warning(f"TelegramNetworkError detected: {error}")
    elif isinstance(error, TelegramAPIError):
        user_message = "Ошибка Telegram API. Попробуйте позже."
    elif isinstance(error, Exception):
        user_message = "Произошла неожиданная ошибка. Попробуйте позже."
    else:
        user_message = "Неизвестная ошибка."
    
    # Отправляем сообщение пользователю
    try:
        if message:
            await message.answer(
                f"❌ <b>Ошибка</b>\n\n{user_message}",
                parse_mode="HTML"
            )
        elif callback:
            await callback.answer(user_message, show_alert=True)
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

async def handle_network_error_with_retry(
    error: Exception,
    operation_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> bool:
    """
    Обрабатывает сетевую ошибку с retry логикой
    
    Args:
        error: Исключение
        operation_name: Название операции для логирования
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка между попытками
    
    Returns:
        True если ошибка обработана успешно, False иначе
    """
    if not isinstance(error, TelegramNetworkError):
        return False
    
    error_str = str(error).lower()
    retryable_patterns = [
        'timeout', 'connection reset', 'connection refused',
        'connection aborted', 'network is unreachable',
        'temporary failure', 'bad gateway', 'service unavailable',
        'gateway timeout', 'internal server error'
    ]
    
    if not any(pattern in error_str for pattern in retryable_patterns):
        logger.error(f"Non-retryable network error in {operation_name}: {error}")
        return False
    
    logger.warning(f"Retryable network error in {operation_name}: {error}")
    
    for attempt in range(max_retries):
        delay = base_delay * (2 ** attempt)  # Экспоненциальный backoff
        logger.info(f"Retrying {operation_name} in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
        
        await asyncio.sleep(delay)
        
        # Здесь должна быть логика повторного выполнения операции
        # Это зависит от конкретного контекста использования
    
    logger.error(f"Failed to recover from network error in {operation_name} after {max_retries} retries")
    return False

def safe_async(func: Callable) -> Callable:
    """
    Декоратор для безопасного выполнения асинхронных функций
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Пытаемся найти message или callback в аргументах
            message = None
            callback = None
            
            for arg in args:
                if isinstance(arg, types.Message):
                    message = arg
                elif isinstance(arg, types.CallbackQuery):
                    callback = arg
            
            await handle_error(e, message, callback, func.__name__)
            return None
    
    return wrapper

def validate_user_input(text: str, max_length: int = 2000, min_length: int = 1) -> str:
    """
    Валидация пользовательского ввода
    
    Args:
        text: Текст для валидации
        max_length: Максимальная длина
        min_length: Минимальная длина
        
    Returns:
        Очищенный текст
        
    Raises:
        ValidationError: Если валидация не прошла
    """
    if not text:
        raise ValidationError("Пустой текст", "Пожалуйста, введите текст.")
    
    text = text.strip()
    
    if len(text) < min_length:
        raise ValidationError(
            f"Text too short: {len(text)} < {min_length}",
            f"Текст слишком короткий. Минимум {min_length} символов."
        )
    
    if len(text) > max_length:
        raise ValidationError(
            f"Text too long: {len(text)} > {max_length}",
            f"Текст слишком длинный. Максимум {max_length} символов."
        )
    
    return text

def validate_user_id(user_id: Any) -> int:
    """
    Валидация ID пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Валидный ID пользователя
        
    Raises:
        ValidationError: Если ID невалидный
    """
    try:
        user_id = int(user_id)
        if user_id <= 0:
            raise ValueError("User ID must be positive")
        return user_id
    except (ValueError, TypeError):
        raise ValidationError(
            f"Invalid user ID: {user_id}",
            "Неверный ID пользователя. Используйте числовой ID."
        )
