"""
Простая нормализация слов для системы блокировки сообщений
Оптимизировано для простого Telegram-бота без внешних зависимостей
"""
import re
from typing import Set, Optional

def extract_words_from_text(text: str) -> Set[str]:
    """
    Извлечь и нормализовать все слова из текста (для системы блокировки)
    
    Args:
        text: Исходный текст
        
    Returns:
        Множество нормализованных слов
    """
    if not text:
        return set()
    
    # Убираем все кроме букв и пробелов
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = clean_text.split()
    
    normalized_words = set()
    for word in words:
        if len(word) > 2:  # Игнорируем короткие слова
            normalized = normalize_word(word)
            if normalized:
                normalized_words.add(normalized)
    
    return normalized_words

def normalize_word(word: str) -> Optional[str]:
    """
    Нормализовать слово до базовой формы (простая версия)
    
    Args:
        word: Слово для нормализации
        
    Returns:
        Нормализованное слово или None при ошибке
    """
    if not word:
        return None
    
    # Простая нормализация: убираем окончания и приводим к нижнему регистру
    word = word.lower().strip()
    
    # Убираем знаки препинания
    word = re.sub(r'[^\w]', '', word)
    
    # Простые правила для базовых форм (для основных случаев)
    if len(word) > 3:
        # Убираем типичные окончания
        if word.endswith(('ая', 'ое', 'ый', 'ий', 'ой')):
            word = word[:-2]  # Прилагательные
        elif word.endswith(('ам', 'ом', 'ем', 'ах', 'ях')):
            word = word[:-2]  # Падежные окончания
        elif word.endswith(('и', 'ы', 'е')):
            word = word[:-1]  # Множественное число
    
    return word if word else None
