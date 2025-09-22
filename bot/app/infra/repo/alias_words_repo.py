import aiosqlite
from typing import Set, List, Optional

class AliasWordsRepo:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def add_used_words(self, alias: str) -> None:
        """Добавить слова из псевдонима в список использованных"""
        words = self._extract_words(alias)
        for word in words:
            await self.db.execute(
                "INSERT OR IGNORE INTO alias_words (word, word_type) VALUES (?, ?)",
                (word, self._get_word_type(word))
            )
        await self.db.commit()

    async def get_used_words(self, word_type: Optional[str] = None) -> Set[str]:
        """Получить все использованные слова определенного типа"""
        if word_type:
            async with self.db.execute(
                "SELECT word FROM alias_words WHERE word_type = ?",
                (word_type,)
            ) as cursor:
                return {row[0] async for row in cursor}
        else:
            async with self.db.execute("SELECT word FROM alias_words") as cursor:
                return {row[0] async for row in cursor}

    async def is_word_used(self, word: str) -> bool:
        """Проверить, использовалось ли слово"""
        row = await (await self.db.execute(
            "SELECT 1 FROM alias_words WHERE word = ?",
            (word,)
        )).fetchone()
        return row is not None

    def _extract_words(self, alias: str) -> List[str]:
        """Извлечь отдельные слова из псевдонима"""
        words = []
        
        import re
        
        # Извлекаем эмодзи
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF]'
        emojis = re.findall(emoji_pattern, alias)
        words.extend(emojis)
        
        # Убираем эмодзи и цифры, разбиваем по пробелам
        clean_alias = re.sub(r'[^\w\s]', ' ', alias)
        parts = clean_alias.split()
        
        for part in parts:
            if part.isdigit():
                words.append(part)  # Цифры
            else:
                words.append(part.lower())  # Слова
        
        return words

    def _get_word_type(self, word: str) -> str:
        """Определить тип слова"""
        import re
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF]'
        
        if re.match(emoji_pattern, word):
            return "emoji"
        elif word.isdigit():
            return "number"
        elif len(word) <= 3:
            return "short"
        else:
            return "long"

    async def get_available_words(self, word_type: str, all_words: List[str]) -> List[str]:
        """Получить доступные слова определенного типа"""
        used_words = await self.get_used_words(word_type)
        return [word for word in all_words if word not in used_words]
