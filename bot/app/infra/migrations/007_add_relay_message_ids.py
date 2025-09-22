"""
Migration: Add Relay Message IDs
Description: Добавление полей для хранения ID сообщений анонимного чата для работы с реплаями
Version: 008
Created: 2025-01-22T00:00:00
"""

version = "007"
name = "add_relay_message_ids"
description = "Добавление полей для хранения ID сообщений анонимного чата для работы с реплаями"

up_sql = """
-- Добавляем поля для хранения ID сообщений анонимного чата
ALTER TABLE relays ADD COLUMN a_message_id INTEGER;
ALTER TABLE relays ADD COLUMN b_message_id INTEGER;
"""

down_sql = """
-- Удаляем добавленные поля (SQLite не поддерживает DROP COLUMN, поэтому создаем новую таблицу)
CREATE TABLE relays_backup AS SELECT id, a_user_id, b_user_id, a_alias, b_alias, expires_at, created_at FROM relays;
DROP TABLE relays;
ALTER TABLE relays_backup RENAME TO relays;
"""
