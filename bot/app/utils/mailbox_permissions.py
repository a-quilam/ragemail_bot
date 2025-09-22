from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.users_repo import UsersRepo
from app.core.config import settings

async def can_access_mailbox(db, user_id: int, mailbox_id: int) -> bool:
    """
    Проверить, может ли пользователь получить доступ к ящику.
    Доступ имеют:
    1. Суперадмин (SUPERADMIN_ID)
    2. Создатель ящика
    3. Админы и суперадмины (если ящик не имеет создателя - для обратной совместимости)
    """
    # Суперадмин имеет доступ ко всем ящикам
    if settings.SUPERADMIN_ID and user_id == settings.SUPERADMIN_ID:
        return True
    
    # Получаем информацию о ящике
    mailboxes_repo = MailboxesRepo(db)
    box = await mailboxes_repo.get(mailbox_id)
    if not box:
        return False
    
    _, _, _, _, _, creator_id = box
    
    # Если ящик имеет создателя, только он имеет доступ
    if creator_id is not None:
        return creator_id == user_id
    
    # Для ящиков без создателя (обратная совместимость) - проверяем роль
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(user_id)
    return role in ("admin", "superadmin")

async def can_manage_mailbox(db, user_id: int, mailbox_id: int) -> bool:
    """
    Проверить, может ли пользователь управлять ящиком (статистика, настройки и т.д.).
    Права управления имеют:
    1. Суперадмин (SUPERADMIN_ID)
    2. Создатель ящика
    """
    # Суперадмин имеет доступ ко всем ящикам
    if settings.SUPERADMIN_ID and user_id == settings.SUPERADMIN_ID:
        return True
    
    # Получаем информацию о ящике
    mailboxes_repo = MailboxesRepo(db)
    box = await mailboxes_repo.get(mailbox_id)
    if not box:
        return False
    
    _, _, _, _, _, creator_id = box
    
    # Если ящик имеет создателя, только он имеет права управления
    if creator_id is not None:
        return creator_id == user_id
    
    # Для ящиков без создателя (обратная совместимость) - проверяем роль
    users_repo = UsersRepo(db)
    role = await users_repo.get_role(user_id)
    return role in ("admin", "superadmin")
