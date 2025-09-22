"""
Тесты для проверки исправлений морфологии псевдонимов
"""
import unittest
import sys
import os

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot'))

from app.utils.morphology import (
    process_alias_morphology_simple,
    decline_adjective_simple,
    get_noun_gender_simple,
    normalize_word,
    extract_words_from_text
)

class TestMorphologyFixes(unittest.TestCase):
    """Тесты для морфологических исправлений"""
    
    def test_process_alias_morphology_simple_female_nouns(self):
        """Тест склонения прилагательных с женскими существительными"""
        test_cases = [
            ("🐵 роговообманковый обезьяна", "🐵 роговообманковая обезьяна"),
            ("🦊 виридиановый лиса", "🦊 виридиановая лиса"),
            ("🐱 гуттаперчевый кошка", "🐱 гуттаперчевая кошка"),
            ("🐰 сургучный зайчиха", "🐰 сургучная зайчиха"),
        ]
        
        for input_alias, expected in test_cases:
            with self.subTest(input_alias=input_alias):
                result = process_alias_morphology_simple(input_alias)
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_alias}'")
    
    def test_process_alias_morphology_simple_male_nouns(self):
        """Тест склонения прилагательных с мужскими существительными"""
        test_cases = [
            ("🐱 гуттаперчевый кот", "🐱 гуттаперчевый кот"),
            ("🐶 сургучный пес", "🐶 сургучный пес"),
            ("🐯 виридиановый тигр", "🐯 виридиановый тигр"),
            ("🐻 роговообманковый медведь", "🐻 роговообманковый медведь"),
        ]
        
        for input_alias, expected in test_cases:
            with self.subTest(input_alias=input_alias):
                result = process_alias_morphology_simple(input_alias)
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_alias}'")
    
    def test_process_alias_morphology_simple_neuter_nouns(self):
        """Тест склонения прилагательных со средними существительными (упрощенная версия не поддерживает)"""
        test_cases = [
            ("🐭 гуттаперчевый существо", "🐭 гуттаперчевый существо"),  # Не изменяется
            ("🐹 сургучный животное", "🐹 сургучный животное"),  # Не изменяется
        ]
        
        for input_alias, expected in test_cases:
            with self.subTest(input_alias=input_alias):
                result = process_alias_morphology_simple(input_alias)
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_alias}'")
    
    def test_decline_adjective_simple_female(self):
        """Тест склонения прилагательных в женский род"""
        test_cases = [
            ("роговообманковый", "роговообманковая"),
            ("гуттаперчевый", "гуттаперчевая"),
            ("сургучный", "сургучная"),
            ("виридиановый", "виридиановая"),
        ]
        
        for input_adj, expected in test_cases:
            with self.subTest(input_adj=input_adj):
                result = decline_adjective_simple(input_adj, "femn")
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_adj}'")
    
    def test_decline_adjective_simple_male(self):
        """Тест склонения прилагательных в мужской род"""
        test_cases = [
            ("роговообманковый", "роговообманковый"),
            ("гуттаперчевый", "гуттаперчевый"),
            ("сургучный", "сургучный"),
            ("виридиановый", "виридиановый"),
        ]
        
        for input_adj, expected in test_cases:
            with self.subTest(input_adj=input_adj):
                result = decline_adjective_simple(input_adj, "masc")
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_adj}'")
    
    def test_get_noun_gender_simple(self):
        """Тест определения рода существительных"""
        test_cases = [
            ("обезьяна", "femn"),
            ("кот", "masc"),
            ("пес", "masc"),
            ("лиса", "femn"),
            ("кошка", "femn"),
            ("тигр", "masc"),
            ("медведь", "masc"),
        ]
        
        for noun, expected_gender in test_cases:
            with self.subTest(noun=noun):
                result = get_noun_gender_simple(noun)
                self.assertEqual(result, expected_gender, 
                    f"Expected gender '{expected_gender}', got '{result}' for noun '{noun}'")
    
    def test_normalize_word(self):
        """Тест нормализации слов"""
        test_cases = [
            ("роговообманковый", "роговообманковый"),
            ("гуттаперчевый", "гуттаперчевый"),
            ("сургучный", "сургучный"),
            ("виридиановый", "виридиановый"),
        ]
        
        for input_word, expected in test_cases:
            with self.subTest(input_word=input_word):
                result = normalize_word(input_word)
                self.assertEqual(result, expected, 
                    f"Expected '{expected}', got '{result}' for input '{input_word}'")
    
    def test_extract_words_from_text(self):
        """Тест извлечения слов из текста"""
        text = "🐵 роговообманковый обезьяна и 🐱 гуттаперчевый кот"
        result = extract_words_from_text(text)
        
        # Проверяем, что извлечены основные слова
        expected_words = {"роговообманковый", "обезьяна", "гуттаперчевый", "кот"}
        self.assertTrue(expected_words.issubset(result), 
            f"Expected words {expected_words} not found in result {result}")
    
    def test_process_alias_morphology_simple_edge_cases(self):
        """Тест граничных случаев"""
        # Случай с недостаточным количеством частей
        result = process_alias_morphology_simple("🐵 роговообманковый")
        self.assertEqual(result, "🐵 роговообманковый")
        
        # Случай с пустой строкой
        result = process_alias_morphology_simple("")
        self.assertEqual(result, "")
        
        # Случай с None
        result = process_alias_morphology_simple(None)
        self.assertEqual(result, None)
    
    def test_process_alias_morphology_simple_with_extra_parts(self):
        """Тест обработки псевдонимов с дополнительными частями"""
        # Псевдоним с дополнительными частями
        result = process_alias_morphology_simple("🐵 роговообманковый обезьяна 123")
        self.assertEqual(result, "🐵 роговообманковая обезьяна 123")
        
        # Псевдоним с множественными частями (только первые 3 части обрабатываются)
        result = process_alias_morphology_simple("🐵 роговообманковый обезьяна-123")
        self.assertEqual(result, "🐵 роговообманковый обезьяна-123")  # Не изменяется, так как "обезьяна-123" не распознается как женский род

if __name__ == '__main__':
    unittest.main()
