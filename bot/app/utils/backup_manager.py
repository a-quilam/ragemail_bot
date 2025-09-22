"""
Backup management utilities for critical data protection
"""
import asyncio
import logging
import time
import json
import os
import shutil
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
try:
    import aiosqlite
except ImportError:
    aiosqlite = None
try:
    import aiofiles
except ImportError:
    aiofiles = None


@dataclass
class BackupInfo:
    """Информация о резервной копии"""
    id: str
    name: str
    created_at: float
    size_bytes: int
    backup_type: str
    status: str  # "created", "verified", "failed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None


class BackupManager:
    """Менеджер резервного копирования для критических данных"""
    
    def __init__(self, backup_dir: str = "backups", max_backups: int = 10):
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self._backups: Dict[str, BackupInfo] = {}
        self._lock = None  # Will be initialized when needed
        
        # Создаем директорию для бэкапов
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Загружаем информацию о существующих бэкапах (синхронно)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если цикл уже запущен, создаем задачу
                asyncio.create_task(self._load_existing_backups())
            else:
                # Если цикл не запущен, запускаем синхронно
                loop.run_until_complete(self._load_existing_backups())
        except RuntimeError:
            # Нет активного цикла событий, пропускаем загрузку
            pass
    
    async def _load_existing_backups(self):
        """Загрузить информацию о существующих резервных копиях"""
        try:
            metadata_file = self.backup_dir / "backups_metadata.json"
            if metadata_file.exists():
                async with aiofiles.open(metadata_file, 'r') as f:
                    content = await f.read()
                    metadata = json.loads(content)
                    
                    for backup_id, backup_data in metadata.items():
                        self._backups[backup_id] = BackupInfo(**backup_data)
                        
                logging.info(f"Loaded {len(self._backups)} existing backups")
        except Exception as e:
            logging.error(f"Error loading existing backups: {e}")
    
    async def _save_backups_metadata(self):
        """Сохранить метаданные резервных копий"""
        try:
            metadata_file = self.backup_dir / "backups_metadata.json"
            metadata = {}
            
            for backup_id, backup_info in self._backups.items():
                metadata[backup_id] = {
                    "id": backup_info.id,
                    "name": backup_info.name,
                    "created_at": backup_info.created_at,
                    "size_bytes": backup_info.size_bytes,
                    "backup_type": backup_info.backup_type,
                    "status": backup_info.status,
                    "metadata": backup_info.metadata,
                    "file_path": backup_info.file_path
                }
            
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
                
        except Exception as e:
            logging.error(f"Error saving backups metadata: {e}")
    
    def _generate_backup_id(self) -> str:
        """Генерация уникального ID для резервной копии"""
        timestamp = int(time.time())
        return f"backup_{timestamp}"
    
    async def create_database_backup(
        self, 
        db_path: str, 
        backup_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Создать резервную копию базы данных
        
        Args:
            db_path: Путь к файлу базы данных
            backup_name: Имя резервной копии
            
        Returns:
            ID резервной копии или None если ошибка
        """
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                backup_id = self._generate_backup_id()
                if not backup_name:
                    backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                backup_filename = f"{backup_name}_{backup_id}.db"
                backup_path = self.backup_dir / backup_filename
                
                # Копируем файл базы данных
                shutil.copy2(db_path, backup_path)
                
                # Получаем размер файла
                file_size = backup_path.stat().st_size
                
                # Создаем информацию о резервной копии
                backup_info = BackupInfo(
                    id=backup_id,
                    name=backup_name,
                    created_at=time.time(),
                    size_bytes=file_size,
                    backup_type="database",
                    status="created",
                    file_path=str(backup_path),
                    metadata={
                        "source_db": db_path,
                        "backup_format": "sqlite"
                    }
                )
                
                self._backups[backup_id] = backup_info
                await self._save_backups_metadata()
                
                # Проверяем целостность резервной копии
                if await self._verify_database_backup(backup_path):
                    backup_info.status = "verified"
                    await self._save_backups_metadata()
                    logging.info(f"Database backup created and verified: {backup_id}")
                else:
                    backup_info.status = "failed"
                    await self._save_backups_metadata()
                    logging.error(f"Database backup verification failed: {backup_id}")
                    return None
                
                # Очищаем старые резервные копии
                await self._cleanup_old_backups()
                
                return backup_id
                
            except Exception as e:
                logging.error(f"Error creating database backup: {e}")
                return None
    
    async def _verify_database_backup(self, backup_path: Path) -> bool:
        """Проверить целостность резервной копии базы данных"""
        try:
            async with aiosqlite.connect(backup_path) as db:
                # Проверяем, что база данных открывается
                cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = await cursor.fetchall()
                
                # Проверяем основные таблицы
                expected_tables = ['users', 'mailboxes', 'stats']
                existing_tables = [table[0] for table in tables]
                
                for expected_table in expected_tables:
                    if expected_table not in existing_tables:
                        logging.warning(f"Expected table {expected_table} not found in backup")
                        return False
                
                # Проверяем целостность базы данных
                cursor = await db.execute("PRAGMA integrity_check")
                result = await cursor.fetchone()
                
                if result and result[0] == "ok":
                    return True
                else:
                    logging.error(f"Database integrity check failed: {result}")
                    return False
                    
        except Exception as e:
            logging.error(f"Error verifying database backup: {e}")
            return False
    
    async def create_config_backup(
        self, 
        config_data: Dict[str, Any], 
        backup_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Создать резервную копию конфигурации
        
        Args:
            config_data: Данные конфигурации
            backup_name: Имя резервной копии
            
        Returns:
            ID резервной копии или None если ошибка
        """
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                backup_id = self._generate_backup_id()
                if not backup_name:
                    backup_name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                backup_filename = f"{backup_name}_{backup_id}.json"
                backup_path = self.backup_dir / backup_filename
                
                # Сохраняем конфигурацию в JSON
                async with aiofiles.open(backup_path, 'w') as f:
                    await f.write(json.dumps(config_data, indent=2, ensure_ascii=False))
                
                # Получаем размер файла
                file_size = backup_path.stat().st_size
                
                # Создаем информацию о резервной копии
                backup_info = BackupInfo(
                    id=backup_id,
                    name=backup_name,
                    created_at=time.time(),
                    size_bytes=file_size,
                    backup_type="config",
                    status="created",
                    file_path=str(backup_path),
                    metadata={
                        "config_keys": list(config_data.keys()),
                        "backup_format": "json"
                    }
                )
                
                self._backups[backup_id] = backup_info
                await self._save_backups_metadata()
                
                logging.info(f"Config backup created: {backup_id}")
                return backup_id
                
            except Exception as e:
                logging.error(f"Error creating config backup: {e}")
                return None
    
    async def restore_database_backup(self, backup_id: str, target_db_path: str) -> bool:
        """
        Восстановить базу данных из резервной копии
        
        Args:
            backup_id: ID резервной копии
            target_db_path: Путь к целевой базе данных
            
        Returns:
            True если восстановление успешно, False если ошибка
        """
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                if backup_id not in self._backups:
                    logging.error(f"Backup not found: {backup_id}")
                    return False
                
                backup_info = self._backups[backup_id]
                if backup_info.backup_type != "database":
                    logging.error(f"Backup {backup_id} is not a database backup")
                    return False
                
                if not backup_info.file_path or not Path(backup_info.file_path).exists():
                    logging.error(f"Backup file not found: {backup_info.file_path}")
                    return False
                
                # Создаем резервную копию текущей базы данных
                if Path(target_db_path).exists():
                    current_backup_id = await self.create_database_backup(
                        target_db_path, 
                        f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    if not current_backup_id:
                        logging.error("Failed to create backup of current database before restore")
                        return False
                
                # Копируем резервную копию
                shutil.copy2(backup_info.file_path, target_db_path)
                
                # Проверяем целостность восстановленной базы данных
                if await self._verify_database_backup(Path(target_db_path)):
                    logging.info(f"Database restored successfully from backup: {backup_id}")
                    return True
                else:
                    logging.error(f"Restored database integrity check failed: {backup_id}")
                    return False
                    
            except Exception as e:
                logging.error(f"Error restoring database backup: {e}")
                return False
    
    async def restore_config_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Восстановить конфигурацию из резервной копии
        
        Args:
            backup_id: ID резервной копии
            
        Returns:
            Данные конфигурации или None если ошибка
        """
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                if backup_id not in self._backups:
                    logging.error(f"Backup not found: {backup_id}")
                    return None
                
                backup_info = self._backups[backup_id]
                if backup_info.backup_type != "config":
                    logging.error(f"Backup {backup_id} is not a config backup")
                    return None
                
                if not backup_info.file_path or not Path(backup_info.file_path).exists():
                    logging.error(f"Backup file not found: {backup_info.file_path}")
                    return None
                
                # Читаем конфигурацию
                async with aiofiles.open(backup_info.file_path, 'r') as f:
                    content = await f.read()
                    config_data = json.loads(content)
                
                logging.info(f"Config restored successfully from backup: {backup_id}")
                return config_data
                
            except Exception as e:
                logging.error(f"Error restoring config backup: {e}")
                return None
    
    async def _cleanup_old_backups(self):
        """Очистка старых резервных копий"""
        try:
            # Сортируем резервные копии по дате создания
            sorted_backups = sorted(
                self._backups.items(),
                key=lambda x: x[1].created_at,
                reverse=True
            )
            
            # Удаляем старые резервные копии
            if len(sorted_backups) > self.max_backups:
                backups_to_remove = sorted_backups[self.max_backups:]
                
                for backup_id, backup_info in backups_to_remove:
                    # Удаляем файл
                    if backup_info.file_path and Path(backup_info.file_path).exists():
                        Path(backup_info.file_path).unlink()
                    
                    # Удаляем из словаря
                    del self._backups[backup_id]
                    
                    logging.info(f"Removed old backup: {backup_id}")
                
                await self._save_backups_metadata()
                
        except Exception as e:
            logging.error(f"Error cleaning up old backups: {e}")
    
    async def list_backups(self) -> List[BackupInfo]:
        """Получить список всех резервных копий"""
        return list(self._backups.values())
    
    async def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """Получить информацию о резервной копии"""
        return self._backups.get(backup_id)
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Удалить резервную копию"""
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                if backup_id not in self._backups:
                    logging.error(f"Backup not found: {backup_id}")
                    return False
                
                backup_info = self._backups[backup_id]
                
                # Удаляем файл
                if backup_info.file_path and Path(backup_info.file_path).exists():
                    Path(backup_info.file_path).unlink()
                
                # Удаляем из словаря
                del self._backups[backup_id]
                await self._save_backups_metadata()
                
                logging.info(f"Backup deleted: {backup_id}")
                return True
                
            except Exception as e:
                logging.error(f"Error deleting backup: {e}")
                return False
    
    async def get_backup_stats(self) -> Dict[str, Any]:
        """Получить статистику резервных копий"""
        total_size = sum(backup.size_bytes for backup in self._backups.values())
        backup_types = {}
        
        for backup in self._backups.values():
            backup_type = backup.backup_type
            if backup_type not in backup_types:
                backup_types[backup_type] = {"count": 0, "size": 0}
            backup_types[backup_type]["count"] += 1
            backup_types[backup_type]["size"] += backup.size_bytes
        
        return {
            "total_backups": len(self._backups),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "backup_types": backup_types,
            "max_backups": self.max_backups,
            "backup_directory": str(self.backup_dir)
        }


# Глобальный экземпляр менеджера резервного копирования
_backup_manager = BackupManager()


def get_backup_manager() -> BackupManager:
    """Получить глобальный экземпляр менеджера резервного копирования"""
    return _backup_manager


# Утилиты для автоматического резервного копирования
async def auto_backup_database(db_path: str, interval_hours: int = 24) -> bool:
    """
    Автоматическое резервное копирование базы данных
    
    Args:
        db_path: Путь к базе данных
        interval_hours: Интервал между резервными копиями в часах
        
    Returns:
        True если резервная копия создана, False если ошибка
    """
    try:
        manager = get_backup_manager()
        backup_id = await manager.create_database_backup(db_path)
        return backup_id is not None
    except Exception as e:
        logging.error(f"Error in auto backup: {e}")
        return False


async def schedule_regular_backups(db_path: str, interval_hours: int = 24):
    """
    Запланировать регулярные резервные копии
    
    Args:
        db_path: Путь к базе данных
        interval_hours: Интервал между резервными копиями в часах
    """
    while True:
        try:
            await auto_backup_database(db_path, interval_hours)
            await asyncio.sleep(interval_hours * 3600)  # Конвертируем часы в секунды
        except Exception as e:
            logging.error(f"Error in scheduled backup: {e}")
            await asyncio.sleep(3600)  # Ждем час перед повторной попыткой
