"""
Migration: Add Relay Messages History
Description: Создание таблицы relay_messages для хранения истории отправленных сообщений в анонимных чатах
Version: 009
Created: 2025-02-15T00:00:00
"""

version = "009"
name = "add_relay_messages_history"
description = "Создание таблицы relay_messages для хранения истории отправленных сообщений в анонимных чатах"

up_sql = """
CREATE TABLE IF NOT EXISTS relay_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    FOREIGN KEY(relay_id) REFERENCES relays(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relay_messages_user_message ON relay_messages(user_id, message_id);
CREATE INDEX IF NOT EXISTS idx_relay_messages_relay ON relay_messages(relay_id);
"""

down_sql = """
DROP TABLE IF EXISTS relay_messages;
"""
