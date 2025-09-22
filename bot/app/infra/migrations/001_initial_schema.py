"""
Migration: Initial Schema
Description: Создание базовой схемы базы данных
Version: 001
Created: 2024-01-01T00:00:00
"""

version = "001"
name = "initial_schema"
description = "Создание базовой схемы базы данных"

up_sql = """
-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'user',
    active_mailbox_id INTEGER,
    last_bind_mailbox_id INTEGER,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы почтовых ящиков
CREATE TABLE IF NOT EXISTS mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    channel_id INTEGER NOT NULL UNIQUE,
    creator_id INTEGER NOT NULL,
    stat_day INTEGER,
    stat_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы постов
CREATE TABLE IF NOT EXISTS posts (
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    base_text TEXT NOT NULL,
    base_delete_at INTEGER NOT NULL,
    delete_at INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id, message_id)
);

-- Создание таблицы расширений
CREATE TABLE IF NOT EXISTS extensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_key TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_key, user_id, kind)
);

-- Создание таблицы релеев
CREATE TABLE IF NOT EXISTS relays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    a_user_id INTEGER NOT NULL,
    b_user_id INTEGER NOT NULL,
    a_alias TEXT NOT NULL,
    b_alias TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы статистики
CREATE TABLE IF NOT EXISTS stats (
    day TEXT NOT NULL,
    key TEXT NOT NULL,
    cnt INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (day, key)
);

-- Создание таблицы псевдонимов
CREATE TABLE IF NOT EXISTS aliases (
    user_id INTEGER NOT NULL,
    valid_day TEXT NOT NULL,
    alias TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, valid_day)
);

-- Создание таблицы слов для псевдонимов
CREATE TABLE IF NOT EXISTS alias_words (
    word TEXT PRIMARY KEY,
    word_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы блокировок слов
CREATE TABLE IF NOT EXISTS alias_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocked_word TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    reason TEXT DEFAULT '',
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы кулдаунов пользователей
CREATE TABLE IF NOT EXISTS user_cooldowns (
    user_id INTEGER PRIMARY KEY,
    alias TEXT NOT NULL,
    cooldown_until TEXT NOT NULL,
    reason TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы конфигурации кнопок
CREATE TABLE IF NOT EXISTS button_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mailbox_id INTEGER NOT NULL,
    button_text TEXT NOT NULL,
    button_action TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mailbox_id, button_text)
);

-- Создание таблицы отложенной очереди
CREATE TABLE IF NOT EXISTS delayed_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mailbox_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    ttl_seconds INTEGER NOT NULL,
    alias TEXT NOT NULL,
    run_at INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

down_sql = """
-- Удаление всех таблиц
DROP TABLE IF EXISTS delayed_queue;
DROP TABLE IF EXISTS button_configs;
DROP TABLE IF EXISTS user_cooldowns;
DROP TABLE IF EXISTS alias_blocks;
DROP TABLE IF EXISTS alias_words;
DROP TABLE IF EXISTS aliases;
DROP TABLE IF EXISTS stats;
DROP TABLE IF EXISTS relays;
DROP TABLE IF EXISTS extensions;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS mailboxes;
DROP TABLE IF EXISTS users;
"""
