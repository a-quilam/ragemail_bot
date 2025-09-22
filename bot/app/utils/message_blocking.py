"""
Утилиты для блокировки сообщений по содержимому
"""
import logging
from typing import List, Optional
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo

logger = logging.getLogger(__name__)

async def check_message_for_blocked_words(message_text: str, blocks_repo: AliasBlocksRepo, mailbox_id: Optional[int] = None) -> Optional[str]:
    """
    Проверить сообщение на наличие заблокированных слов (с нормализацией через pymorphy2)
    
    Args:
        message_text: Текст сообщения для проверки
        blocks_repo: Репозиторий блокировок
        mailbox_id: ID ящика для локальных блокировок
        
    Returns:
        Заблокированное слово или None если блокировок нет
    """
    if not message_text or not blocks_repo:
        return None
    
    from app.utils.morphology import extract_words_from_text, normalize_word
    
    # Извлекаем и нормализуем все слова из сообщения
    normalized_words = extract_words_from_text(message_text)
    
    # Получаем все заблокированные слова для данного ящика
    blocked_words = await blocks_repo.get_blocked_words(mailbox_id)
    
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
        # Возвращаем первое найденное заблокированное слово
        blocked_normalized_word = next(iter(intersection))
        logger.info(f"Message blocked: normalized word '{blocked_normalized_word}' is blocked for mailbox {mailbox_id}")
        return blocked_normalized_word
    
    return None

def get_blocked_message_response(blocked_word: str, message_text: str, mailbox_id: Optional[int] = None) -> str:
    """
    Получить сообщение для пользователя о блокировке
    
    Args:
        blocked_word: Заблокированное слово
        message_text: Исходный текст сообщения
        mailbox_id: ID ящика
        
    Returns:
        Текст сообщения для пользователя
    """
    return (
        f"🚫 <b>Сообщение заблокировано</b>\n\n"
        f"❌ <b>Причина:</b> Слово \"{blocked_word}\" заблокировано\n"
        f"📝 <b>Ваше сообщение:</b> {message_text[:100]}{'...' if len(message_text) > 100 else ''}\n\n"
        f"💡 Обратитесь к администратору для разблокировки.\n"
        f"⚠️ <b>Внимание:</b> Попытка обхода блока может караться кулдауном."
    )
