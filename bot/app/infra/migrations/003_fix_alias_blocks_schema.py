"""
Migration: Fix Alias Blocks Schema
Description: Добавление недостающих колонок admin_id и reason в таблицу alias_blocks
Version: 003
Created: 2024-12-19T00:00:00
"""

version = "003"
name = "fix_alias_blocks_schema"
description = "Добавление недостающих колонок admin_id и reason в таблицу alias_blocks"

up_sql = """
-- Добавляем колонку admin_id в таблицу alias_blocks
ALTER TABLE alias_blocks ADD COLUMN admin_id INTEGER;

-- Добавляем колонку reason в таблицу alias_blocks
ALTER TABLE alias_blocks ADD COLUMN reason TEXT DEFAULT '';

-- Обновляем существующие записи, устанавливая admin_id = 0 для старых записей
UPDATE alias_blocks SET admin_id = 0 WHERE admin_id IS NULL;

-- Делаем колонку admin_id NOT NULL после обновления данных
-- SQLite не поддерживает ALTER COLUMN, поэтому пересоздаем таблицу
CREATE TABLE alias_blocks_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocked_word TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    reason TEXT DEFAULT '',
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные из старой таблицы
INSERT INTO alias_blocks_new (id, blocked_word, admin_id, reason, expires_at, created_at)
SELECT id, blocked_word, COALESCE(admin_id, 0), COALESCE(reason, ''), expires_at, created_at
FROM alias_blocks;

-- Удаляем старую таблицу
DROP TABLE alias_blocks;

-- Переименовываем новую таблицу
ALTER TABLE alias_blocks_new RENAME TO alias_blocks;

-- Восстанавливаем индексы
CREATE INDEX IF NOT EXISTS idx_alias_blocks_word ON alias_blocks(blocked_word);
CREATE INDEX IF NOT EXISTS idx_alias_blocks_expires ON alias_blocks(expires_at);
"""

down_sql = """
-- Откат: удаляем колонки admin_id и reason
-- SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
CREATE TABLE alias_blocks_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocked_word TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные обратно (без admin_id и reason)
INSERT INTO alias_blocks_old (id, blocked_word, expires_at, created_at)
SELECT id, blocked_word, expires_at, created_at
FROM alias_blocks;

-- Удаляем новую таблицу
DROP TABLE alias_blocks;

-- Переименовываем старую таблицу
ALTER TABLE alias_blocks_old RENAME TO alias_blocks;

-- Восстанавливаем индексы
CREATE INDEX IF NOT EXISTS idx_alias_blocks_word ON alias_blocks(blocked_word);
CREATE INDEX IF NOT EXISTS idx_alias_blocks_expires ON alias_blocks(expires_at);
"""
