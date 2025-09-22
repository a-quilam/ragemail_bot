"""
Система отслеживания изменений ролей для event-driven кэша
"""
import logging
from typing import Dict, Any, Optional
from app.utils.event_driven_role_cache import get_event_driven_role_cache

class RoleChangeTracker:
    """
    Отслеживает все события изменения ролей и обновляет кэш
    """
    
    def __init__(self):
        self.cache = get_event_driven_role_cache()
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        # Добавляем обработчик для логирования событий
        self.cache.add_event_handler(self._log_role_event)
    
    async def _log_role_event(self, event_type: str, data: Dict[str, Any]):
        """Логирование событий изменения ролей"""
        if event_type == 'role_changed':
            logging.info(f"🔄 Role changed: user {data['user_id']} {data['old_role']} -> {data['new_role']}")
        elif event_type == 'role_invalidated':
            logging.info(f"🗑️ Role invalidated: user {data['user_id']} (was: {data['old_role']})")
        elif event_type == 'user_added':
            logging.info(f"➕ User added: {data['user_id']} -> {data['role']}")
        elif event_type == 'cache_cleared':
            logging.info(f"🧹 Cache cleared: {data['cleared_count']} entries")
    
    async def on_user_created(self, user_id: int, role: str = "user"):
        """
        Обработка создания нового пользователя
        
        Args:
            user_id: ID пользователя
            role: Роль пользователя
        """
        await self.cache.add_user(user_id, role)
        logging.info(f"📝 User created event: {user_id} -> {role}")
    
    async def on_role_changed(self, user_id: int, old_role: str, new_role: str):
        """
        Обработка изменения роли пользователя
        
        Args:
            user_id: ID пользователя
            old_role: Старая роль
            new_role: Новая роль
        """
        await self.cache.update_role(user_id, new_role)
        logging.info(f"📝 Role change event: {user_id} {old_role} -> {new_role}")
    
    async def on_admin_added(self, user_id: int, username: Optional[str] = None):
        """
        Обработка добавления нового администратора
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
        """
        await self.cache.update_role(user_id, "admin")
        logging.info(f"📝 Admin added event: {user_id} (@{username})")
    
    async def on_admin_removed(self, user_id: int, username: Optional[str] = None):
        """
        Обработка удаления администратора
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
        """
        await self.cache.update_role(user_id, "user")
        logging.info(f"📝 Admin removed event: {user_id} (@{username})")
    
    async def on_admin_transferred(self, from_user_id: int, to_user_id: int, mailbox_id: int):
        """
        Обработка передачи прав администратора
        
        Args:
            from_user_id: ID пользователя, передающего права
            to_user_id: ID пользователя, получающего права
            mailbox_id: ID ящика
        """
        # Получатель становится админом (если был обычным пользователем)
        await self.cache.update_role(to_user_id, "admin")
        logging.info(f"📝 Admin transfer event: {from_user_id} -> {to_user_id} (mailbox: {mailbox_id})")
    
    async def on_user_joined(self, user_id: int, username: Optional[str] = None):
        """
        Обработка присоединения нового пользователя
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
        """
        await self.cache.add_user(user_id, "user")
        logging.info(f"📝 User joined event: {user_id} (@{username})")
    
    async def on_user_left(self, user_id: int, username: Optional[str] = None):
        """
        Обработка ухода пользователя
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
        """
        await self.cache.remove_user(user_id)
        logging.info(f"📝 User left event: {user_id} (@{username})")
    
    async def on_superadmin_changed(self, old_superadmin_id: Optional[int], new_superadmin_id: int):
        """
        Обработка изменения суперадмина
        
        Args:
            old_superadmin_id: ID старого суперадмина
            new_superadmin_id: ID нового суперадмина
        """
        if old_superadmin_id:
            await self.cache.update_role(old_superadmin_id, "admin")
        await self.cache.update_role(new_superadmin_id, "superadmin")
        logging.info(f"📝 Superadmin changed: {old_superadmin_id} -> {new_superadmin_id}")

# Глобальный экземпляр трекера
_role_tracker: Optional[RoleChangeTracker] = None

def get_role_change_tracker() -> RoleChangeTracker:
    """
    Получить глобальный экземпляр трекера изменений ролей
    
    Returns:
        Экземпляр RoleChangeTracker
    """
    global _role_tracker
    if _role_tracker is None:
        _role_tracker = RoleChangeTracker()
    return _role_tracker

def init_role_change_tracker() -> RoleChangeTracker:
    """
    Инициализировать трекер изменений ролей
    
    Returns:
        Экземпляр RoleChangeTracker
    """
    global _role_tracker
    _role_tracker = RoleChangeTracker()
    return _role_tracker
