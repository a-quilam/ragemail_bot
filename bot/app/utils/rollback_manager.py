"""
Rollback management utilities for undoing changes
"""
import asyncio
import logging
import time
import json
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RollbackType(Enum):
    """Типы отката"""
    USER_ROLE_CHANGE = "user_role_change"
    USERNAME_UPDATE = "username_update"
    ADMIN_REMOVAL = "admin_removal"
    MAILBOX_UPDATE = "mailbox_update"
    CONFIG_CHANGE = "config_change"


@dataclass
class RollbackOperation:
    """Операция отката"""
    id: str
    rollback_type: RollbackType
    original_data: Dict[str, Any]
    target_data: Dict[str, Any]
    created_at: float
    expires_at: float
    executed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """Менеджер отката изменений"""
    
    def __init__(self, default_ttl: int = 3600):  # 1 час по умолчанию
        self._rollback_operations: Dict[str, RollbackOperation] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
        self._cleanup_interval = 300  # 5 минут
        self._last_cleanup = time.time()
    
    def _generate_rollback_id(self) -> str:
        """Генерация уникального ID для операции отката"""
        timestamp = int(time.time() * 1000)  # миллисекунды для уникальности
        return f"rollback_{timestamp}"
    
    async def _cleanup_expired_rollbacks(self):
        """Очистка истекших операций отката"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_rollbacks = []
        for rollback_id, operation in self._rollback_operations.items():
            if current_time > operation.expires_at:
                expired_rollbacks.append(rollback_id)
        
        for rollback_id in expired_rollbacks:
            del self._rollback_operations[rollback_id]
            logging.debug(f"Cleaned up expired rollback: {rollback_id}")
        
        self._last_cleanup = current_time
        
        if expired_rollbacks:
            logging.info(f"Cleaned up {len(expired_rollbacks)} expired rollback operations")
    
    async def create_rollback_operation(
        self,
        rollback_type: RollbackType,
        original_data: Dict[str, Any],
        target_data: Dict[str, Any],
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Создать операцию отката
        
        Args:
            rollback_type: Тип отката
            original_data: Исходные данные
            target_data: Целевые данные
            ttl: Время жизни в секундах
            metadata: Дополнительные метаданные
            
        Returns:
            ID операции отката
        """
        async with self._lock:
            await self._cleanup_expired_rollbacks()
            
            rollback_id = self._generate_rollback_id()
            current_time = time.time()
            
            operation = RollbackOperation(
                id=rollback_id,
                rollback_type=rollback_type,
                original_data=original_data,
                target_data=target_data,
                created_at=current_time,
                expires_at=current_time + (ttl or self._default_ttl),
                metadata=metadata or {}
            )
            
            self._rollback_operations[rollback_id] = operation
            logging.info(f"Created rollback operation: {rollback_id} ({rollback_type.value})")
            
            return rollback_id
    
    async def execute_rollback(
        self,
        rollback_id: str,
        rollback_func: Optional[Callable] = None
    ) -> bool:
        """
        Выполнить откат
        
        Args:
            rollback_id: ID операции отката
            rollback_func: Функция для выполнения отката
            
        Returns:
            True если откат выполнен успешно, False если ошибка
        """
        async with self._lock:
            if rollback_id not in self._rollback_operations:
                logging.error(f"Rollback operation not found: {rollback_id}")
                return False
            
            operation = self._rollback_operations[rollback_id]
            
            if operation.executed:
                logging.warning(f"Rollback operation already executed: {rollback_id}")
                return False
            
            if time.time() > operation.expires_at:
                logging.error(f"Rollback operation expired: {rollback_id}")
                return False
            
            try:
                if rollback_func:
                    # Выполняем пользовательскую функцию отката
                    if asyncio.iscoroutinefunction(rollback_func):
                        await rollback_func(operation.original_data, operation.target_data)
                    else:
                        rollback_func(operation.original_data, operation.target_data)
                else:
                    # Выполняем стандартный откат
                    await self._execute_standard_rollback(operation)
                
                operation.executed = True
                logging.info(f"Rollback executed successfully: {rollback_id}")
                return True
                
            except Exception as e:
                logging.error(f"Error executing rollback {rollback_id}: {e}")
                return False
    
    async def _execute_standard_rollback(self, operation: RollbackOperation):
        """Выполнить стандартный откат"""
        if operation.rollback_type == RollbackType.USER_ROLE_CHANGE:
            # Откат изменения роли пользователя
            user_id = operation.original_data.get('user_id')
            original_role = operation.original_data.get('role')
            
            if user_id and original_role:
                # Здесь должен быть вызов к UsersRepo для восстановления роли
                logging.info(f"Rolling back user {user_id} role to {original_role}")
                # TODO: Интеграция с UsersRepo
        
        elif operation.rollback_type == RollbackType.USERNAME_UPDATE:
            # Откат обновления username
            user_id = operation.original_data.get('user_id')
            original_username = operation.original_data.get('username')
            
            if user_id:
                logging.info(f"Rolling back user {user_id} username to {original_username}")
                # TODO: Интеграция с UsersRepo
        
        elif operation.rollback_type == RollbackType.ADMIN_REMOVAL:
            # Откат удаления администратора
            user_id = operation.original_data.get('user_id')
            original_role = operation.original_data.get('role')
            
            if user_id and original_role:
                logging.info(f"Rolling back admin removal for user {user_id}, restoring role {original_role}")
                # TODO: Интеграция с UsersRepo
    
    async def get_rollback_operation(self, rollback_id: str) -> Optional[RollbackOperation]:
        """Получить операцию отката"""
        return self._rollback_operations.get(rollback_id)
    
    async def list_rollback_operations(
        self, 
        rollback_type: Optional[RollbackType] = None,
        include_expired: bool = False
    ) -> List[RollbackOperation]:
        """Получить список операций отката"""
        current_time = time.time()
        operations = []
        
        for operation in self._rollback_operations.values():
            if rollback_type and operation.rollback_type != rollback_type:
                continue
            
            if not include_expired and current_time > operation.expires_at:
                continue
            
            operations.append(operation)
        
        return operations
    
    async def delete_rollback_operation(self, rollback_id: str) -> bool:
        """Удалить операцию отката"""
        async with self._lock:
            if rollback_id in self._rollback_operations:
                del self._rollback_operations[rollback_id]
                logging.info(f"Deleted rollback operation: {rollback_id}")
                return True
            return False
    
    async def get_rollback_stats(self) -> Dict[str, Any]:
        """Получить статистику операций отката"""
        current_time = time.time()
        total_operations = len(self._rollback_operations)
        executed_operations = sum(1 for op in self._rollback_operations.values() if op.executed)
        expired_operations = sum(1 for op in self._rollback_operations.values() if current_time > op.expires_at)
        
        # Статистика по типам
        type_stats = {}
        for operation in self._rollback_operations.values():
            rollback_type = operation.rollback_type.value
            if rollback_type not in type_stats:
                type_stats[rollback_type] = {"total": 0, "executed": 0, "expired": 0}
            
            type_stats[rollback_type]["total"] += 1
            if operation.executed:
                type_stats[rollback_type]["executed"] += 1
            if current_time > operation.expires_at:
                type_stats[rollback_type]["expired"] += 1
        
        return {
            "total_operations": total_operations,
            "executed_operations": executed_operations,
            "expired_operations": expired_operations,
            "active_operations": total_operations - executed_operations - expired_operations,
            "type_statistics": type_stats,
            "default_ttl": self._default_ttl,
            "cleanup_interval": self._cleanup_interval
        }


# Глобальный экземпляр менеджера отката
_rollback_manager = RollbackManager()


def get_rollback_manager() -> RollbackManager:
    """Получить глобальный экземпляр менеджера отката"""
    return _rollback_manager


# Утилиты для создания операций отката
async def create_user_role_rollback(
    user_id: int,
    original_role: str,
    new_role: str,
    ttl: Optional[int] = None
) -> str:
    """Создать операцию отката для изменения роли пользователя"""
    manager = get_rollback_manager()
    
    return await manager.create_rollback_operation(
        RollbackType.USER_ROLE_CHANGE,
        {"user_id": user_id, "role": original_role},
        {"user_id": user_id, "role": new_role},
        ttl,
        {"operation": "role_change", "timestamp": time.time()}
    )


async def create_username_rollback(
    user_id: int,
    original_username: Optional[str],
    new_username: Optional[str],
    ttl: Optional[int] = None
) -> str:
    """Создать операцию отката для обновления username"""
    manager = get_rollback_manager()
    
    return await manager.create_rollback_operation(
        RollbackType.USERNAME_UPDATE,
        {"user_id": user_id, "username": original_username},
        {"user_id": user_id, "username": new_username},
        ttl,
        {"operation": "username_update", "timestamp": time.time()}
    )


async def create_admin_removal_rollback(
    user_id: int,
    original_role: str,
    ttl: Optional[int] = None
) -> str:
    """Создать операцию отката для удаления администратора"""
    manager = get_rollback_manager()
    
    return await manager.create_rollback_operation(
        RollbackType.ADMIN_REMOVAL,
        {"user_id": user_id, "role": original_role},
        {"user_id": user_id, "role": "user"},
        ttl,
        {"operation": "admin_removal", "timestamp": time.time()}
    )


# Функции для выполнения отката
async def execute_user_role_rollback(rollback_id: str, users_repo) -> bool:
    """Выполнить откат изменения роли пользователя"""
    manager = get_rollback_manager()
    
    async def rollback_func(original_data, target_data):
        user_id = original_data.get('user_id')
        original_role = original_data.get('role')
        
        if user_id and original_role:
            await users_repo.set_role(user_id, original_role)
    
    return await manager.execute_rollback(rollback_id, rollback_func)


async def execute_username_rollback(rollback_id: str, users_repo) -> bool:
    """Выполнить откат обновления username"""
    manager = get_rollback_manager()
    
    async def rollback_func(original_data, target_data):
        user_id = original_data.get('user_id')
        original_username = original_data.get('username')
        
        if user_id:
            await users_repo.update_username(user_id, original_username)
    
    return await manager.execute_rollback(rollback_id, rollback_func)


async def execute_admin_removal_rollback(rollback_id: str, users_repo) -> bool:
    """Выполнить откат удаления администратора"""
    manager = get_rollback_manager()
    
    async def rollback_func(original_data, target_data):
        user_id = original_data.get('user_id')
        original_role = original_data.get('role')
        
        if user_id and original_role:
            await users_repo.set_role(user_id, original_role)
    
    return await manager.execute_rollback(rollback_id, rollback_func)
