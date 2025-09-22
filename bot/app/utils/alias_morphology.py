"""
Простая морфология для псевдонимов
Оптимизировано для простого Telegram-бота без внешних зависимостей
"""
import logging

logger = logging.getLogger(__name__)

# Простое правило склонения прилагательных для псевдонимов
ADJECTIVE_DECLENSION = {
    # Мужской род -> Женский род
    "ый": "ая",
    "ий": "яя", 
    "ой": "ая",
    "евый": "евая",  # для сложных прилагательных
    "овый": "овая",  # для сложных прилагательных
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
    masculine_nouns = [
        "медведь", "конь", "день", "пень", "олень", "лось", "конь",
        "тигр", "лев", "волк", "пес", "кот", "барс", "рысь", "ягуар",
        "леопард", "гепард", "пантера", "каракал", "сервал", "оцелот",
        "маргай", "кодкод", "снежный", "барс", "пума", "ягуар",
        "носорог", "бегемот", "верблюд", "слон", "жираф", "зебра",
        "антилопа", "газель", "импала", "гну", "лань", "косуля",
        "олень", "лось", "кабан", "бык", "баран", "козел", "теленок"
    ]
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
    
    result = " ".join(result_parts)
    
    # Логируем только если что-то изменилось
    if result != alias:
        logger.debug(f"Morphology: '{alias}' -> '{result}' (gender: {gender})")
    
    return result
