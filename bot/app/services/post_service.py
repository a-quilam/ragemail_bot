import time
from typing import Tuple, Optional
from zoneinfo import ZoneInfo
from aiogram import Bot
from app.core.timefmt import fmt_expiry
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.extensions_repo import ExtensionsRepo
from app.infra.repo.stats_repo import StatsRepo
from app.infra.repo.button_configs_repo import ButtonConfigsRepo
from app.services.stats_service import StatsService
from app.keyboards.channel_post import channel_kb

class PostService:
    def __init__(self, bot: Bot, tz: ZoneInfo, posts: PostsRepo, exts: ExtensionsRepo):
        self.bot = bot
        self.tz = tz
        self.posts = posts
        self.exts = exts

    async def publish(self, channel_id: int, author_id: int, alias: str, text: str, ttl_seconds: int, mailbox_id: Optional[int] = None) -> Tuple[int,int,int]:
        now = int(time.time())
        # Округляем до 5 минут в меньшую сторону
        rounded_time = (now // 300) * 300  # 300 секунд = 5 минут
        base_delete_at = rounded_time + ttl_seconds
        delete_at = base_delete_at
        base_text = f"{text}\n\n<b>{alias}</b>\n{fmt_expiry(delete_at, self.tz)}"
        footer = ""
        sent = await self.bot.send_message(channel_id, base_text + footer, disable_web_page_preview=True, parse_mode="HTML")
        post_key = f"{sent.chat.id}:{sent.message_id}"
        counts = await self.exts.counts(post_key)
        
        # Получаем кастомную конфигурацию кнопок для ящика
        custom_config = None
        if mailbox_id:
            try:
                button_configs_repo = ButtonConfigsRepo(self.posts.db)
                custom_config = await button_configs_repo.get_config(mailbox_id)
            except Exception:
                pass
        
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=sent.chat.id,
                message_id=sent.message_id,
                reply_markup=channel_kb(counts.get("1h",0), counts.get("12h",0), allow_contact=True, custom_config=custom_config)
            )
        except Exception:
            pass
        await self.posts.add(sent.chat.id, sent.message_id, author_id, alias, base_text, base_delete_at, delete_at)
        try:
            await StatsService(StatsRepo(self.posts.db), self.tz).inc("posted")
        except Exception:
            pass
        return sent.chat.id, sent.message_id, delete_at

    async def refresh_footer(self, chat_id: int, message_id: int) -> None:
        rec = await self.posts.get(chat_id, message_id)
        if not rec:
            return
        _, _, _, alias, base_text, _, delete_at = rec
        # Извлекаем текст из base_text (убираем псевдоним и время сгорания)
        lines = base_text.split('\n')
        if len(lines) >= 3:
            # Убираем последние две строки (псевдоним и время сгорания)
            text = '\n'.join(lines[:-2])
            new_text = f"{text}\n\n<b>{alias}</b>\n{fmt_expiry(delete_at, self.tz)}"
        else:
            new_text = base_text
        try:
            await self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode="HTML")
        except Exception:
            pass

    async def apply_extensions_and_update(self, chat_id: int, message_id: int, mailbox_id: Optional[int] = None) -> None:
        rec = await self.posts.get(chat_id, message_id)
        if not rec:
            return
        _, _, _, _, _, base_delete_at, _ = rec
        post_key = f"{chat_id}:{message_id}"
        extra = await self.exts.total_extension_seconds(post_key)
        new_delete_at = base_delete_at + extra
        await self.posts.set_delete_at(chat_id, message_id, new_delete_at)
        await self.refresh_footer(chat_id, message_id)
        counts = await self.exts.counts(post_key)
        
        # Получаем кастомную конфигурацию кнопок для ящика
        custom_config = None
        if mailbox_id:
            try:
                button_configs_repo = ButtonConfigsRepo(self.posts.db)
                custom_config = await button_configs_repo.get_config(mailbox_id)
            except Exception:
                pass
        
        try:
            await self.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                reply_markup=channel_kb(counts.get("1h",0), counts.get("12h",0), allow_contact=True, custom_config=custom_config))
        except Exception:
            pass
