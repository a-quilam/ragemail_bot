import asyncio
import logging
import os
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from app.core.config import settings
from app.core.network_config import NetworkConfig
from app.services.network_monitor import NetworkMonitor, NetworkMiddleware
from app.infra.db import connect
# from app.infra.db_pool import initialize_db_pool, get_db_pool, close_db_pool
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.extensions_repo import ExtensionsRepo
from app.infra.repo.relays_repo import RelaysRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.stats_repo import StatsRepo
from app.middlewares.auth_roles import RolesMiddleware
from app.middlewares.mailbox_context import MailboxContextMiddleware
from app.middlewares.fsm_cleanup_middleware import FSMCleanupMiddleware
from app.core.scheduler import Scheduler
from app.core.singleton import acquire_singleton_lock

from app.features.start.router import router as start_router
from app.features.write.router import router as write_router
from app.features.channel.router import router as channel_router
from app.features.relay.router import router as relay_router
from app.features.admin.router import router as admin_router
from app.features.admin.auto_detect import router as auto_detect_router
from app.features.bind.router import router as bind_router
# УДАЛЕН: from app.features.user_direct_write import handle_user_message
# Больше не используется после удаления direct_write_router
from app.features.debug.router import router as debug_router
from app.fsm.admin_states import CreateBoxStates
from aiogram.filters import StateFilter

async def main() -> None:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
    tz = ZoneInfo(settings.TIMEZONE)
    
    # Включаем singleton для предотвращения множественных экземпляров
    lock_fd = acquire_singleton_lock("bot.lock")
    logging.info("Singleton lock acquired")
    
    # Создаем бота с оптимизированными сетевыми настройками
    bot = NetworkConfig.create_bot_with_network_config(settings.BOT_TOKEN, settings)
    bot.default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    
    # Создаем монитор сетевого соединения
    network_monitor = NetworkMonitor(bot, check_interval=settings.NETWORK_MONITOR_INTERVAL)
    
    # Добавляем callback для уведомлений о проблемах с сетью
    async def on_network_health_change(is_healthy: bool):
        if is_healthy:
            logging.info("🌐 Network connection restored")
        else:
            logging.warning("🌐 Network connection issues detected")
    
    network_monitor.add_health_callback(on_network_health_change)
    
    # Устанавливаем монитор для админских команд
    from app.features.admin.cmd_network_status import set_network_monitor
    set_network_monitor(network_monitor)
    # Создаем простое соединение с базой данных
    db = await connect(settings.DB_PATH)
    
    dp = Dispatcher()
    users_repo = UsersRepo(db)
    
    # Включаем middleware
    dp.message.middleware(RolesMiddleware(users_repo))
    dp.callback_query.middleware(RolesMiddleware(users_repo))
    dp.message.middleware(MailboxContextMiddleware(users_repo))
    dp.callback_query.middleware(MailboxContextMiddleware(users_repo))
    
    # Middleware для автоматической очистки FSM состояний при ошибках
    dp.message.middleware(FSMCleanupMiddleware())
    dp.callback_query.middleware(FSMCleanupMiddleware())
    
    # Middleware для мониторинга сетевых запросов
    network_middleware = NetworkMiddleware(network_monitor)
    dp.message.middleware(network_middleware)
    dp.callback_query.middleware(network_middleware)

    # ВАЖНО: Порядок роутеров имеет значение!
    # Админские функции должны быть ПЕРВЫМИ для обработки кнопок
    
    # Отладочный middleware удален - проблема решена
    
    dp.include_router(admin_router)   # Админские функции - ПЕРВЫЙ!
    dp.include_router(start_router)  # /start команда
    dp.include_router(bind_router)   # Обработка start payload
    dp.include_router(write_router)   # Написание писем - ДОЛЖЕН БЫТЬ ПЕРЕД relay_router!
    dp.include_router(relay_router)  # /end команда и релеи
    dp.include_router(channel_router) # Callback кнопки каналов
    dp.include_router(auto_detect_router)  # Автоматическое обнаружение каналов
    dp.include_router(debug_router)   # Отладочный роутер - последний
    
    # УДАЛЕН: direct_write_router - дублировал функциональность write_router
    # Проблема дублирования сообщений была вызвана конфликтом между:
    # 1. on_auto_text_input в write_router (строка 37 в router.py)
    # 2. handle_direct_write в direct_write_router (удален)
    # 
    # write_router уже содержит всю необходимую логику для обработки
    # сообщений от обычных пользователей через on_auto_text_input

    # background scheduler
    scheduler = Scheduler(bot, tz, PostsRepo(db), ExtensionsRepo(db), RelaysRepo(db), MailboxesRepo(db), StatsRepo(db), users_repo, db)
    scheduler.start()
    
    # Запускаем автоматическую очистку FSM состояний
    from app.utils.fsm_timeout import start_fsm_timeout_cleanup
    start_fsm_timeout_cleanup()
    
    # Запускаем мониторинг сетевого соединения
    await network_monitor.start_monitoring()

    # Удаляем вебхук и пропускаем старые апдейты
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Тестируем соединение перед запуском
    if not await NetworkConfig.test_connection(bot):
        logging.warning("Initial connection test failed, but continuing with startup")
    
    try:
        await dp.start_polling(bot, db=db, tz=tz)
    finally:
        # Останавливаем мониторинг сетевого соединения
        await network_monitor.stop_monitoring()
        
        # Останавливаем автоматическую очистку FSM состояний
        from app.utils.fsm_timeout import stop_fsm_timeout_cleanup
        stop_fsm_timeout_cleanup()
        
        # Закрываем HTTP-сессию бота
        await bot.session.close()
        
        # Закрываем соединение с базой данных
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
