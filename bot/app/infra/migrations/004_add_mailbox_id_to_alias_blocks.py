"""
Migration: Add Mailbox ID to Alias Blocks
Description: Добавление mailbox_id в таблицу alias_blocks для локальных блокировок
Version: 004
Created: 2024-12-19T00:00:00
"""

version = "004"
name = "add_mailbox_id_to_alias_blocks"
description = "Добавление mailbox_id в таблицу alias_blocks для локальных блокировок"

up_sql = """
-- Добавляем колонку mailbox_id в таблицу alias_blocks
ALTER TABLE alias_blocks ADD COLUMN mailbox_id INTEGER;

-- Обновляем существующие записи, устанавливая mailbox_id = NULL для глобальных блокировок
-- (старые блокировки остаются глобальными для обратной совместимости)
UPDATE alias_blocks SET mailbox_id = NULL WHERE mailbox_id IS NULL;

-- Создаем индекс для быстрого поиска по mailbox_id
CREATE INDEX IF NOT EXISTS idx_alias_blocks_mailbox ON alias_blocks(mailbox_id);
"""

down_sql = """
-- Удаляем индекс
DROP INDEX IF EXISTS idx_alias_blocks_mailbox;

-- Удаляем колонку mailbox_id
-- SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
CREATE TABLE alias_blocks_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocked_word TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    reason TEXT DEFAULT '',
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные обратно (без mailbox_id)
INSERT INTO alias_blocks_old (id, blocked_word, admin_id, reason, expires_at, created_at)
SELECT id, blocked_word, admin_id, reason, expires_at, created_at
FROM alias_blocks;

-- Удаляем новую таблицу
DROP TABLE alias_blocks;

-- Переименовываем старую таблицу
ALTER TABLE alias_blocks_old RENAME TO alias_blocks;

-- Восстанавливаем индексы
CREATE INDEX IF NOT EXISTS idx_alias_blocks_word ON alias_blocks(blocked_word);
CREATE INDEX IF NOT EXISTS idx_alias_blocks_expires ON alias_blocks(expires_at);
"""
