"""
Простое логирование админских действий
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

# Создаем отдельный логгер для админских действий
admin_logger = logging.getLogger("admin_actions")

def log_admin_action(
    admin_id: int,
    action: str,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
    tz: Optional[ZoneInfo] = None
) -> None:
    """
    Логирует админское действие
    
    Args:
        admin_id: ID администратора
        action: Действие (add_admin, remove_admin, delete_mailbox, etc.)
        target_id: ID цели действия (опционально)
        details: Дополнительные детали (опционально)
        tz: Часовой пояс (опционально)
    """
    timestamp = datetime.now(tz or ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
    
    log_parts = [
        f"[{timestamp}]",
        f"ADMIN:{admin_id}",
        f"ACTION:{action}"
    ]
    
    if target_id:
        log_parts.append(f"TARGET:{target_id}")
    
    if details:
        log_parts.append(f"DETAILS:{details}")
    
    log_message = " | ".join(log_parts)
    admin_logger.info(log_message)

# Удобные функции для конкретных действий
def log_add_admin(admin_id: int, new_admin_id: int, username: Optional[str] = None):
    """Логирует добавление администратора"""
    details = f"username:{username}" if username else None
    log_admin_action(admin_id, "add_admin", new_admin_id, details)

def log_remove_admin(admin_id: int, removed_admin_id: int, username: Optional[str] = None):
    """Логирует удаление администратора"""
    details = f"username:{username}" if username else None
    log_admin_action(admin_id, "remove_admin", removed_admin_id, details)

def log_create_mailbox(admin_id: int, mailbox_id: int, title: str):
    """Логирует создание ящика"""
    log_admin_action(admin_id, "create_mailbox", mailbox_id, f"title:{title}")

def log_delete_mailbox(admin_id: int, mailbox_id: int, title: str):
    """Логирует удаление ящика"""
    log_admin_action(admin_id, "delete_mailbox", mailbox_id, f"title:{title}")

def log_block_word(admin_id: int, word: str, reason: Optional[str] = None):
    """Логирует блокировку слова"""
    details = f"reason:{reason}" if reason else None
    log_admin_action(admin_id, "block_word", None, f"word:{word}|{details}")

def log_unblock_word(admin_id: int, word: str):
    """Логирует разблокировку слова"""
    log_admin_action(admin_id, "unblock_word", None, f"word:{word}")

def log_cooldown_user(admin_id: int, user_id: int, alias: str, reason: Optional[str] = None):
    """Логирует установку кулдауна"""
    details = f"alias:{alias}|reason:{reason}" if reason else f"alias:{alias}"
    log_admin_action(admin_id, "cooldown_user", user_id, details)

def log_backup_created(admin_id: int, backup_file: str):
    """Логирует создание бэкапа"""
    log_admin_action(admin_id, "backup_created", None, f"file:{backup_file}")

def log_backup_restored(admin_id: int, backup_file: str):
    """Логирует восстановление из бэкапа"""
    log_admin_action(admin_id, "backup_restored", None, f"file:{backup_file}")
