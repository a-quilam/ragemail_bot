from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from app.fsm.admin_states import CreateBoxStates, AddAdminStates, RemoveAdminStates, TransferAdminStates, ButtonConfigStates, AntispamStates
from .menu_open import on_settings_button
from .create_box_step0 import cb_create_box, cb_select_channel, cb_cancel_box, cb_refresh_channel_list
# from .create_box_step1 import on_box_channel  # Удален, используется simple_channel_add
from .create_box_confirm import cb_box_confirm, cb_box_back
from .simple_channel_add import cb_add_channel_simple, on_channel_input
from .action_add_admin import on_add_admin_start, on_add_admin_input
from .action_remove_admin import on_remove_admin_start, on_remove_admin_input, on_remove_admin_confirm, on_remove_admin_cancel
from .action_transfer_admin import cb_transfer_admin_start, on_transfer_admin_input
from .back_to_start import on_back_button
from .cmd_statday import cmd_statday
from .cmd_stathour import cmd_stathour
from .cmd_postpin import cmd_postpin, on_postpin_text, _postpin_wait
from .cmd_refresh import cmd_refresh
from .cmd_stats import cmd_stats
from .cmd_backup import cmd_backup, cmd_restore
from .antispam_management import cmd_antispam, cmd_block_word, cmd_unblock_word, cmd_show_blocks, cb_antispam_mailbox_selection, cmd_cooldown_user, cmd_remove_cooldown, cmd_show_cooldowns
from .mailbox_management import (
    on_mailbox_management, cb_set_active_mailbox, cb_delete_mailbox, 
    cb_confirm_delete_mailbox, cb_cancel_delete_mailbox, cb_back_to_settings
)
from .button_config import (
    cb_button_config_start, cb_add_button, on_add_button_text, cb_edit_button, 
    cb_edit_button_item, cb_toggle_button, cb_delete_button, cb_confirm_delete_button,
    cb_reset_buttons, cb_confirm_reset_buttons, on_button_config_text
)
from .cmd_network_status import router as network_status_router, set_network_monitor

router = Router()

# Отладочный middleware удален - проблема решена

# Проверка ролей должна происходить в middleware, а не в фильтрах роутера

# Кнопка "✍️ Написать письмо" НЕ обрабатывается в admin_router,
# она передается дальше в write_router через порядок роутеров в main.py

# ===== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ =====
# Основные админские функции
router.message.register(on_settings_button, F.text == "⚙️ Настройки")  # Открытие настроек

# Кнопка "✍️ Написать письмо" не обрабатывается в admin_router,
# она передается дальше в write_router через порядок роутеров в main.py
router.message.register(cb_create_box, F.text == "➕ Создать почтовый ящик")  # Создание нового ящика
router.message.register(on_mailbox_management, F.text == "📦 Управление ящиками")  # Управление существующими ящиками
router.message.register(on_add_admin_start, F.text == "👤 Добавить админа")  # Добавление нового админа
router.message.register(on_remove_admin_start, F.text == "🗑️ Удалить админа")  # Удаление админа
router.message.register(on_back_button, F.text == "🔙 Назад")  # Возврат в главное меню
router.message.register(cmd_antispam, F.text == "🛡️ Антиспам")  # Управление антиспамом

# Дополнительные админские функции
router.message.register(cmd_postpin, F.text == "📌 Закрепить пост")  # Закрепление поста с deeplink
router.message.register(cmd_refresh, F.text == "🔄 Обновить")  # Обновление данных
router.message.register(cmd_stats, F.text == "📊 Статистика")  # Просмотр статистики

# ===== ОБРАБОТЧИКИ СОЗДАНИЯ ЯЩИКА =====
# Callback кнопки для выбора канала
router.callback_query.register(cb_select_channel, F.data.startswith("select_channel:"))  # Выбор канала из списка
router.callback_query.register(cb_refresh_channel_list, F.data == "refresh_channel_list")  # Обновление списка каналов
router.callback_query.register(cb_cancel_box, F.data == "box:cancel")  # Отмена создания ящика

# Обработка ввода канала (ссылка, ID или пересылка)
router.message.register(on_channel_input, StateFilter(CreateBoxStates.ADD_CHANNEL))  # Ввод информации о канале


# Add admin states
router.message.register(on_add_admin_input, StateFilter(AddAdminStates.ASK_USER))

# Remove admin states
router.message.register(on_remove_admin_input, StateFilter(RemoveAdminStates.ASK_USER))

# Remove admin confirmations
router.callback_query.register(on_remove_admin_confirm, F.data.startswith("confirm:remove_admin:"))
router.callback_query.register(on_remove_admin_cancel, F.data.startswith("cancel:remove_admin:"))

# Transfer admin states
router.message.register(on_transfer_admin_input, StateFilter(TransferAdminStates.ASK_USER))

# Button config states
router.message.register(on_add_button_text, StateFilter(ButtonConfigStates.ADD_BUTTON))
router.message.register(on_button_config_text, StateFilter(ButtonConfigStates.MAIN))

# Confirm callbacks
router.callback_query.register(cb_box_confirm, F.data == "box:confirm", StateFilter(CreateBoxStates.CONFIRM))
router.callback_query.register(cb_box_back, F.data == "box:back", StateFilter(CreateBoxStates.CONFIRM))

# Commands (только команды, кнопки уже зарегистрированы выше)
router.message.register(cmd_statday, Command("statday"))
router.message.register(cmd_stathour, Command("stathour"))
router.message.register(cmd_refresh, Command("refresh"))
router.message.register(cmd_backup, Command("backup"))
router.message.register(cmd_restore, Command("restore"))
router.message.register(cmd_antispam, Command("antispam"))
router.message.register(cmd_block_word, Command("block"), StateFilter(AntispamStates.MAILBOX_SELECTED))
router.message.register(cmd_unblock_word, Command("unblock"), StateFilter(AntispamStates.MAILBOX_SELECTED))
router.message.register(cmd_show_blocks, Command("blocks"))
router.message.register(cmd_cooldown_user, Command("cooldown"))
router.message.register(cmd_remove_cooldown, Command("remove_cooldown"))
router.message.register(cmd_show_cooldowns, Command("cooldowns"))

# Команда для принудительной очистки FSM состояний
@router.message(Command("clear_state"))
async def cmd_clear_state(m: types.Message, state: FSMContext):
    """Принудительная очистка FSM состояния"""
    from app.utils.fsm_utils import safe_clear_state
    from app.utils.fsm_timeout import untrack_fsm_state
    
    current_state = await state.get_state()
    await safe_clear_state(state, m.from_user.id)
    await untrack_fsm_state(m.from_user.id, state)
    
    if current_state:
        await m.answer(f"✅ FSM состояние очищено. Предыдущее состояние: {current_state}")
    else:
        await m.answer("ℹ️ FSM состояние уже было пустым.")

# Команда для принудительной очистки всех состояний пользователя
@router.message(Command("reset_all"))
async def cmd_reset_all(m: types.Message, state: FSMContext):
    """Принудительная очистка всех состояний и данных пользователя"""
    from app.utils.fsm_utils import safe_clear_state
    from app.utils.fsm_timeout import untrack_fsm_state
    
    current_state = await state.get_state()
    await safe_clear_state(state, m.from_user.id)
    await state.set_data({})
    await untrack_fsm_state(m.from_user.id, state)
    
    if current_state:
        await m.answer(f"✅ Все состояния и данные очищены. Предыдущее состояние: {current_state}")
    else:
        await m.answer("ℹ️ Все состояния и данные уже были пустыми.")

# Команда для просмотра текущего FSM состояния
@router.message(Command("state_info"))
async def cmd_state_info(m: types.Message, state: FSMContext):
    """Показать информацию о текущем FSM состоянии"""
    from app.utils.fsm_timeout import fsm_timeout_manager
    
    current_state = await state.get_state()
    state_data = await state.get_data()
    tracked_users = fsm_timeout_manager.get_tracked_users_count()
    
    info_text = f"📊 <b>Информация о FSM состоянии</b>\n\n"
    info_text += f"👤 <b>Пользователь:</b> {m.from_user.id}\n"
    info_text += f"🔄 <b>Текущее состояние:</b> {current_state or 'Нет'}\n"
    info_text += f"📦 <b>Данные состояния:</b> {len(state_data)} элементов\n"
    info_text += f"👥 <b>Отслеживаемых пользователей:</b> {tracked_users}\n"
    
    if state_data:
        info_text += f"\n📋 <b>Данные:</b>\n"
        for key, value in state_data.items():
            info_text += f"• {key}: {value}\n"
    
    await m.answer(info_text, parse_mode="HTML")

# Antispam callbacks
router.callback_query.register(cb_antispam_mailbox_selection, F.data.startswith("antispam_mailbox:"))

# Mailbox management callbacks
router.callback_query.register(cb_set_active_mailbox, F.data.startswith("set_active:"))
router.callback_query.register(cb_delete_mailbox, F.data.startswith("delete_mailbox:"))
router.callback_query.register(cb_confirm_delete_mailbox, F.data.startswith("confirm:delete_mailbox:"))
router.callback_query.register(cb_cancel_delete_mailbox, F.data.startswith("cancel:delete_mailbox:"))
router.callback_query.register(cb_transfer_admin_start, F.data.startswith("transfer_admin:"))
router.callback_query.register(cb_back_to_settings, F.data == "back_to_settings")

# Button configuration callbacks
router.callback_query.register(cb_button_config_start, F.data.startswith("button_config:"))
router.callback_query.register(cb_add_button, F.data.startswith("add_button:"))
router.callback_query.register(cb_edit_button, F.data.startswith("edit_button:"))
router.callback_query.register(cb_edit_button_item, F.data.startswith("edit_button_item:"))
router.callback_query.register(cb_toggle_button, F.data.startswith("toggle_button:"))
router.callback_query.register(cb_delete_button, F.data.startswith("delete_button:"))
router.callback_query.register(cb_confirm_delete_button, F.data.startswith("confirm_delete_button:"))
router.callback_query.register(cb_reset_buttons, F.data.startswith("reset_buttons:"))
router.callback_query.register(cb_confirm_reset_buttons, F.data.startswith("confirm_reset_buttons:"))

# Postpin follow-up text (guarded inside handler by internal state)
# Этот хендлер должен быть последним, чтобы не перехватывать другие сообщения
# Добавляем фильтр, чтобы хендлер не перехватывал все сообщения
from .cmd_postpin import _postpin_wait, on_postpin_text

# Список текстов кнопок, которые нужно игнорировать в on_postpin_text
button_texts_to_ignore = [
    "✍️ Написать письмо", "⚙️ Настройки", "📊 Статистика", "📌 Закрепить пост", 
    "🔄 Обновить", "🛡️ Антиспам", "👤 Добавить админа", "🗑️ Удалить админа", 
    "➕ Создать почтовый ящик", "📦 Управление ящиками", "🔙 Назад"
]

router.message.register(
    on_postpin_text, 
    lambda m: m.from_user.id in _postpin_wait and m.text not in button_texts_to_ignore
)

# Включаем роутер для сетевых команд
router.include_router(network_status_router)
