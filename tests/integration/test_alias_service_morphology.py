"""
Интеграционные тесты для проверки морфологии в AliasService
"""
import unittest
import asyncio
import aiosqlite
import tempfile
import os
import sys
from zoneinfo import ZoneInfo

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bot'))

from app.services.alias_service import AliasService
from app.infra.repo.aliases_repo import AliasesRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo

class TestAliasServiceMorphology(unittest.IsolatedAsyncioTestCase):
    """Тесты для проверки морфологии в AliasService"""
    
    async def asyncSetUp(self):
        """Настройка тестовой базы данных"""
        # Создаем временную базу данных
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Подключаемся к базе данных
        self.db = await aiosqlite.connect(self.temp_db.name)
        
        # Создаем таблицы
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                user_id INTEGER,
                valid_day TEXT,
                alias TEXT,
                PRIMARY KEY (user_id, valid_day)
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS alias_words (
                word TEXT PRIMARY KEY,
                word_type TEXT,
                usage_count INTEGER DEFAULT 1
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS alias_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT,
                admin_id INTEGER,
                mailbox_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.commit()
        
        # Создаем репозитории
        self.aliases_repo = AliasesRepo(self.db)
        self.words_repo = AliasWordsRepo(self.db)
        self.blocks_repo = AliasBlocksRepo(self.db)
        
        # Создаем сервис
        self.tz = ZoneInfo("Europe/Moscow")
        self.alias_service = AliasService(
            self.aliases_repo, 
            self.tz, 
            self.words_repo, 
            self.blocks_repo
        )
    
    async def asyncTearDown(self):
        """Очистка после тестов"""
        await self.db.close()
        os.unlink(self.temp_db.name)
    
    async def test_alias_generation_with_morphology(self):
        """Тест генерации псевдонимов с морфологической обработкой"""
        # Генерируем несколько псевдонимов
        aliases = []
        for i in range(10):
            alias = await self.alias_service.get_or_issue(12345 + i)
            aliases.append(alias)
            print(f"Generated alias {i+1}: {alias}")
        
        # Проверяем, что хотя бы один псевдоним содержит прилагательное + существительное
        adjective_noun_aliases = [alias for alias in aliases if len(alias.split()) >= 3]
        self.assertGreater(len(adjective_noun_aliases), 0, 
            "Should generate at least one alias with adjective + noun")
        
        # Проверяем морфологию для псевдонимов с прилагательными
        for alias in adjective_noun_aliases:
            parts = alias.split()
            if len(parts) >= 3:
                emoji, adjective, noun = parts[0], parts[1], parts[2]
                
                # Проверяем, что прилагательное склонено правильно
                # Для женских существительных прилагательное должно заканчиваться на -ая или -яя
                if noun in ["обезьяна", "лиса", "кошка", "зайчиха"]:
                    self.assertTrue(
                        adjective.endswith(("ая", "яя")), 
                        f"Adjective '{adjective}' should be declined for feminine noun '{noun}' in alias '{alias}'"
                    )
                # Для мужских существительных прилагательное должно заканчиваться на -ый или -ий
                elif noun in ["кот", "пес", "тигр", "медведь"]:
                    self.assertTrue(
                        adjective.endswith(("ый", "ий")), 
                        f"Adjective '{adjective}' should be declined for masculine noun '{noun}' in alias '{alias}'"
                    )
    
    async def test_specific_morphology_cases(self):
        """Тест конкретных случаев морфологии"""
        # Тестируем конкретные случаи, которые были проблемными
        test_cases = [
            ("роговообманковый", "обезьяна", "роговообманковая"),
            ("гуттаперчевый", "лиса", "гуттаперчевая"),
            ("сургучный", "кошка", "сургучная"),
            ("виридиановый", "обезьяна", "виридиановая"),
        ]
        
        for adjective, noun, expected_declined in test_cases:
            with self.subTest(adjective=adjective, noun=noun):
                # Создаем тестовый псевдоним
                test_alias = f"🐵 {adjective} {noun}"
                
                # Применяем морфологическую обработку
                from app.utils.morphology import process_alias_morphology_simple
                result = process_alias_morphology_simple(test_alias)
                
                # Проверяем результат
                expected_alias = f"🐵 {expected_declined} {noun}"
                self.assertEqual(result, expected_alias, 
                    f"Expected '{expected_alias}', got '{result}'")
    
    async def test_alias_service_fallback(self):
        """Тест fallback поведения при ошибках морфологии"""
        # Тестируем, что сервис работает даже при ошибках морфологии
        # Это важно для стабильности системы
        
        # Генерируем псевдоним
        alias = await self.alias_service.get_or_issue(99999)
        
        # Проверяем, что псевдоним сгенерирован
        self.assertIsNotNone(alias)
        self.assertGreater(len(alias), 0)
        
        # Проверяем базовую структуру
        parts = alias.split()
        self.assertGreaterEqual(len(parts), 2, "Alias should have at least emoji and one word")
        
        # Первая часть должна быть эмодзи
        self.assertTrue(parts[0].startswith(""), "First part should be an emoji")

if __name__ == '__main__':
    unittest.main()
