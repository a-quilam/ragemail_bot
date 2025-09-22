"""
Migration: Add Cancel Message ID to Delayed Queue
Description: Добавление поля cancel_message_id в таблицу delayed_queue для отслеживания сообщений с кнопкой отмены
Version: 008
Created: 2024-12-21T00:00:00
"""

version = "008"
name = "add_cancel_message_id"
description = "Добавление поля cancel_message_id в таблицу delayed_queue для отслеживания сообщений с кнопкой отмены"

up_sql = """
-- Добавляем колонку cancel_message_id в таблицу delayed_queue
ALTER TABLE delayed_queue ADD COLUMN cancel_message_id INTEGER;
"""

down_sql = """
-- Удаляем колонку cancel_message_id
-- SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
CREATE TABLE delayed_queue_old (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mailbox_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    ttl_seconds INTEGER NOT NULL,
    alias TEXT NOT NULL,
    run_at INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные обратно (без cancel_message_id)
INSERT INTO delayed_queue_old (id, user_id, mailbox_id, text, ttl_seconds, alias, run_at, created_at)
SELECT id, user_id, mailbox_id, text, ttl_seconds, alias, run_at, created_at
FROM delayed_queue;

-- Удаляем новую таблицу
DROP TABLE delayed_queue;

-- Переименовываем старую таблицу
ALTER TABLE delayed_queue_old RENAME TO delayed_queue;

-- Восстанавливаем индексы
CREATE INDEX IF NOT EXISTS idx_delayed_queue_run_at ON delayed_queue(run_at);
CREATE INDEX IF NOT EXISTS idx_delayed_queue_user ON delayed_queue(user_id);
"""
