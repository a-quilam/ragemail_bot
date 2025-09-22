"""
Сервис для асинхронной обработки тяжелых операций
"""
import asyncio
import logging
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Статусы задач"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    """Фоновая задача"""
    task_id: str
    name: str
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    created_at: float = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    message: str = ""

class BackgroundTaskService:
    """
    Сервис для управления фоновыми задачами.
    
    Позволяет выполнять тяжелые операции асинхронно без блокировки
    основного потока бота.
    """
    
    def __init__(self, max_concurrent_tasks: int = 3):
        """
        Инициализация сервиса фоновых задач.
        
        Args:
            max_concurrent_tasks: Максимальное количество одновременных задач
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._task_counter = 0
        self._lock = asyncio.Lock()
    
    async def submit_task(
        self, 
        name: str, 
        func: Callable, 
        *args, 
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        **kwargs
    ) -> str:
        """
        Отправить задачу на выполнение.
        
        Args:
            name: Название задачи
            func: Функция для выполнения
            *args: Аргументы функции
            progress_callback: Callback для отслеживания прогресса
            **kwargs: Именованные аргументы функции
            
        Returns:
            ID задачи
        """
        async with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time())}"
            
            task = BackgroundTask(
                task_id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs,
                created_at=time.time()
            )
            
            self.tasks[task_id] = task
            
            # Запускаем задачу если есть свободные слоты
            if len(self.running_tasks) < self.max_concurrent_tasks:
                await self._start_task(task_id, progress_callback)
            
            logger.info(f"Submitted background task: {name} (ID: {task_id})")
            return task_id
    
    async def _start_task(self, task_id: str, progress_callback: Optional[Callable] = None):
        """Запустить задачу"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        # Создаем asyncio задачу
        asyncio_task = asyncio.create_task(
            self._execute_task(task, progress_callback)
        )
        self.running_tasks[task_id] = asyncio_task
        
        logger.info(f"Started background task: {task.name} (ID: {task_id})")
    
    async def _execute_task(self, task: BackgroundTask, progress_callback: Optional[Callable] = None):
        """Выполнить задачу"""
        try:
            # Если функция поддерживает progress_callback, передаем его
            if progress_callback and 'progress_callback' in task.func.__code__.co_varnames:
                task.kwargs['progress_callback'] = progress_callback
            
            result = await task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.message = "Задача выполнена успешно"
            
            logger.info(f"Completed background task: {task.name} (ID: {task.task_id})")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.message = "Задача отменена"
            logger.info(f"Cancelled background task: {task.name} (ID: {task.task_id})")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.message = f"Ошибка: {str(e)}"
            logger.error(f"Failed background task: {task.name} (ID: {task.task_id}): {e}")
            
        finally:
            task.completed_at = time.time()
            
            # Удаляем из выполняющихся задач
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            # Запускаем следующую задачу из очереди
            await self._start_next_pending_task(progress_callback)
    
    async def _start_next_pending_task(self, progress_callback: Optional[Callable] = None):
        """Запустить следующую задачу из очереди"""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return
        
        # Ищем задачу в статусе PENDING
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                await self._start_task(task_id, progress_callback)
                break
    
    async def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Получить статус задачи"""
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Отменить задачу.
        
        Args:
            task_id: ID задачи
            
        Returns:
            True если задача была отменена, False если не найдена
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status == TaskStatus.RUNNING and task_id in self.running_tasks:
            # Отменяем выполняющуюся задачу
            asyncio_task = self.running_tasks[task_id]
            asyncio_task.cancel()
            
        elif task.status == TaskStatus.PENDING:
            # Помечаем ожидающую задачу как отмененную
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            task.message = "Задача отменена"
        
        logger.info(f"Cancelled background task: {task.name} (ID: {task_id})")
        return True
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Очистить завершенные задачи старше указанного возраста.
        
        Args:
            max_age_hours: Максимальный возраст задач в часах
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                and task.completed_at 
                and (current_time - task.completed_at) > max_age_seconds):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old background tasks")
    
    async def get_service_status(self) -> dict:
        """Получить статус сервиса"""
        pending_count = sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING)
        running_count = len(self.running_tasks)
        completed_count = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_count = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        
        return {
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "total_tasks": len(self.tasks),
            "pending_tasks": pending_count,
            "running_tasks": running_count,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "available_slots": self.max_concurrent_tasks - running_count
        }

# Глобальный экземпляр сервиса
_background_service: Optional[BackgroundTaskService] = None

def get_background_service() -> BackgroundTaskService:
    """Получить глобальный экземпляр сервиса фоновых задач"""
    global _background_service
    if _background_service is None:
        _background_service = BackgroundTaskService()
    return _background_service

async def cleanup_background_tasks():
    """Очистить старые фоновые задачи"""
    service = get_background_service()
    await service.cleanup_completed_tasks()
