import aiosqlite
import os
import logging

async def connect(db_path: str) -> aiosqlite.Connection:
    first_time = not os.path.exists(db_path)
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    await apply_migrations(db)
    return db

async def apply_migrations(db: aiosqlite.Connection) -> None:
    # Применяем миграции напрямую без менеджера
    # Создаем таблицу для отслеживания миграций
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Проверяем целостность базы данных
    await check_database_integrity(db)
    
    # Проверяем, применена ли уже миграция 001
    result = await (await db.execute("SELECT version FROM schema_migrations WHERE version = '001'")).fetchone()
    if not result:
        # Применяем миграцию 001
        from .migrations.migration_manager import MigrationManager
        import os
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        manager = MigrationManager(db, migrations_dir)
        await manager.initialize()
        await manager.migrate_to_latest()
    
    # Создаем индексы для оптимизации запросов
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
        "CREATE INDEX IF NOT EXISTS idx_users_active_mailbox ON users(active_mailbox_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_mailboxes_channel_id ON mailboxes(channel_id)",
        "CREATE INDEX IF NOT EXISTS idx_mailboxes_creator_id ON mailboxes(creator_id)",
        "CREATE INDEX IF NOT EXISTS idx_posts_chat_message ON posts(chat_id, message_id)",
        "CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id)",
        "CREATE INDEX IF NOT EXISTS idx_posts_delete_at ON posts(delete_at)",
        "CREATE INDEX IF NOT EXISTS idx_extensions_post_key ON extensions(post_key)",
        "CREATE INDEX IF NOT EXISTS idx_extensions_user_kind ON extensions(user_id, kind)",
        "CREATE INDEX IF NOT EXISTS idx_relays_users ON relays(a_user_id, b_user_id)",
        "CREATE INDEX IF NOT EXISTS idx_relays_expires ON relays(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_stats_day_key ON stats(day, key)",
        "CREATE INDEX IF NOT EXISTS idx_aliases_user_day ON aliases(user_id, valid_day)",
        "CREATE INDEX IF NOT EXISTS idx_alias_blocks_word ON alias_blocks(blocked_word)",
        "CREATE INDEX IF NOT EXISTS idx_alias_blocks_expires ON alias_blocks(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_cooldowns_user ON user_cooldowns(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_cooldowns_until ON user_cooldowns(cooldown_until)"
    ]
    
    for index_sql in indexes:
        try:
            await db.execute(index_sql)
        except Exception:
            # Индекс уже существует или ошибка создания
            pass
    
    # Миграция: добавляем поле creator_id в mailboxes если его нет
    try:
        await db.execute("ALTER TABLE mailboxes ADD COLUMN creator_id INTEGER")
        await db.commit()
    except Exception:
        # Колонка уже существует
        pass
    
    # Миграция: создаем таблицу mailbox_admins если её нет
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mailbox_admins (
                mailbox_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (mailbox_id, user_id),
                FOREIGN KEY (mailbox_id) REFERENCES mailboxes(id) ON DELETE CASCADE
            )
        """)
        await db.commit()
    except Exception:
        # Таблица уже существует
        pass
    
    # Миграция: добавляем поле username в users если его нет
    try:
        await db.execute("ALTER TABLE users ADD COLUMN username TEXT")
        await db.commit()
    except Exception:
        # Колонка уже существует
        pass
    
    # Миграция: создаем таблицу mailbox_button_configs если её нет
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mailbox_button_configs (
                mailbox_id INTEGER PRIMARY KEY,
                button_config TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (mailbox_id) REFERENCES mailboxes(id) ON DELETE CASCADE
            )
        """)
        await db.commit()
    except Exception:
        # Таблица уже существует
        pass
    
    # Таблицы для системы антиспама создаются в миграции 001
    
    await db.commit()

async def check_database_integrity(db: aiosqlite.Connection) -> None:
    """Проверка целостности базы данных при запуске"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Проверяем основные таблицы
        required_tables = [
            'users', 'mailboxes', 'posts', 'extensions', 'relays', 
            'stats', 'aliases', 'alias_words', 'alias_blocks', 'user_cooldowns'
        ]
        
        for table in required_tables:
            result = await (await db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")).fetchone()
            if not result:
                logger.warning(f"Table {table} is missing, will be created by migrations")
        
        # Проверяем индексы
        indexes_result = await (await db.execute("SELECT name FROM sqlite_master WHERE type='index'")).fetchall()
        logger.info(f"Database has {len(indexes_result)} indexes")
        
        # Проверяем количество записей в основных таблицах
        for table in ['users', 'mailboxes', 'posts']:
            try:
                count_result = await (await db.execute(f"SELECT COUNT(*) FROM {table}")).fetchone()
                if count_result:
                    logger.info(f"Table {table} has {count_result[0]} records")
            except Exception as e:
                logger.warning(f"Could not check table {table}: {e}")
        
        logger.info("Database integrity check completed successfully")
        
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")
        # Не прерываем запуск, только логируем ошибку
