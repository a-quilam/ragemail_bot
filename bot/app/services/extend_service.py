import time
from app.infra.repo.extensions_repo import ExtensionsRepo, KIND_TO_SECONDS
from app.infra.repo.posts_repo import PostsRepo

class ExtendService:
    def __init__(self, exts: ExtensionsRepo, posts: PostsRepo):
        self.exts = exts
        self.posts = posts

    async def toggle_with_rule(self, chat_id: int, message_id: int, user_id: int, kind: str) -> tuple[bool, str]:
        post = await self.posts.get(chat_id, message_id)
        if not post:
            return False, "Пост уже сгорел."
        _, _, _, _, _, _, delete_at = post
        now = int(time.time())
        remaining = max(0, delete_at - now)
        became_active = await self.exts.toggle(f"{chat_id}:{message_id}", user_id, kind)
        if not became_active:
            interval = KIND_TO_SECONDS.get(kind, 0)
            if remaining < interval:
                await self.exts.toggle(f"{chat_id}:{message_id}", user_id, kind)
                return False, "Снять вклад нельзя: осталось меньше продолжительности этого продления."
        return True, "Ок"
