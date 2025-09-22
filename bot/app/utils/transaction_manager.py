"""
Transaction management utilities for database operations
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
try:
    import aiosqlite
except ImportError:
    aiosqlite = None


class TransactionState(Enum):
    """Состояния транзакции"""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionInfo:
    """Информация о транзакции"""
    id: str
    state: TransactionState
    started_at: float
    operations: List[Dict[str, Any]] = field(default_factory=list)
    rollback_operations: List[Dict[str, Any]] = field(default_factory=list)
    timeout: float = 30.0
    isolation_level: str = "DEFERRED"


class TransactionManager:
    """Менеджер транзакций для управления операциями базы данных"""
    
    def __init__(self):
        self._active_transactions: Dict[str, TransactionInfo] = {}
        self._transaction_counter = 0
        self._lock = asyncio.Lock()
        self._cleanup_interval = 60.0  # 1 минута
        self._last_cleanup = time.time()
    
    def _generate_transaction_id(self) -> str:
        """Генерация уникального ID транзакции"""
        self._transaction_counter += 1
        return f"tx_{int(time.time())}_{self._transaction_counter}"
    
    async def _cleanup_stale_transactions(self):
        """Очистка устаревших транзакций"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        stale_transactions = []
        for tx_id, tx_info in self._active_transactions.items():
            if current_time - tx_info.started_at > tx_info.timeout:
                stale_transactions.append(tx_id)
        
        for tx_id in stale_transactions:
            logging.warning(f"Cleaning up stale transaction: {tx_id}")
            await self.rollback_transaction(tx_id)
        
        self._last_cleanup = current_time
    
    async def begin_transaction(
        self, 
        timeout: float = 30.0,
        isolation_level: str = "DEFERRED"
    ) -> str:
        """
        Начать новую транзакцию
        
        Args:
            timeout: Таймаут транзакции в секундах
            isolation_level: Уровень изоляции (DEFERRED, IMMEDIATE, EXCLUSIVE)
            
        Returns:
            ID транзакции
        """
        async with self._lock:
            await self._cleanup_stale_transactions()
            
            tx_id = self._generate_transaction_id()
            tx_info = TransactionInfo(
                id=tx_id,
                state=TransactionState.PENDING,
                started_at=time.time(),
                timeout=timeout,
                isolation_level=isolation_level
            )
            
            self._active_transactions[tx_id] = tx_info
            logging.debug(f"Transaction started: {tx_id}")
            return tx_id
    
    async def add_operation(
        self, 
        tx_id: str, 
        operation_type: str,
        query: str,
        params: tuple = (),
        rollback_query: Optional[str] = None,
        rollback_params: tuple = ()
    ) -> bool:
        """
        Добавить операцию в транзакцию
        
        Args:
            tx_id: ID транзакции
            operation_type: Тип операции (INSERT, UPDATE, DELETE, etc.)
            query: SQL запрос
            params: Параметры запроса
            rollback_query: SQL запрос для отката
            rollback_params: Параметры для отката
            
        Returns:
            True если операция добавлена, False если ошибка
        """
        async with self._lock:
            if tx_id not in self._active_transactions:
                logging.error(f"Transaction not found: {tx_id}")
                return False
            
            tx_info = self._active_transactions[tx_id]
            if tx_info.state != TransactionState.PENDING:
                logging.error(f"Transaction {tx_id} is not in PENDING state: {tx_info.state}")
                return False
            
            operation = {
                "type": operation_type,
                "query": query,
                "params": params,
                "rollback_query": rollback_query,
                "rollback_params": rollback_params,
                "added_at": time.time()
            }
            
            tx_info.operations.append(operation)
            logging.debug(f"Operation added to transaction {tx_id}: {operation_type}")
            return True
    
    async def commit_transaction(self, tx_id: str) -> bool:
        """
        Подтвердить транзакцию
        
        Args:
            tx_id: ID транзакции
            
        Returns:
            True если транзакция подтверждена, False если ошибка
        """
        async with self._lock:
            if tx_id not in self._active_transactions:
                logging.error(f"Transaction not found: {tx_id}")
                return False
            
            tx_info = self._active_transactions[tx_id]
            if tx_info.state != TransactionState.PENDING:
                logging.error(f"Transaction {tx_id} is not in PENDING state: {tx_info.state}")
                return False
            
            tx_info.state = TransactionState.ACTIVE
            logging.info(f"Transaction committed: {tx_id} with {len(tx_info.operations)} operations")
            
            # Удаляем транзакцию из активных
            del self._active_transactions[tx_id]
            return True
    
    async def rollback_transaction(self, tx_id: str) -> bool:
        """
        Откатить транзакцию
        
        Args:
            tx_id: ID транзакции
            
        Returns:
            True если транзакция откачена, False если ошибка
        """
        async with self._lock:
            if tx_id not in self._active_transactions:
                logging.warning(f"Transaction not found for rollback: {tx_id}")
                return False
            
            tx_info = self._active_transactions[tx_id]
            tx_info.state = TransactionState.ROLLED_BACK
            
            logging.info(f"Transaction rolled back: {tx_id}")
            
            # Удаляем транзакцию из активных
            del self._active_transactions[tx_id]
            return True
    
    def get_transaction_info(self, tx_id: str) -> Optional[TransactionInfo]:
        """Получить информацию о транзакции"""
        return self._active_transactions.get(tx_id)
    
    def get_active_transactions(self) -> Dict[str, TransactionInfo]:
        """Получить все активные транзакции"""
        return self._active_transactions.copy()
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Получить статистику транзакций"""
        current_time = time.time()
        active_count = len(self._active_transactions)
        
        # Статистика по состояниям
        state_counts = {}
        for tx_info in self._active_transactions.values():
            state = tx_info.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Статистика по времени
        oldest_transaction = None
        if self._active_transactions:
            oldest_transaction = min(
                self._active_transactions.values(),
                key=lambda tx: tx.started_at
            )
        
        return {
            "active_transactions": active_count,
            "state_counts": state_counts,
            "oldest_transaction_age": (
                current_time - oldest_transaction.started_at 
                if oldest_transaction else 0
            ),
            "cleanup_interval": self._cleanup_interval,
            "last_cleanup": self._last_cleanup
        }


# Глобальный экземпляр менеджера транзакций
_transaction_manager = TransactionManager()


def get_transaction_manager() -> TransactionManager:
    """Получить глобальный экземпляр менеджера транзакций"""
    return _transaction_manager


@asynccontextmanager
async def transaction(
    timeout: float = 30.0,
    isolation_level: str = "DEFERRED"
):
    """
    Контекстный менеджер для транзакций
    
    Args:
        timeout: Таймаут транзакции в секундах
        isolation_level: Уровень изоляции
    """
    manager = get_transaction_manager()
    tx_id = await manager.begin_transaction(timeout, isolation_level)
    
    try:
        yield tx_id
        await manager.commit_transaction(tx_id)
    except Exception as e:
        await manager.rollback_transaction(tx_id)
        raise


class DatabaseTransaction:
    """Класс для управления транзакциями базы данных"""
    
    def __init__(self, db):
        self.db = db
        self.transaction_manager = get_transaction_manager()
        self._current_transaction: Optional[str] = None
    
    async def begin(self, timeout: float = 30.0, isolation_level: str = "DEFERRED") -> str:
        """Начать транзакцию"""
        self._current_transaction = await self.transaction_manager.begin_transaction(
            timeout, isolation_level
        )
        return self._current_transaction
    
    async def add_operation(
        self,
        operation_type: str,
        query: str,
        params: tuple = (),
        rollback_query: Optional[str] = None,
        rollback_params: tuple = ()
    ) -> bool:
        """Добавить операцию в текущую транзакцию"""
        if not self._current_transaction:
            logging.error("No active transaction")
            return False
        
        return await self.transaction_manager.add_operation(
            self._current_transaction,
            operation_type,
            query,
            params,
            rollback_query,
            rollback_params
        )
    
    async def commit(self) -> bool:
        """Подтвердить транзакцию"""
        if not self._current_transaction:
            logging.error("No active transaction to commit")
            return False
        
        success = await self.transaction_manager.commit_transaction(self._current_transaction)
        if success:
            self._current_transaction = None
        return success
    
    async def rollback(self) -> bool:
        """Откатить транзакцию"""
        if not self._current_transaction:
            logging.error("No active transaction to rollback")
            return False
        
        success = await self.transaction_manager.rollback_transaction(self._current_transaction)
        if success:
            self._current_transaction = None
        return success
    
    @asynccontextmanager
    async def transaction_context(self, timeout: float = 30.0, isolation_level: str = "DEFERRED"):
        """Контекстный менеджер для транзакции"""
        tx_id = await self.begin(timeout, isolation_level)
        try:
            yield tx_id
            await self.commit()
        except Exception as e:
            await self.rollback()
            raise


# Утилиты для работы с транзакциями
async def execute_in_transaction(
    db,
    operations: List[Dict[str, Any]],
    timeout: float = 30.0
) -> bool:
    """
    Выполнить список операций в транзакции
    
    Args:
        db: Соединение с базой данных
        operations: Список операций
        timeout: Таймаут транзакции
        
    Returns:
        True если все операции выполнены успешно, False если ошибка
    """
    async with transaction(timeout) as tx_id:
        manager = get_transaction_manager()
        
        # Добавляем все операции в транзакцию
        for operation in operations:
            await manager.add_operation(
                tx_id,
                operation.get("type", "UNKNOWN"),
                operation["query"],
                operation.get("params", ()),
                operation.get("rollback_query"),
                operation.get("rollback_params", ())
            )
        
        # Выполняем операции
        try:
            async with db.execute("BEGIN TRANSACTION"):
                for operation in operations:
                    await db.execute(operation["query"], operation.get("params", ()))
                await db.commit()
            return True
        except Exception as e:
            logging.error(f"Transaction failed: {e}")
            await db.rollback()
            return False


def get_transaction_stats() -> Dict[str, Any]:
    """Получить статистику транзакций"""
    return _transaction_manager.get_transaction_stats()
