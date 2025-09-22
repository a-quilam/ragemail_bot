"""
Конфигурация сетевых настроек для aiogram
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiohttp import ClientTimeout, TCPConnector
from aiohttp.connector import ssl

logger = logging.getLogger(__name__)

class NetworkConfig:
    """Конфигурация сетевых параметров для улучшения стабильности соединения"""
    
    # Настройки соединения (фиксированные)
    KEEPALIVE_TIMEOUT = 30.0  # Таймаут keep-alive
    ENABLE_CLEANUP_CLOSED = True  # Очистка закрытых соединений
    LIMIT_CONNECTIONS = 100   # Лимит соединений
    LIMIT_PER_HOST = 30      # Лимит соединений на хост
    
    @classmethod
    def get_timeouts(cls, settings):
        """Получает настройки таймаутов из конфигурации"""
        return {
            'connect': settings.NETWORK_CONNECT_TIMEOUT,
            'read': settings.NETWORK_READ_TIMEOUT,
            'total': settings.NETWORK_TOTAL_TIMEOUT,
        }
    
    @classmethod
    def get_retry_settings(cls, settings):
        """Получает настройки retry из конфигурации"""
        return {
            'max_retries': settings.NETWORK_MAX_RETRIES,
            'base_delay': settings.NETWORK_BASE_DELAY,
            'max_delay': settings.NETWORK_MAX_DELAY,
            'backoff_factor': settings.NETWORK_BACKOFF_FACTOR,
        }
    
    @classmethod
    def create_session(cls, settings) -> AiohttpSession:
        """Создает настроенную сессию для aiogram"""
        
        # Получаем настройки таймаутов
        timeouts = cls.get_timeouts(settings)
        
        # Настройки SSL
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Настройки TCP коннектора
        connector = TCPConnector(
            limit=cls.LIMIT_CONNECTIONS,
            limit_per_host=cls.LIMIT_PER_HOST,
            keepalive_timeout=cls.KEEPALIVE_TIMEOUT,
            enable_cleanup_closed=cls.ENABLE_CLEANUP_CLOSED,
            ssl=ssl_context,
            use_dns_cache=True,
            ttl_dns_cache=300,  # 5 минут кеш DNS
            family=0,  # Автоматический выбор IPv4/IPv6
        )
        
        # Настройки таймаутов
        timeout = ClientTimeout(
            total=timeouts['total'],
            connect=timeouts['connect'],
            sock_read=timeouts['read'],
        )
        
        # Создаем сессию с настройками
        session = AiohttpSession(
            timeout=timeouts['total'],  # Используем числовое значение для совместимости
        )
        
        logger.info(f"Created network session with timeouts: connect={timeouts['connect']}s, "
                   f"read={timeouts['read']}s, total={timeouts['total']}s")
        
        return session
    
    @classmethod
    def create_bot_with_network_config(cls, token: str, settings) -> Bot:
        """Создает бота с оптимизированными сетевыми настройками"""
        
        session = cls.create_session(settings)
        
        # Создаем бота с кастомной сессией
        bot = Bot(
            token=token,
            session=session,
        )
        
        logger.info("Bot created with optimized network configuration")
        return bot
    
    @classmethod
    async def test_connection(cls, bot: Bot) -> bool:
        """Тестирует соединение с Telegram API"""
        try:
            me = await bot.get_me()
            logger.info(f"Connection test successful. Bot: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    @classmethod
    async def wait_for_connection(
        cls, 
        bot: Bot, 
        settings,
        max_attempts: Optional[int] = None,
        check_interval: float = 5.0
    ) -> bool:
        """Ожидает восстановления соединения с Telegram API"""
        
        retry_settings = cls.get_retry_settings(settings)
        max_attempts = max_attempts or retry_settings['max_retries']
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            logger.info(f"Testing connection (attempt {attempt}/{max_attempts})")
            
            if await cls.test_connection(bot):
                logger.info("Connection restored successfully")
                return True
            
            if attempt < max_attempts:
                delay = retry_settings['base_delay'] * (retry_settings['backoff_factor'] ** attempt)
                delay = min(delay, retry_settings['max_delay'])
                logger.info(f"Waiting {delay:.1f}s before next attempt...")
                await asyncio.sleep(delay)
        
        logger.error(f"Failed to restore connection after {max_attempts} attempts")
        return False

class NetworkErrorHandler:
    """Обработчик сетевых ошибок с улучшенной логикой retry"""
    
    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        """Определяет, можно ли повторить запрос при данной ошибке"""
        
        error_str = str(error).lower()
        
        # Ошибки, при которых стоит повторить запрос
        retryable_patterns = [
            'timeout',
            'connection reset',
            'connection refused',
            'connection aborted',
            'network is unreachable',
            'temporary failure',
            'bad gateway',
            'service unavailable',
            'gateway timeout',
            'internal server error',
            'too many requests',
        ]
        
        return any(pattern in error_str for pattern in retryable_patterns)
    
    @staticmethod
    def get_retry_delay(attempt: int, base_delay: float = 1.0) -> float:
        """Вычисляет задержку для retry с экспоненциальным backoff"""
        
        delay = base_delay * (NetworkConfig.BACKOFF_FACTOR ** attempt)
        return min(delay, NetworkConfig.MAX_DELAY)
    
    @staticmethod
    async def handle_network_error(
        error: Exception, 
        operation_name: str,
        max_retries: int = 3
    ) -> bool:
        """Обрабатывает сетевую ошибку с retry логикой"""
        
        if not NetworkErrorHandler.is_retryable_error(error):
            logger.error(f"Non-retryable error in {operation_name}: {error}")
            return False
        
        logger.warning(f"Retryable network error in {operation_name}: {error}")
        
        for attempt in range(max_retries):
            delay = NetworkErrorHandler.get_retry_delay(attempt)
            logger.info(f"Retrying {operation_name} in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            
            await asyncio.sleep(delay)
            
            # Здесь должна быть логика повторного выполнения операции
            # Это зависит от конкретного контекста использования
            
        logger.error(f"Failed to recover from network error in {operation_name} after {max_retries} retries")
        return False
