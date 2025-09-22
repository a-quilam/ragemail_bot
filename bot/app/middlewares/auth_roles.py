from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from app.core.config import settings
from app.infra.repo.users_repo import UsersRepo

class RolesMiddleware(BaseMiddleware):
    def __init__(self, users: UsersRepo):
        super().__init__()
        self.users = users

    async def __call__(self, handler: Callable[[Dict[str, Any], Any], Awaitable[Any]], event: Any, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        role = "user"
        if user:
            if settings.SUPERADMIN_ID and user.id == settings.SUPERADMIN_ID:
                role = "superadmin"
            else:
                role = await self.users.get_role(user.id)
        data["role"] = role
        return await handler(event, data)
