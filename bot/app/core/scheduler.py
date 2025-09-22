import asyncio
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot
from app.infra.repo.posts_repo import PostsRepo
from app.infra.repo.extensions_repo import ExtensionsRepo
from app.infra.repo.relays_repo import RelaysRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.repo.stats_repo import StatsRepo
from app.infra.repo.users_repo import UsersRepo
from app.services.post_service import PostService
from app.utils.backup import BackupManager
from app.utils.admin_logger import log_backup_created

class Scheduler:
    def __init__(self, bot: Bot, tz: ZoneInfo, posts: PostsRepo, exts: ExtensionsRepo, relays: RelaysRepo, mailboxes: MailboxesRepo, stats: StatsRepo, users: UsersRepo, db=None):
        self.bot = bot
        self.tz = tz
        self.posts = posts
        self.exts = exts
        self.relays = relays
        self.mailboxes = mailboxes
        self.stats = stats
        self.users = users
        self.db = db
        self._task: asyncio.Task | None = None
        self._last_backup = None

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def _run(self):
        while True:
            try:
                await self._tick()
            except Exception:
                pass
            await asyncio.sleep(5)

    async def _tick(self):
        now = int(time.time())
        
        # Оптимизация: batch операции для удаления постов
        expired_posts = await self.posts.list_expired(now)
        if expired_posts:
            # Удаляем сообщения из Telegram batch'ем
            for cid, mid in expired_posts:
                try:
                    await self.bot.delete_message(cid, mid)
                except Exception:
                    pass
            
            # Удаляем из БД batch'ем
            post_keys = [f"{cid}:{mid}" for cid, mid in expired_posts]
            await self._batch_delete_posts(expired_posts, post_keys)
        
        await self.relays.purge_expired(now)
        await self._process_delayed_queue()
        await self._maybe_weekly_stats()
        await self._maybe_daily_backup()

    async def _batch_delete_posts(self, expired_posts: list, post_keys: list):
        """Batch удаление постов и их расширений"""
        if not expired_posts:
            return
            
        # Удаляем посты batch'ем
        await self.posts.batch_delete(expired_posts)
        
        # Удаляем расширения batch'ем
        await self.exts.batch_delete_posts(post_keys)

    async def _process_delayed_queue(self):
        now = int(time.time())
        async with self.mailboxes.db.execute("SELECT id,user_id,mailbox_id,text,ttl_seconds,alias FROM delayed_queue WHERE run_at<=?", (now,)) as cur:
            rows = await cur.fetchall()
        
        if not rows:
            return
            
        # Оптимизация: получаем все нужные ящики одним запросом
        mailbox_ids = list(set(row[2] for row in rows))
        mailboxes = await self.mailboxes.batch_get(mailbox_ids)
        
        # Обрабатываем элементы очереди
        processed_ids = []
        for _id, user_id, mailbox_id, text, ttl, alias in rows:
            if mailbox_id not in mailboxes:
                processed_ids.append(_id)
                continue
                
            _, _, channel_id, _, _ = mailboxes[mailbox_id]
            svc = PostService(self.bot, self.tz, self.posts, self.exts)
            try:
                await svc.publish(channel_id, user_id, alias, text, ttl, mailbox_id)
                processed_ids.append(_id)
            except Exception:
                pass
        
        # Удаляем обработанные элементы batch'ем
        if processed_ids:
            placeholders = ','.join('?' * len(processed_ids))
            await self.mailboxes.db.execute(f"DELETE FROM delayed_queue WHERE id IN ({placeholders})", processed_ids)
            await self.mailboxes.db.commit()

    async def _maybe_weekly_stats(self):
        boxes = await self.mailboxes.list_all()
        now_dt = datetime.now(self.tz)
        dow = (now_dt.isoweekday())
        hhmm = now_dt.strftime("%H:%M")
        
        # Оптимизация: собираем все ящики, которым нужно отправить статистику
        boxes_to_process = []
        for bid, title, channel_id, stat_day, stat_time in boxes:
            if stat_day is not None and stat_day == dow and stat_time == hhmm:
                boxes_to_process.append((bid, title, channel_id))
        
        if not boxes_to_process:
            return
            
        # Получаем статистику один раз для всех ящиков
        since = (now_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        aggregated_stats = await self.stats.get_aggregated_stats(since, "day")
        
        if not aggregated_stats:
            return
            
        # Формируем сообщение один раз
        out = []
        for day, day_stats in aggregated_stats.items():
            items = [f"{key}:{total}" for key, total in day_stats.items()]
            out.append(f"{day} — " + ", ".join(items))
        
        message_text = "Мини-аналитика за неделю:\n" + "\n".join(out)
        
        # Отправляем всем ящикам
        for bid, title, channel_id in boxes_to_process:
            try:
                await self.bot.send_message(channel_id, message_text)
            except Exception:
                pass

    async def _maybe_daily_backup(self):
        """Создает ежедневный бэкап в 3:00"""
        if not self.db:
            return
            
        now = datetime.now(self.tz)
        current_date = now.strftime("%Y-%m-%d")
        
        # Проверяем, не создавали ли уже бэкап сегодня
        if self._last_backup == current_date:
            return
            
        # Создаем бэкап в 3:00
        if now.hour == 3 and now.minute < 5:  # В течение 5 минут после 3:00
            try:
                backup_manager = BackupManager(self.db)
                backup_file = await backup_manager.save_backup()
                if backup_file:
                    self._last_backup = current_date
                    # Логируем создание автоматического бэкапа
                    log_backup_created(0, backup_file)  # 0 = система
            except Exception as e:
                # Логируем ошибку, но не прерываем работу
                import logging
                logging.error(f"Failed to create daily backup: {e}")
