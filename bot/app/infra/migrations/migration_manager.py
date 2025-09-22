"""
Менеджер миграций базы данных
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import aiosqlite

logger = logging.getLogger(__name__)

@dataclass
class Migration:
    """Миграция базы данных"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    created_at: datetime
    applied_at: Optional[datetime] = None

class MigrationManager:
    """
    Менеджер миграций базы данных.
    
    Управляет версионированием схемы базы данных,
    применением и откатом миграций.
    """
    
    def __init__(self, db: aiosqlite.Connection, migrations_dir: str):
        """
        Инициализация менеджера миграций.
        
        Args:
            db: Соединение с базой данных
            migrations_dir: Директория с файлами миграций
        """
        self.db = db
        self.migrations_dir = migrations_dir
        self.migrations_table = "schema_migrations"
    
    async def initialize(self) -> None:
        """Инициализация системы миграций"""
        # Создаем таблицу для отслеживания миграций
        await self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT
            )
        """)
        await self.db.commit()
        
        logger.info("Migration system initialized")
    
    async def get_applied_migrations(self) -> List[str]:
        """Получить список примененных миграций"""
        rows = await (await self.db.execute(
            f"SELECT version FROM {self.migrations_table} ORDER BY version"
        )).fetchall()
        return [row[0] for row in rows]
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Получить список непримененных миграций"""
        applied_versions = set(await self.get_applied_migrations())
        all_migrations = await self._load_migrations()
        
        pending = []
        for migration in all_migrations:
            if migration.version not in applied_versions:
                pending.append(migration)
        
        return sorted(pending, key=lambda m: m.version)
    
    async def _load_migrations(self) -> List[Migration]:
        """Загрузить все миграции из файлов"""
        migrations = []
        
        if not os.path.exists(self.migrations_dir):
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if not filename.endswith('.py'):
                continue
            
            try:
                migration = await self._load_migration_file(filename)
                if migration:
                    migrations.append(migration)
            except Exception as e:
                logger.error(f"Error loading migration {filename}: {e}")
        
        return migrations
    
    async def _load_migration_file(self, filename: str) -> Optional[Migration]:
        """Загрузить миграцию из файла"""
        filepath = os.path.join(self.migrations_dir, filename)
        
        # Извлекаем версию из имени файла (например: 001_initial_schema.py)
        version = filename.split('_')[0]
        name = filename.replace('.py', '').replace(f"{version}_", "")
        
        # Читаем содержимое файла
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Извлекаем SQL из файла (простая реализация)
        up_sql = self._extract_sql_from_content(content, 'up_sql')
        down_sql = self._extract_sql_from_content(content, 'down_sql')
        description = self._extract_description_from_content(content)
        
        if not up_sql:
            logger.warning(f"No up_sql found in migration {filename}")
            return None
        
        return Migration(
            version=version,
            name=name,
            description=description,
            up_sql=up_sql,
            down_sql=down_sql,
            created_at=datetime.now()
        )
    
    def _extract_sql_from_content(self, content: str, sql_type: str) -> str:
        """Извлечь SQL из содержимого файла"""
        lines = content.split('\n')
        sql_lines = []
        in_sql_block = False
        
        for line in lines:
            if f'{sql_type} = """' in line or f"{sql_type} = '''" in line:
                in_sql_block = True
                # Извлекаем SQL с той же строки
                sql_part = line.split('"""')[1] if '"""' in line else line.split("'''")[1]
                if sql_part.strip():
                    sql_lines.append(sql_part)
                continue
            
            if in_sql_block:
                if '"""' in line or "'''" in line:
                    # Конец SQL блока
                    sql_part = line.split('"""')[0] if '"""' in line else line.split("'''")[0]
                    if sql_part.strip():
                        sql_lines.append(sql_part)
                    break
                else:
                    sql_lines.append(line)
        
        return '\n'.join(sql_lines).strip()
    
    def _extract_description_from_content(self, content: str) -> str:
        """Извлечь описание из содержимого файла"""
        lines = content.split('\n')
        for line in lines:
            if 'description' in line and '=' in line:
                # Извлекаем описание
                desc = line.split('=')[1].strip().strip('"\'')
                return desc
        return ""
    
    def _split_sql_commands(self, sql: str) -> List[str]:
        """
        Разбить SQL на отдельные команды.
        
        Args:
            sql: SQL строка с несколькими командами
            
        Returns:
            Список отдельных SQL команд
        """
        # Разбиваем по точкам с запятой, но учитываем строки и комментарии
        commands = []
        current_command = ""
        in_string = False
        string_char = None
        
        i = 0
        while i < len(sql):
            char = sql[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_command += char
                elif char == ';':
                    # Конец команды
                    if current_command.strip():
                        commands.append(current_command.strip())
                    current_command = ""
                else:
                    current_command += char
            else:
                current_command += char
                if char == string_char and (i == 0 or sql[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        # Добавляем последнюю команду, если она есть
        if current_command.strip():
            commands.append(current_command.strip())
        
        return commands
    
    async def apply_migration(self, migration: Migration) -> bool:
        """
        Применить миграцию.
        
        Args:
            migration: Миграция для применения
            
        Returns:
            True если миграция применена успешно
        """
        try:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            # Разбиваем SQL на отдельные команды
            sql_commands = self._split_sql_commands(migration.up_sql)
            
            # Выполняем каждую команду отдельно
            for sql_command in sql_commands:
                if sql_command.strip():
                    await self.db.execute(sql_command)
            
            # Записываем информацию о примененной миграции
            await self.db.execute(f"""
                INSERT INTO {self.migrations_table} (version, name, description, applied_at)
                VALUES (?, ?, ?, ?)
            """, (migration.version, migration.name, migration.description, datetime.now()))
            
            await self.db.commit()
            
            logger.info(f"Migration {migration.version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migration {migration.version}: {e}")
            await self.db.rollback()
            return False
    
    async def rollback_migration(self, migration: Migration) -> bool:
        """
        Откатить миграцию.
        
        Args:
            migration: Миграция для отката
            
        Returns:
            True если миграция откачена успешно
        """
        try:
            logger.info(f"Rolling back migration {migration.version}: {migration.name}")
            
            # Выполняем SQL отката
            if migration.down_sql:
                await self.db.execute(migration.down_sql)
            
            # Удаляем запись о миграции
            await self.db.execute(f"""
                DELETE FROM {self.migrations_table} WHERE version = ?
            """, (migration.version,))
            
            await self.db.commit()
            
            logger.info(f"Migration {migration.version} rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migration {migration.version}: {e}")
            await self.db.rollback()
            return False
    
    async def migrate_to_latest(self) -> int:
        """
        Применить все непримененные миграции.
        
        Returns:
            Количество примененных миграций
        """
        pending_migrations = await self.get_pending_migrations()
        applied_count = 0
        
        for migration in pending_migrations:
            if await self.apply_migration(migration):
                applied_count += 1
            else:
                logger.error(f"Failed to apply migration {migration.version}, stopping")
                break
        
        if applied_count > 0:
            logger.info(f"Applied {applied_count} migrations")
        
        return applied_count
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Получить статус миграций"""
        applied_migrations = await self.get_applied_migrations()
        pending_migrations = await self.get_pending_migrations()
        
        return {
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_versions": applied_migrations,
            "pending_versions": [m.version for m in pending_migrations],
            "latest_applied": applied_migrations[-1] if applied_migrations else None,
            "next_pending": pending_migrations[0].version if pending_migrations else None
        }
    
    async def create_migration(self, name: str, description: str = "") -> str:
        """
        Создать новую миграцию.
        
        Args:
            name: Название миграции
            description: Описание миграции
            
        Returns:
            Путь к созданному файлу миграции
        """
        # Генерируем версию на основе текущего времени
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{version}_{name}.py"
        filepath = os.path.join(self.migrations_dir, filename)
        
        # Создаем директорию если не существует
        os.makedirs(self.migrations_dir, exist_ok=True)
        
        # Создаем шаблон миграции
        template = f'''"""
Migration: {name}
Description: {description}
Version: {version}
Created: {datetime.now().isoformat()}
"""

version = "{version}"
name = "{name}"
description = "{description}"

up_sql = """
-- SQL для применения миграции
-- Добавьте здесь SQL команды для применения изменений
"""

down_sql = """
-- SQL для отката миграции
-- Добавьте здесь SQL команды для отката изменений
"""
'''
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {filepath}")
        return filepath
