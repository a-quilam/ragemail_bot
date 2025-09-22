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
            except Exception as e:
                logging.error(f"Error in scheduler tick: {e}")
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
        try:
            async with self.mailboxes.db.execute("SELECT id,user_id,mailbox_id,text,ttl_seconds,alias,cancel_message_id FROM delayed_queue WHERE run_at<=?", (now,)) as cur:
                rows = await cur.fetchall()
            
            if not rows:
                return
                
            # Оптимизация: получаем все нужные ящики одним запросом
            mailbox_ids = list(set(row[2] for row in rows))
            mailboxes = await self.mailboxes.batch_get(mailbox_ids)
            
            # Обрабатываем элементы очереди
            processed_ids = []
            failed_ids = []
            
            for _id, user_id, mailbox_id, text, ttl, alias, cancel_message_id in rows:
                try:
                    if mailbox_id not in mailboxes:
                        processed_ids.append(_id)  # Удаляем из очереди
                        continue
                        
                    _, _, channel_id, _, _, _ = mailboxes[mailbox_id]
                    svc = PostService(self.bot, self.tz, self.posts, self.exts)
                    
                    await svc.publish(channel_id, user_id, alias, text, ttl, mailbox_id)
                    processed_ids.append(_id)
                    
                    # Уведомляем пользователя об успешной отправке
                    try:
                        # Формируем ссылку на канал
                        channel_link = f"https://t.me/{channel_id.replace('@', '')}" if str(channel_id).startswith('@') else f"https://t.me/c/{str(channel_id)[4:]}" if str(channel_id).startswith('-100') else f"https://t.me/{channel_id}"
                        
                        await self.bot.send_message(
                            user_id, 
                            f"✅ <b>Отложенное сообщение отправлено!</b>\n\n"
                            f"📺 <b>Канал:</b> <a href='{channel_link}'>Перейти к посту</a>",
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                        
                        # Удаляем сообщение с кнопкой отмены, если оно существует
                        if cancel_message_id:
                            try:
                                await self.bot.delete_message(user_id, cancel_message_id)
                            except Exception:
                                pass  # Игнорируем ошибки удаления сообщения
                    except Exception:
                        pass  # Игнорируем ошибки уведомлений
                    
                except Exception as e:
                    logging.error(f"Failed to send delayed message {_id}: {e}")
                    failed_ids.append(_id)
                    
                    # Уведомляем пользователя об ошибке
                    try:
                        await self.bot.send_message(
                            user_id, 
                            f"❌ Не удалось отправить отложенное сообщение"
                        )
                    except Exception:
                        pass  # Игнорируем ошибки уведомлений
            
            # Удаляем успешно обработанные элементы
            if processed_ids:
                placeholders = ','.join('?' * len(processed_ids))
                await self.mailboxes.db.execute(f"DELETE FROM delayed_queue WHERE id IN ({placeholders})", processed_ids)
            
            # Для неудачных сообщений увеличиваем run_at на 5 минут для retry
            if failed_ids:
                retry_time = now + 300  # 5 минут
                placeholders = ','.join('?' * len(failed_ids))
                await self.mailboxes.db.execute(
                    f"UPDATE delayed_queue SET run_at = ? WHERE id IN ({placeholders})", 
                    [retry_time] + failed_ids
                )
            
            await self.mailboxes.db.commit()
            
        except Exception as e:
            logging.error(f"Error in delayed queue processing: {e}")

    async def _maybe_weekly_stats(self):
        boxes = await self.mailboxes.list_all()
        now_dt = datetime.now(self.tz)
        dow = (now_dt.isoweekday())
        hhmm = now_dt.strftime("%H:%M")
        
        # Оптимизация: собираем все ящики, которым нужно отправить статистику
        boxes_to_process = []
        for bid, title, channel_id, stat_day, stat_time, creator_id in boxes:
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
