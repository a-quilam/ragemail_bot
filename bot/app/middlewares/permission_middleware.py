"""
Middleware для проверки прав доступа
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from app.core.permissions import PermissionManager, Role, AccessContext
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
import logging

logger = logging.getLogger(__name__)

class PermissionMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав доступа.
    
    Автоматически проверяет права пользователя перед выполнением
    обработчиков команд и callback'ов.
    """
    
    def __init__(self, users_repo: UsersRepo, mailboxes_repo: MailboxesRepo):
        """
        Инициализация middleware.
        
        Args:
            users_repo: Репозиторий пользователей
            mailboxes_repo: Репозиторий ящиков
        """
        self.users_repo = users_repo
        self.mailboxes_repo = mailboxes_repo
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с проверкой прав доступа.
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные для обработчика
            
        Returns:
            Результат обработки события
        """
        # Получаем информацию о пользователе
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)
        
        # Получаем роль пользователя с кэшированием
        from app.utils.role_cache import get_role_cache
        role_cache = get_role_cache()
        user_role_str = await role_cache.get_role(user_id, self.users_repo.get_role)
        try:
            user_role = Role(user_role_str)
        except ValueError:
            user_role = Role.USER
        
        # Создаем контекст доступа
        context = AccessContext(
            user_id=user_id,
            user_role=user_role
        )
        
        # Добавляем контекст в данные
        data['access_context'] = context
        data['user_role'] = user_role
        
        # Проверяем права для админских команд
        if self._is_admin_command(event):
            if not self._has_admin_access(user_role):
                await self._send_access_denied(event, "Требуются права администратора")
                return
        
        # Проверяем права для команд управления ящиками
        if self._is_mailbox_command(event):
            await self._check_mailbox_access(event, context, data)
        
        return await handler(event, data)
    
    def _is_admin_command(self, event: TelegramObject) -> bool:
        """Проверить, является ли команда админской"""
        if isinstance(event, Message) and event.text:
            admin_commands = [
                '/add_admin', '/remove_admin', '/transfer_admin',
                '/create_mailbox', '/delete_mailbox', '/manage_mailbox',
                '/antispam', '/stats', '/backup', '/refresh'
            ]
            return any(event.text.startswith(cmd) for cmd in admin_commands)
        
        if isinstance(event, CallbackQuery) and event.data:
            admin_callbacks = [
                'add_admin', 'remove_admin', 'transfer_admin',
                'create_mailbox', 'delete_mailbox', 'manage_mailbox',
                'antispam', 'stats', 'backup', 'refresh'
            ]
            return any(event.data.startswith(cb) for cb in admin_callbacks)
        
        return False
    
    def _has_admin_access(self, user_role: Role) -> bool:
        """Проверить, есть ли у пользователя права администратора"""
        return user_role in [Role.ADMIN, Role.SUPERADMIN]
    
    def _is_mailbox_command(self, event: TelegramObject) -> bool:
        """Проверить, является ли команда связанной с ящиками"""
        if isinstance(event, Message) and event.text:
            mailbox_commands = ['/create_mailbox', '/delete_mailbox', '/manage_mailbox']
            return any(event.text.startswith(cmd) for cmd in mailbox_commands)
        
        if isinstance(event, CallbackQuery) and event.data:
            mailbox_callbacks = ['create_mailbox', 'delete_mailbox', 'manage_mailbox']
            return any(event.data.startswith(cb) for cb in mailbox_callbacks)
        
        return False
    
    async def _check_mailbox_access(self, event: TelegramObject, context: AccessContext, data: Dict[str, Any]):
        """Проверить доступ к ящику"""
        # Получаем ID ящика из данных
        mailbox_id = data.get('active_mailbox_id')
        
        if not mailbox_id:
            return
        
        # Проверяем, является ли пользователь создателем ящика
        is_creator = await self.mailboxes_repo.is_creator(mailbox_id, context.user_id)
        context.is_mailbox_creator = is_creator
        
        # Проверяем доступ
        if not PermissionManager.can_access_mailbox(context):
            await self._send_access_denied(event, "Нет доступа к указанному ящику")
            return
    
    async def _send_access_denied(self, event: TelegramObject, message: str):
        """Отправить сообщение об отказе в доступе"""
        try:
            if isinstance(event, Message):
                await event.answer(f"❌ {message}")
            elif isinstance(event, CallbackQuery):
                await event.answer(f"❌ {message}", show_alert=True)
        except Exception as e:
            logger.error(f"Error sending access denied message: {e}")

class RoleBasedMiddleware(BaseMiddleware):
    """
    Middleware для маршрутизации на основе ролей.
    
    Направляет пользователей к соответствующим обработчикам
    в зависимости от их роли.
    """
    
    def __init__(self, users_repo: UsersRepo):
        """
        Инициализация middleware.
        
        Args:
            users_repo: Репозиторий пользователей
        """
        self.users_repo = users_repo
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с маршрутизацией по ролям.
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные для обработчика
            
        Returns:
            Результат обработки события
        """
        # Получаем роль пользователя
        user_role = data.get('user_role', Role.USER)
        
        # Добавляем информацию о роли в данные
        data['is_admin'] = user_role in [Role.ADMIN, Role.SUPERADMIN]
        data['is_superadmin'] = user_role == Role.SUPERADMIN
        data['is_regular_user'] = user_role == Role.USER
        
        return await handler(event, data)
