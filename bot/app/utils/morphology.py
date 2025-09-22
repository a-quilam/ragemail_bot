"""
Морфологический анализ слов с использованием pymorphy3
Оптимизировано для простого Telegram-бота
"""
import logging
import re
from typing import Set, Optional
from pymorphy3 import MorphAnalyzer

logger = logging.getLogger(__name__)

# Инициализируем анализатор морфологии
try:
    morph = MorphAnalyzer()
    MORPH_AVAILABLE = True
except Exception as e:
    logger.error(f"Failed to initialize MorphAnalyzer: {e}")
    morph = None
    MORPH_AVAILABLE = False

def extract_words_from_text(text: str) -> Set[str]:
    """
    Извлечь и нормализовать все слова из текста (для системы блокировки)
    
    Args:
        text: Исходный текст
        
    Returns:
        Множество нормализованных слов
    """
    if not text or not MORPH_AVAILABLE:
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
    Нормализовать слово (привести к начальной форме) для системы блокировки
    
    Args:
        word: Исходное слово
        
    Returns:
        Нормализованное слово или None при ошибке
    """
    if not word or not MORPH_AVAILABLE:
        return word
    
    # Получаем морфологический анализ
    parsed = morph.parse(word)
    if parsed:
        # Берем первую (наиболее вероятную) интерпретацию
        normal_form = parsed[0].normal_form
        return normal_form.lower()
    return word.lower()

# Простое правило склонения прилагательных для псевдонимов
ADJECTIVE_DECLENSION = {
    # Мужской род -> Женский род
    "ый": "ая",
    "ий": "яя", 
    "ой": "ая",
}

def decline_adjective_simple(adjective: str, gender: str = "femn") -> str:
    """
    Простое склонение прилагательного по роду (для псевдонимов)
    
    Args:
        adjective: Прилагательное в мужском роде
        gender: Род ("masc", "femn")
        
    Returns:
        Склоненное прилагательное
    """
    if not adjective or gender == "masc":
        return adjective
    
    # Простое правило: заменяем окончание
    for masc_ending, femn_ending in ADJECTIVE_DECLENSION.items():
        if adjective.endswith(masc_ending):
            return adjective[:-len(masc_ending)] + femn_ending
    
    return adjective

def get_noun_gender_simple(noun: str) -> str:
    """
    Простое определение рода существительного (для псевдонимов)
    
    Args:
        noun: Существительное
        
    Returns:
        Род ("masc", "femn")
    """
    if not noun:
        return "femn"
    
    # Специальные случаи для мужских существительных (исключения)
    masculine_nouns = ["медведь", "конь", "день", "пень", "олень", "лось", "конь"]
    if noun in masculine_nouns:
        return "masc"
    
    # Простые правила для определения рода
    feminine_endings = ["а", "я"]
    
    # Проверяем женские окончания
    for ending in feminine_endings:
        if noun.endswith(ending):
            return "femn"
    
    # По умолчанию мужской род
    return "masc"

def process_alias_morphology_simple(alias: str) -> str:
    """
    Обработать морфологию псевдонима (склонить прилагательное по роду существительного)
    Оптимизированная версия без pymorphy3 для простоты
    
    Args:
        alias: Псевдоним в формате "эмодзи прилагательное существительное"
        
    Returns:
        Псевдоним с правильно склоненным прилагательным
    """
    if not alias:
        return alias
    
    # Разбираем псевдоним на части
    parts = alias.split()
    if len(parts) < 3:
        return alias
    
    emoji, adjective, noun = parts[0], parts[1], parts[2]
    
    # Определяем род существительного
    gender = get_noun_gender_simple(noun)
    
    # Склоняем прилагательное
    declined_adjective = decline_adjective_simple(adjective, gender)
    
    # Собираем результат
    result_parts = [emoji, declined_adjective, noun]
    if len(parts) > 3:
        result_parts.extend(parts[3:])
    
    return " ".join(result_parts)

# Функция для тестирования
def test_morphology():
    """Тестирование морфологических функций"""
    test_cases = [
        "🐵 роговообманковый обезьяна",
        "🐱 гуттаперчевый кот",
        "🐶 сургучный пес",
        "🦊 виридиановый лиса"
    ]
    
    print("Testing morphology processing:")
    for test_case in test_cases:
        result = process_alias_morphology_simple(test_case)
        print(f"  '{test_case}' -> '{result}'")

if __name__ == "__main__":
    test_morphology()
