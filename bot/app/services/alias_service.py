import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from app.infra.repo.aliases_repo import AliasesRepo
from app.infra.repo.alias_words_repo import AliasWordsRepo
from app.infra.repo.alias_blocks_repo import AliasBlocksRepo
from app.core.constants import (
    ADJECTIVES, NOUNS_2SYL, ANIMAL_EMOJIS, 
    MAX_ALIAS_ATTEMPTS, CACHE_EXPIRY_SECONDS
)
import logging

logger = logging.getLogger(__name__)

class AliasService:
    """
    Сервис для генерации и управления псевдонимами пользователей.
    
    Обеспечивает уникальность псевдонимов, кэширование доступных слов
    и проверку на заблокированные слова.
    """
    
    def __init__(self, repo: AliasesRepo, tz: ZoneInfo, words_repo: AliasWordsRepo = None, blocks_repo: AliasBlocksRepo = None):
        """
        Инициализация сервиса псевдонимов.
        
        Args:
            repo: Репозиторий для работы с псевдонимами
            tz: Часовой пояс для определения дня
            words_repo: Репозиторий для работы со словами (опционально)
            blocks_repo: Репозиторий для работы с блокировками (опционально)
        """
        self.repo = repo
        self.tz = tz
        self.words_repo = words_repo
        self.blocks_repo = blocks_repo
        # Оптимизированное кэширование
        self._available_words_cache = None
        self._cache_expires = 0
        self._alias_pool = []  # Основной пул псевдонимов
        self._backup_pool = []  # Резервный пул псевдонимов
        self._pool_size = 50  # Размер пула псевдонимов
        self._generating_backup = False  # Флаг генерации резервного пула

    def clear_cache(self):
        """Принудительно очистить все кэши для применения обновлений"""
        self._alias_pool = []
        self._backup_pool = []
        self._available_words_cache = None
        self._cache_expires = 0
        self._generating_backup = False
        logger.info("AliasService cache cleared - new aliases will be generated with updated morphology")

    def _today_key(self) -> str:
        """
        Получить ключ текущего дня в формате YYYY-MM-DD.
        
        Returns:
            Строка с датой в формате YYYY-MM-DD
        """
        return datetime.now(self.tz).strftime("%Y-%m-%d")

    async def _get_cached_available_words(self):
        """Оптимизированное получение кэшированных слов"""
        now = time.time()
        if self._available_words_cache is None or now > self._cache_expires:
            # Обновляем кэш раз в 5 минут
            try:
                if self.words_repo:
                    self._available_words_cache = {
                        'emojis': await self.words_repo.get_used_words("emoji"),
                        'adjectives': await self.words_repo.get_available_words("long", ADJECTIVES),
                        'nouns': await self.words_repo.get_available_words("short", NOUNS_2SYL)
                    }
                else:
                    self._available_words_cache = {
                        'emojis': set(),
                        'adjectives': ADJECTIVES,
                        'nouns': NOUNS_2SYL
                    }
                # Кэш на 5 минут вместо 1 часа
                self._cache_expires = now + 300
                logger.debug(f"Alias cache updated: {len(self._available_words_cache['adjectives'])} adjectives, {len(self._available_words_cache['nouns'])} nouns")
            except Exception as e:
                logger.error(f"Error updating alias cache: {e}")
                # Fallback к базовым данным
                self._available_words_cache = {
                    'emojis': set(),
                    'adjectives': ADJECTIVES,
                    'nouns': NOUNS_2SYL
                }
                self._cache_expires = now + 60  # Короткий кэш при ошибке
        return self._available_words_cache

    async def _generate_alias_pool(self):
        """Генерация пула псевдонимов только когда он пустой"""
        # Генерируем пул только если он пустой
        if self._alias_pool:
            return self._alias_pool
        
        logger.info("Generating new alias pool (pool is empty)...")
        start_time = time.time()
        
        # Получаем кэшированные данные
        cache = await self._get_cached_available_words()
        
        # Генерируем пул псевдонимов
        self._alias_pool = []
        used_aliases = set()
        
        for _ in range(self._pool_size):
            # Быстрая генерация без проверки уникальности в БД
            available_emojis = [e for e in ANIMAL_EMOJIS if e not in cache['emojis']]
            if not available_emojis:
                available_emojis = ANIMAL_EMOJIS
            
            emoji = random.choice(available_emojis)
            
            if random.random() < 0.5:
                # Формат: эмодзи + прилагательное + существительное
                adjective = random.choice(cache['adjectives'] or ADJECTIVES)
                noun = random.choice(cache['nouns'] or NOUNS_2SYL)
                alias = f"{emoji} {adjective} {noun}"
                
                # Применяем упрощенную морфологическую обработку
                original_alias = alias
                try:
                    from app.utils.alias_morphology import process_alias_morphology_simple
                    alias = process_alias_morphology_simple(alias)
                    if alias != original_alias:
                        logger.info(f"Morphology applied: '{original_alias}' -> '{alias}'")
                    else:
                        logger.debug(f"Morphology unchanged: '{alias}'")
                except Exception as e:
                    logger.warning(f"Failed to process alias morphology: {e}")
                    # Продолжаем с исходным псевдонимом
            else:
                # Формат: эмодзи + существительное + цифры
                noun = random.choice(cache['nouns'] or NOUNS_2SYL)
                number = random.randint(10, 99)
                alias = f"{emoji} {noun}-{number}"
            
            # Проверяем уникальность в пуле
            if alias not in used_aliases:
                self._alias_pool.append(alias)
                used_aliases.add(alias)
        
        generation_time = time.time() - start_time
        logger.info(f"Alias pool generated in {generation_time:.3f}s: {len(self._alias_pool)} aliases")

    async def _generate_backup_pool(self):
        """Генерация резервного пула в фоновом режиме"""
        if self._generating_backup or self._backup_pool:
            return  # Уже генерируется или уже есть резервный пул
        
        self._generating_backup = True
        logger.info("Generating backup alias pool in background...")
        start_time = time.time()
        
        try:
            # Получаем кэшированные данные
            cache = await self._get_cached_available_words()
            
            # Генерируем резервный пул псевдонимов
            self._backup_pool = []
            used_aliases = set()
            
            for _ in range(self._pool_size):
                # Быстрая генерация без проверки уникальности в БД
                available_emojis = [e for e in ANIMAL_EMOJIS if e not in cache['emojis']]
                if not available_emojis:
                    available_emojis = ANIMAL_EMOJIS
                
                emoji = random.choice(available_emojis)
                
                if random.random() < 0.5:
                    # Формат: эмодзи + прилагательное + существительное
                    adjective = random.choice(cache['adjectives'] or ADJECTIVES)
                    noun = random.choice(cache['nouns'] or NOUNS_2SYL)
                    alias = f"{emoji} {adjective} {noun}"
                    
                    # Применяем упрощенную морфологическую обработку
                    original_alias = alias
                    try:
                        from app.utils.alias_morphology import process_alias_morphology_simple
                        alias = process_alias_morphology_simple(alias)
                        if alias != original_alias:
                            logger.info(f"Backup morphology applied: '{original_alias}' -> '{alias}'")
                        else:
                            logger.debug(f"Backup morphology unchanged: '{alias}'")
                    except Exception as e:
                        logger.warning(f"Failed to process backup alias morphology: {e}")
                        # Продолжаем с исходным псевдонимом
                else:
                    # Формат: эмодзи + существительное + цифры
                    noun = random.choice(cache['nouns'] or NOUNS_2SYL)
                    number = random.randint(10, 99)
                    alias = f"{emoji} {noun}-{number}"
                
                # Проверяем уникальность в резервном пуле
                if alias not in used_aliases:
                    self._backup_pool.append(alias)
                    used_aliases.add(alias)
            
            generation_time = time.time() - start_time
            logger.info(f"Backup alias pool generated in {generation_time:.3f}s: {len(self._backup_pool)} aliases")
            
        except Exception as e:
            logger.error(f"Error generating backup pool: {e}")
        finally:
            self._generating_backup = False

    async def _rand_alias_fast(self) -> str:
        """Быстрая генерация псевдонима из пула"""
        # Получаем основной пул псевдонимов
        await self._generate_alias_pool()
        
        # Если основной пул пустой, используем резервный
        if not self._alias_pool and self._backup_pool:
            logger.info("Main pool empty, switching to backup pool")
            self._alias_pool = self._backup_pool
            self._backup_pool = []
            # После переключения на резервный пул, сразу генерируем новый резервный
            if not self._generating_backup:
                logger.info("Generating new backup pool after switching...")
                import asyncio
                asyncio.create_task(self._generate_backup_pool())
        
        if self._alias_pool:
            # Берем случайный псевдоним из пула
            alias = random.choice(self._alias_pool)
            self._alias_pool.remove(alias)  # Убираем из пула
            
            # ПРЕДВАРИТЕЛЬНО генерируем резервный пул когда основной почти заканчивается
            if len(self._alias_pool) <= 5 and not self._backup_pool and not self._generating_backup:
                logger.info(f"Main pool almost empty: {len(self._alias_pool)} aliases left, generating backup pool in background...")
                # Запускаем генерацию резервного пула в фоне (не ждем)
                import asyncio
                asyncio.create_task(self._generate_backup_pool())
            
            return alias
        
        # Fallback к простой генерации
        logger.warning("Both pools empty, using fallback generation")
        emoji = random.choice(ANIMAL_EMOJIS)
        noun = random.choice(NOUNS_2SYL)
        number = random.randint(10, 99)
        return f"{emoji} {noun}-{number}"

    async def _rand_alias(self) -> str:
        """Генерирует уникальный псевдоним с оптимизацией"""
        # Используем быструю генерацию из пула
        return await self._rand_alias_fast()

    async def get_or_issue(self, user_id: int, mailbox_id: Optional[int] = None) -> str:
        """Оптимизированное получение или создание псевдонима"""
        start_time = time.time()
        
        try:
            day = self._today_key()
            alias = await self.repo.get_for_today(user_id, day)
            
            if not alias:
                # Генерируем новый псевдоним
                alias = await self._rand_alias()
                
                # Сохраняем использованные слова (асинхронно, не блокируем)
                if self.words_repo:
                    try:
                        await self.words_repo.add_used_words(alias)
                    except Exception as e:
                        logger.warning(f"Failed to save used words: {e}")
                
                # Сохраняем псевдоним
                await self.repo.set_for_today(user_id, alias, day)
            
            processing_time = time.time() - start_time
            if processing_time > 0.1:  # Логируем медленные операции
                logger.warning(f"Slow alias generation: {processing_time:.3f}s for user {user_id}")
            
            return alias
            
        except Exception as e:
            logger.error(f"Error in get_or_issue: {e}")
            # Fallback к простому псевдониму
            emoji = random.choice(ANIMAL_EMOJIS)
            noun = random.choice(NOUNS_2SYL)
            number = random.randint(10, 99)
            return f"{emoji} {noun}-{number}"
    
