"""
Утилиты для автоматической очистки FSM состояний по таймауту
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class FSMTimeoutManager:
    """Менеджер для отслеживания и очистки FSM состояний по таймауту"""
    
    def __init__(self, timeout_minutes: int = 10):
        self.timeout_minutes = timeout_minutes
        self.user_states: Dict[int, datetime] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def start_cleanup_task(self):
        """Запустить задачу очистки состояний"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("FSM timeout cleanup task started")
    
    def stop_cleanup_task(self):
        """Остановить задачу очистки состояний"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("FSM timeout cleanup task stopped")
    
    def track_user_state(self, user_id: int):
        """Отслеживать состояние пользователя"""
        self.user_states[user_id] = datetime.now()
        logger.debug(f"Tracking FSM state for user {user_id}")
    
    def untrack_user_state(self, user_id: int):
        """Прекратить отслеживание состояния пользователя"""
        if user_id in self.user_states:
            del self.user_states[user_id]
            logger.debug(f"Stopped tracking FSM state for user {user_id}")
    
    async def _cleanup_loop(self):
        """Основной цикл очистки состояний"""
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                await self._cleanup_expired_states()
            except asyncio.CancelledError:
                logger.info("FSM cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in FSM cleanup loop: {e}")
    
    async def _cleanup_expired_states(self):
        """Очистить истекшие состояния"""
        now = datetime.now()
        timeout_threshold = now - timedelta(minutes=self.timeout_minutes)
        
        expired_users = [
            user_id for user_id, timestamp in self.user_states.items()
            if timestamp < timeout_threshold
        ]
        
        for user_id in expired_users:
            logger.warning(f"FSM state timeout for user {user_id}, clearing state")
            # Здесь можно добавить логику для принудительной очистки состояния
            # Но это требует доступа к FSMContext, что сложно реализовать глобально
            del self.user_states[user_id]
    
    def get_tracked_users_count(self) -> int:
        """Получить количество отслеживаемых пользователей"""
        return len(self.user_states)

# Глобальный экземпляр менеджера
fsm_timeout_manager = FSMTimeoutManager(timeout_minutes=10)

async def track_fsm_state(user_id: int, state: FSMContext):
    """Отслеживать FSM состояние пользователя"""
    fsm_timeout_manager.track_user_state(user_id)
    
    # Проверяем, есть ли уже состояние
    current_state = await state.get_state()
    if current_state:
        logger.info(f"User {user_id} entered FSM state: {current_state}")

async def untrack_fsm_state(user_id: int, state: FSMContext):
    """Прекратить отслеживание FSM состояния пользователя"""
    fsm_timeout_manager.untrack_user_state(user_id)
    
    # Очищаем состояние, но НЕ очищаем AntispamStates
    current_state = await state.get_state()
    if current_state and not str(current_state).startswith("AntispamStates"):
        await state.clear()
        logger.info(f"User {user_id} exited FSM state: {current_state}")
    elif current_state and str(current_state).startswith("AntispamStates"):
        logger.info(f"Preserving AntispamStates {current_state} for user {user_id}")

def start_fsm_timeout_cleanup():
    """Запустить автоматическую очистку FSM состояний"""
    fsm_timeout_manager.start_cleanup_task()

def stop_fsm_timeout_cleanup():
    """Остановить автоматическую очистку FSM состояний"""
    fsm_timeout_manager.stop_cleanup_task()
