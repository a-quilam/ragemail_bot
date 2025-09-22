from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from app.core.config import settings
from app.infra.repo.users_repo import UsersRepo
from app.utils.event_driven_role_cache import get_event_driven_role_cache

class RolesMiddleware(BaseMiddleware):
    def __init__(self, users: UsersRepo):
        super().__init__()
        self.users = users
        self.role_cache = get_event_driven_role_cache()

    async def __call__(self, handler: Callable[[Dict[str, Any], Any], Awaitable[Any]], event: Any, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        role = "user"
        if user:
            # Используем event-driven кэш для получения роли
            role = await self.role_cache.get_role(user.id, self.users.get_role)
        data["role"] = role
        return await handler(event, data)
