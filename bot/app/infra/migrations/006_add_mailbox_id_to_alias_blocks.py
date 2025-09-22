"""
Миграция 006: Добавление колонки mailbox_id в таблицу alias_blocks
"""
import logging

async def up(db):
    """Добавить колонку mailbox_id в таблицу alias_blocks"""
    try:
        # Проверяем, существует ли уже колонка mailbox_id
        cursor = await db.execute("PRAGMA table_info(alias_blocks)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'mailbox_id' not in column_names:
            # Добавляем колонку mailbox_id
            await db.execute("ALTER TABLE alias_blocks ADD COLUMN mailbox_id INTEGER")
            logging.info("Added mailbox_id column to alias_blocks table")
        else:
            logging.info("mailbox_id column already exists in alias_blocks table")
            
        # Создаем индекс для mailbox_id
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alias_blocks_mailbox_id ON alias_blocks(mailbox_id)")
        logging.info("Created index for mailbox_id in alias_blocks table")
        
    except Exception as e:
        logging.error(f"Error in migration 006: {e}")
        raise

async def down(db):
    """Удалить колонку mailbox_id из таблицы alias_blocks"""
    try:
        # Удаляем индекс
        await db.execute("DROP INDEX IF EXISTS idx_alias_blocks_mailbox_id")
        logging.info("Dropped index for mailbox_id in alias_blocks table")
        
        # Удаляем колонку mailbox_id
        await db.execute("ALTER TABLE alias_blocks DROP COLUMN mailbox_id")
        logging.info("Removed mailbox_id column from alias_blocks table")
        
    except Exception as e:
        logging.error(f"Error in migration 006 rollback: {e}")
        raise
