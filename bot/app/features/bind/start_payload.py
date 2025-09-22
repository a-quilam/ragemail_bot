from aiogram import types
from aiogram.filters import CommandStart
import logging
from app.infra.repo.users_repo import UsersRepo
from app.infra.repo.mailboxes_repo import MailboxesRepo
from app.infra.tg_api import user_is_member
from app.core.config import settings
from app.keyboards.write_flow import start_kb_admin, start_kb_user

async def cmd_start_payload(m: types.Message, db, bot):
    """Обработка deeplink с оптимизированными запросами к БД"""
    
    try:
        # Фильтр уже проверил, что есть параметры
        logging.info(f"START with payload processing: '{m.text}'")
        
        payload = m.text.split()[1]
        if not payload.isdigit():
            await m.answer("❌ Неверный формат ссылки.")
            return True
        
        try:
            mailbox_id = int(payload)
            if mailbox_id <= 0:
                await m.answer("❌ Неверный ID ящика.")
                return True
        except (ValueError, OverflowError):
            await m.answer("❌ Неверный формат ID ящика.")
            return True
        
        # Получаем данные ящика
        box = await MailboxesRepo(db).get(mailbox_id)
        if not box or len(box) < 6:
            await m.answer("❌ Ящик не найден.")
            return True
        
        _, _, channel_id, _, _, creator_id = box
        
        if not channel_id:
            await m.answer("❌ Ошибка: канал ящика не настроен.")
            return True
        
        # Проверяем подписку на канал
        if not await user_is_member(bot, channel_id, m.from_user.id):
            await m.answer(
                "❌ <b>Доступ ограничен</b>\n\n"
                "Вы не подписаны на канал этого ящика.\n"
                "Подпишитесь на канал и нажмите ссылку ещё раз.",
                parse_mode="HTML"
            )
            return True
        
        # Оптимизированная работа с пользователем - один запрос вместо двух
        users_repo = UsersRepo(db)
        user_data = await users_repo.get(m.from_user.id)
        
        if not user_data:
            # Создаем пользователя и сразу устанавливаем активный ящик
            await users_repo.upsert(m.from_user.id, username=m.from_user.username)
            await users_repo.set_active_mailbox(m.from_user.id, mailbox_id)
        else:
            # Обновляем username и активный ящик
            await users_repo.update_username(m.from_user.id, m.from_user.username)
            await users_repo.set_active_mailbox(m.from_user.id, mailbox_id)
        
        # Оптимизированная проверка прав - без дополнительных запросов к БД
        can_manage = (
            (settings.SUPERADMIN_ID and m.from_user.id == settings.SUPERADMIN_ID) or
            (creator_id and creator_id == m.from_user.id)
        )
        
        # Если не создатель и не суперадмин, проверяем роль (редкий случай)
        if not can_manage and user_data:
            role = user_data[1] if len(user_data) > 1 else "user"
            can_manage = role in ("admin", "superadmin")
        
        # Отправляем интерфейс
        if can_manage:
            await m.answer(
                "✅ <b>Привязка выполнена!</b>\n\n"
                "Теперь вы пишете в этот ящик по умолчанию.\n\n"
                "Доступные действия:\n"
                "✍️ <b>Написать письмо</b> — создать анонимное сообщение\n"
                "⚙️ <b>Настройки</b> — управление ящиками и пользователями\n"
                "📊 <b>Статистика</b> — просмотр статистики\n"
                "📌 <b>Закрепить пост</b> — создать deeplink-пост\n"
                "🔄 <b>Обновить</b> — синхронизация с каналом",
                reply_markup=start_kb_admin()
            )
        else:
            await m.answer(
                "✅ <b>Привязка выполнена!</b>\n\n"
                "Теперь вы пишете в этот ящик по умолчанию.\n\n"
                "Просто напишите ваше анонимное сообщение, и я отправлю его в канал.",
                reply_markup=start_kb_user()
            )
        
        return True
    
    except Exception as e:
        logging.error(f"Error processing deeplink for user {m.from_user.id}: {e}", exc_info=True)
        await m.answer("❌ Произошла ошибка при обработке ссылки. Попробуйте позже.")
        return True
