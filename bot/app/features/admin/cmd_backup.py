from aiogram import types
from aiogram.fsm.context import FSMContext
from app.infra.db import connect
from app.utils.backup import BackupManager
from app.core.config import settings
import os

async def cmd_backup(m: types.Message, state: FSMContext):
    """Команда для создания бэкапа данных"""
    # Проверяем, что пользователь - суперадмин
    if not settings.SUPERADMIN_ID or m.from_user.id != settings.SUPERADMIN_ID:
        await m.answer("❌ Доступ запрещен. Только суперадмин может создавать бэкапы.")
        return

    try:
        # Создаем бэкап
        db = await connect("queue.db")
        backup_manager = BackupManager(db)
        
        filename = await backup_manager.save_backup()
        
        await m.answer(
            f"✅ <b>Бэкап создан успешно!</b>\n\n"
            f"📁 Файл: <code>{filename}</code>\n"
            f"📊 Сохранены данные:\n"
            f"• 👥 Пользователи и роли\n"
            f"• 📦 Почтовые ящики\n"
            f"• 🏷️ Алиасы\n"
            f"• 🔗 Привязки пользователей\n\n"
            f"💡 <i>Используйте этот файл для восстановления данных при обновлении бота.</i>",
            parse_mode="HTML"
        )
        
        await db.close()
        
    except Exception as e:
        await m.answer(f"❌ Ошибка создания бэкапа: {str(e)}")

async def cmd_restore(m: types.Message, state: FSMContext):
    """Команда для восстановления данных из последнего бэкапа"""
    # Проверяем, что пользователь - суперадмин
    if not settings.SUPERADMIN_ID or m.from_user.id != settings.SUPERADMIN_ID:
        await m.answer("❌ Доступ запрещен. Только суперадмин может восстанавливать бэкапы.")
        return

    # Ищем последний бэкап
    if not os.path.exists("backups"):
        await m.answer("❌ Папка с бэкапами не найдена.")
        return
    
    backup_files = [f for f in os.listdir("backups") if f.endswith(".json")]
    if not backup_files:
        await m.answer("❌ Бэкапы не найдены.")
        return
    
    # Берем самый новый файл
    backup_files.sort(reverse=True)
    filename = backup_files[0]
    backup_path = f"backups/{filename}"
    
    if not os.path.exists(backup_path):
        await m.answer(f"❌ Файл бэкапа не найден: {backup_path}")
        return

    try:
        # Восстанавливаем данные
        db = await connect("queue.db")
        backup_manager = BackupManager(db)
        
        success = await backup_manager.load_backup(backup_path)
        
        if success:
            await m.answer(
                f"✅ <b>Данные восстановлены успешно!</b>\n\n"
                f"📁 Из файла: <code>{filename}</code>\n"
                f"🔄 Восстановлены:\n"
                f"• 👥 Пользователи и роли\n"
                f"• 📦 Почтовые ящики\n"
                f"• 🏷️ Алиасы\n"
                f"• 🔗 Привязки пользователей\n\n"
                f"⚠️ <i>Бот перезапущен с новыми данными.</i>",
                parse_mode="HTML"
            )
        else:
            await m.answer("❌ Ошибка восстановления данных. Проверьте файл бэкапа.")
        
        await db.close()
        
    except Exception as e:
        await m.answer(f"❌ Ошибка восстановления: {str(e)}")
