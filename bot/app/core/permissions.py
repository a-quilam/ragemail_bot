"""
Система ролей и разрешений
"""
from enum import Enum
from typing import Set, Optional, List
from dataclasses import dataclass

class Role(Enum):
    """Роли пользователей"""
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class Permission(Enum):
    """Разрешения"""
    # Управление пользователями
    MANAGE_USERS = "manage_users"
    ADD_ADMIN = "add_admin"
    REMOVE_ADMIN = "remove_admin"
    TRANSFER_ADMIN = "transfer_admin"
    
    # Управление ящиками
    CREATE_MAILBOX = "create_mailbox"
    DELETE_MAILBOX = "delete_mailbox"
    MANAGE_MAILBOX = "manage_mailbox"
    ACCESS_ANY_MAILBOX = "access_any_mailbox"
    
    # Антиспам
    MANAGE_ANTISPAM = "manage_antispam"
    BLOCK_WORDS = "block_words"
    MANAGE_COOLDOWNS = "manage_cooldowns"
    
    # Статистика
    VIEW_STATS = "view_stats"
    EXPORT_STATS = "export_stats"
    
    # Система
    MANAGE_BACKUPS = "manage_backups"
    SYSTEM_SETTINGS = "system_settings"
    VIEW_LOGS = "view_logs"
    
    # Посты
    PIN_POSTS = "pin_posts"
    DELETE_POSTS = "delete_posts"
    MANAGE_BUTTONS = "manage_buttons"

@dataclass
class AccessContext:
    """Контекст доступа"""
    user_id: int
    user_role: Role
    target_mailbox_id: Optional[int] = None
    target_user_id: Optional[int] = None
    is_mailbox_creator: bool = False

class PermissionManager:
    """Менеджер разрешений"""
    
    # Матрица ролей и разрешений
    ROLE_PERMISSIONS = {
        Role.USER: {
            Permission.CREATE_MAILBOX,
            Permission.VIEW_STATS,  # Только для своих ящиков
        },
        Role.ADMIN: {
            Permission.MANAGE_USERS,
            Permission.ADD_ADMIN,
            Permission.REMOVE_ADMIN,
            Permission.CREATE_MAILBOX,
            Permission.DELETE_MAILBOX,
            Permission.MANAGE_MAILBOX,
            Permission.ACCESS_ANY_MAILBOX,
            Permission.MANAGE_ANTISPAM,
            Permission.BLOCK_WORDS,
            Permission.MANAGE_COOLDOWNS,
            Permission.VIEW_STATS,
            Permission.EXPORT_STATS,
            Permission.MANAGE_BACKUPS,
            Permission.PIN_POSTS,
            Permission.DELETE_POSTS,
            Permission.MANAGE_BUTTONS,
        },
        Role.SUPERADMIN: {
            # Суперадмин имеет все разрешения
            *[perm for perm in Permission],
            Permission.TRANSFER_ADMIN,
            Permission.SYSTEM_SETTINGS,
            Permission.VIEW_LOGS,
        }
    }
    
    @classmethod
    def has_permission(cls, role: Role, permission: Permission) -> bool:
        """
        Проверить, есть ли у роли разрешение.
        
        Args:
            role: Роль пользователя
            permission: Разрешение
            
        Returns:
            True если есть разрешение
        """
        return permission in cls.ROLE_PERMISSIONS.get(role, set())
    
    @classmethod
    def get_role_permissions(cls, role: Role) -> Set[Permission]:
        """
        Получить все разрешения роли.
        
        Args:
            role: Роль пользователя
            
        Returns:
            Множество разрешений
        """
        return cls.ROLE_PERMISSIONS.get(role, set())
    
    @classmethod
    def can_access_mailbox(cls, context: AccessContext) -> bool:
        """
        Проверить доступ к ящику.
        
        Args:
            context: Контекст доступа
            
        Returns:
            True если есть доступ
        """
        # Суперадмин имеет доступ ко всем ящикам
        if context.user_role == Role.SUPERADMIN:
            return True
        
        # Админ имеет доступ ко всем ящикам
        if context.user_role == Role.ADMIN:
            return True
        
        # Обычный пользователь может управлять только своими ящиками
        if context.user_role == Role.USER:
            return context.is_mailbox_creator
        
        return False
    
    @classmethod
    def can_manage_user(cls, context: AccessContext) -> bool:
        """
        Проверить возможность управления пользователем.
        
        Args:
            context: Контекст доступа
            
        Returns:
            True если можно управлять
        """
        # Нельзя управлять самим собой
        if context.user_id == context.target_user_id:
            return False
        
        # Суперадмин может управлять всеми
        if context.user_role == Role.SUPERADMIN:
            return True
        
        # Админ может управлять только обычными пользователями
        if context.user_role == Role.ADMIN:
            # Здесь нужно проверить роль целевого пользователя
            # Пока возвращаем True, но в реальности нужно проверить роль
            return True
        
        return False
    
    @classmethod
    def require_permission(cls, permission: Permission):
        """
        Декоратор для проверки разрешений.
        
        Args:
            permission: Требуемое разрешение
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Извлекаем контекст из аргументов
                context = cls._extract_context_from_args(args, kwargs)
                
                if not cls.has_permission(context.user_role, permission):
                    raise PermissionError(f"Недостаточно прав для выполнения операции: {permission.value}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    @classmethod
    def require_mailbox_access(cls):
        """
        Декоратор для проверки доступа к ящику.
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                context = cls._extract_context_from_args(args, **kwargs)
                
                if not cls.can_access_mailbox(context):
                    raise PermissionError("Нет доступа к указанному ящику")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    @classmethod
    def _extract_context_from_args(cls, args, kwargs) -> AccessContext:
        """
        Извлечь контекст доступа из аргументов функции.
        
        Args:
            args: Позиционные аргументы
            kwargs: Именованные аргументы
            
        Returns:
            Контекст доступа
        """
        # Ищем объекты Message или CallbackQuery
        user_id = None
        user_role = Role.USER
        target_mailbox_id = kwargs.get('active_mailbox_id')
        target_user_id = kwargs.get('target_user_id')
        
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_id = arg.from_user.id
                # Здесь нужно получить роль из БД, пока используем дефолт
                break
        
        return AccessContext(
            user_id=user_id or 0,
            user_role=user_role,
            target_mailbox_id=target_mailbox_id,
            target_user_id=target_user_id
        )

def check_permission(role: Role, permission: Permission) -> bool:
    """Проверить разрешение для роли"""
    return PermissionManager.has_permission(role, permission)

def check_mailbox_access(user_role: Role, is_creator: bool) -> bool:
    """Проверить доступ к ящику"""
    context = AccessContext(
        user_id=0,
        user_role=user_role,
        is_mailbox_creator=is_creator
    )
    return PermissionManager.can_access_mailbox(context)

def get_user_permissions(role: Role) -> List[str]:
    """Получить список разрешений пользователя в виде строк"""
    permissions = PermissionManager.get_role_permissions(role)
    return [perm.value for perm in permissions]

def require_admin(func):
    """
    Декоратор для проверки прав администратора.
    Проверяет, что пользователь является админом или суперадмином.
    """
    async def wrapper(*args, **kwargs):
        # Извлекаем контекст из аргументов
        context = PermissionManager._extract_context_from_args(args, kwargs)
        
        if context.user_role not in [Role.ADMIN, Role.SUPERADMIN]:
            raise PermissionError("Недостаточно прав. Требуется роль администратора.")
        
        return await func(*args, **kwargs)
    return wrapper
