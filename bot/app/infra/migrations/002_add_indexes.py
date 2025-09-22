"""
Migration: Add Indexes
Description: Добавление индексов для оптимизации запросов
Version: 002
Created: 2024-01-01T00:00:00
"""

version = "002"
name = "add_indexes"
description = "Добавление индексов для оптимизации запросов"

up_sql = """
-- Индексы для таблицы пользователей
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active_mailbox ON users(active_mailbox_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Индексы для таблицы почтовых ящиков
CREATE INDEX IF NOT EXISTS idx_mailboxes_channel_id ON mailboxes(channel_id);
CREATE INDEX IF NOT EXISTS idx_mailboxes_creator_id ON mailboxes(creator_id);

-- Индексы для таблицы постов
CREATE INDEX IF NOT EXISTS idx_posts_chat_message ON posts(chat_id, message_id);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_delete_at ON posts(delete_at);

-- Индексы для таблицы расширений
CREATE INDEX IF NOT EXISTS idx_extensions_post_key ON extensions(post_key);
CREATE INDEX IF NOT EXISTS idx_extensions_user_kind ON extensions(user_id, kind);

-- Индексы для таблицы релеев
CREATE INDEX IF NOT EXISTS idx_relays_users ON relays(a_user_id, b_user_id);
CREATE INDEX IF NOT EXISTS idx_relays_expires ON relays(expires_at);

-- Индексы для таблицы статистики
CREATE INDEX IF NOT EXISTS idx_stats_day_key ON stats(day, key);

-- Индексы для таблицы псевдонимов
CREATE INDEX IF NOT EXISTS idx_aliases_user_day ON aliases(user_id, valid_day);

-- Индексы для таблицы блокировок слов
CREATE INDEX IF NOT EXISTS idx_alias_blocks_word ON alias_blocks(blocked_word);
CREATE INDEX IF NOT EXISTS idx_alias_blocks_expires ON alias_blocks(expires_at);

-- Индексы для таблицы кулдаунов
CREATE INDEX IF NOT EXISTS idx_cooldowns_user ON user_cooldowns(user_id);
CREATE INDEX IF NOT EXISTS idx_cooldowns_until ON user_cooldowns(cooldown_until);

-- Индексы для таблицы конфигурации кнопок
CREATE INDEX IF NOT EXISTS idx_button_configs_mailbox ON button_configs(mailbox_id);

-- Индексы для таблицы отложенной очереди
CREATE INDEX IF NOT EXISTS idx_delayed_queue_run_at ON delayed_queue(run_at);
CREATE INDEX IF NOT EXISTS idx_delayed_queue_user ON delayed_queue(user_id);
"""

down_sql = """
-- Удаление всех индексов
DROP INDEX IF EXISTS idx_delayed_queue_user;
DROP INDEX IF EXISTS idx_delayed_queue_run_at;
DROP INDEX IF EXISTS idx_button_configs_mailbox;
DROP INDEX IF EXISTS idx_cooldowns_until;
DROP INDEX IF EXISTS idx_cooldowns_user;
DROP INDEX IF EXISTS idx_alias_blocks_expires;
DROP INDEX IF EXISTS idx_alias_blocks_word;
DROP INDEX IF EXISTS idx_aliases_user_day;
DROP INDEX IF EXISTS idx_stats_day_key;
DROP INDEX IF EXISTS idx_relays_expires;
DROP INDEX IF EXISTS idx_relays_users;
DROP INDEX IF EXISTS idx_extensions_user_kind;
DROP INDEX IF EXISTS idx_extensions_post_key;
DROP INDEX IF EXISTS idx_posts_delete_at;
DROP INDEX IF EXISTS idx_posts_author_id;
DROP INDEX IF EXISTS idx_posts_chat_message;
DROP INDEX IF EXISTS idx_mailboxes_creator_id;
DROP INDEX IF EXISTS idx_mailboxes_channel_id;
DROP INDEX IF EXISTS idx_users_username;
DROP INDEX IF EXISTS idx_users_active_mailbox;
DROP INDEX IF EXISTS idx_users_role;
"""
