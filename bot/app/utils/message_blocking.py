"""
Утилиты для блокировки сообщений по содержимому
"""
import logging
from typing import List, Optional
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo

logger = logging.getLogger(__name__)

async def check_message_for_blocked_words(message_text: str, blocks_repo: AliasBlocksRepo, mailbox_id: Optional[int] = None) -> Optional[dict]:
    """
    Проверить сообщение на наличие заблокированных слов (оптимизированная версия)
    
    Args:
        message_text: Текст сообщения для проверки
        blocks_repo: Репозиторий блокировок
        mailbox_id: ID ящика для локальных блокировок
        
    Returns:
        Словарь с информацией о блокировке или None если блокировок нет
        Формат: {"word": "заблокированное_слово", "reason": "причина_блокировки"}
    """
    if not message_text or not blocks_repo:
        return None
    
    # ОПТИМИЗАЦИЯ 1: Проверяем, есть ли заблокированные слова в ящике
    blocked_words = await blocks_repo.get_blocked_words(mailbox_id)
    if not blocked_words:
        # Если нет заблокированных слов - не проверяем ничего
        return None
    
    from app.utils.word_normalization import extract_words_from_text, normalize_word
    
    # ОПТИМИЗАЦИЯ 2: Умная обработка текста в зависимости от длины
    if len(message_text) <= 200:
        # Короткие сообщения - проверяем полностью
        normalized_words = extract_words_from_text(message_text)
    else:
        # Длинные сообщения - проверяем каждое второе слово
        words = message_text.split()
        # Берем каждое второе слово для экономии ресурсов
        sampled_words = [words[i] for i in range(0, len(words), 2)]
        sampled_text = ' '.join(sampled_words)
        normalized_words = extract_words_from_text(sampled_text)
    
    # Нормализуем заблокированные слова
    blocked_normalized = set()
    for blocked_word_info in blocked_words:
        blocked_word = blocked_word_info['word']
        normalized_blocked = normalize_word(blocked_word)
        if normalized_blocked:
            blocked_normalized.add(normalized_blocked)
    
    # Проверяем пересечение нормализованных слов
    intersection = normalized_words.intersection(blocked_normalized)
    if intersection:
        # Возвращаем первое найденное заблокированное слово с причиной
        blocked_normalized_word = next(iter(intersection))
        
        # Находим причину блокировки для этого слова
        blocking_reason = ""
        for blocked_word_info in blocked_words:
            if normalize_word(blocked_word_info['word']) == blocked_normalized_word:
                blocking_reason = blocked_word_info.get('reason', '')
                break
        
        logger.info(f"Message blocked: normalized word '{blocked_normalized_word}' is blocked for mailbox {mailbox_id}")
        return {
            "word": blocked_normalized_word,
            "reason": blocking_reason
        }
    
    return None

def get_blocked_message_response(blocked_info: dict, message_text: str, mailbox_id: Optional[int] = None) -> str:
    """
    Получить сообщение для пользователя о блокировке
    
    Args:
        blocked_info: Словарь с информацией о блокировке {"word": "слово", "reason": "причина"}
        message_text: Исходный текст сообщения
        mailbox_id: ID ящика
        
    Returns:
        Текст сообщения для пользователя
    """
    blocked_word = blocked_info["word"]
    blocking_reason = blocked_info.get("reason", "")
    
    # Формируем сообщение с причиной блокировки
    reason_text = f"\n📋 <b>Причина блокировки:</b> {blocking_reason}" if blocking_reason else ""
    
    return (
        f"🚫 <b>Сообщение заблокировано</b>\n\n"
        f"❌ <b>Заблокированное слово:</b> \"{blocked_word}\"{reason_text}\n"
        f"📝 <b>Ваше сообщение:</b> {message_text[:100]}{'...' if len(message_text) > 100 else ''}\n\n"
        f"💡 Обратитесь к администратору для разблокировки.\n"
        f"⚠️ <b>Внимание:</b> Попытка обхода блока может караться кулдауном."
    )


def get_blocked_message_keyboard() -> 'ReplyKeyboardMarkup':
    """
    Получить клавиатуру для сообщения о блокировке
    
    Returns:
        ReplyKeyboardMarkup с кнопкой продолжения
    """
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="✅ Хорошо, не буду нарушать")
        ]],
        resize_keyboard=True,
        selective=True,
        one_time_keyboard=True
    )
