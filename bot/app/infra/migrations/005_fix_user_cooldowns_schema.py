"""
Migration: Fix User Cooldowns Schema
Description: Добавление недостающих колонок alias, reason и mailbox_id в таблицу user_cooldowns
Version: 005
Created: 2024-12-19T00:00:00
"""

version = "005"
name = "fix_user_cooldowns_schema"
description = "Добавление недостающих колонок alias, reason и mailbox_id в таблицу user_cooldowns"

up_sql = """
-- Добавляем колонку alias в таблицу user_cooldowns
ALTER TABLE user_cooldowns ADD COLUMN alias TEXT;

-- Добавляем колонку reason в таблицу user_cooldowns
ALTER TABLE user_cooldowns ADD COLUMN reason TEXT DEFAULT '';

-- Добавляем колонку mailbox_id в таблицу user_cooldowns для локальных кулдаунов
ALTER TABLE user_cooldowns ADD COLUMN mailbox_id INTEGER;

-- Обновляем существующие записи, устанавливая значения по умолчанию
UPDATE user_cooldowns SET alias = 'Unknown', reason = '', mailbox_id = NULL WHERE alias IS NULL;

-- Создаем индекс для быстрого поиска по mailbox_id
CREATE INDEX IF NOT EXISTS idx_user_cooldowns_mailbox ON user_cooldowns(mailbox_id);
"""

down_sql = """
-- Удаляем индекс
DROP INDEX IF EXISTS idx_user_cooldowns_mailbox;

-- Удаляем добавленные колонки
-- SQLite не поддерживает DROP COLUMN, поэтому пересоздаем таблицу
CREATE TABLE user_cooldowns_old (
    user_id INTEGER PRIMARY KEY,
    cooldown_until INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Копируем данные обратно (без alias, reason, mailbox_id)
INSERT INTO user_cooldowns_old (user_id, cooldown_until, created_at)
SELECT user_id, cooldown_until, created_at
FROM user_cooldowns;

-- Удаляем новую таблицу
DROP TABLE user_cooldowns;

-- Переименовываем старую таблицу
ALTER TABLE user_cooldowns_old RENAME TO user_cooldowns;

-- Восстанавливаем индексы
CREATE INDEX IF NOT EXISTS idx_cooldowns_user ON user_cooldowns(user_id);
CREATE INDEX IF NOT EXISTS idx_cooldowns_until ON user_cooldowns(cooldown_until);
"""
