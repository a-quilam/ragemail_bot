from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def channel_kb(count1h: int, count12h: int, allow_contact: bool = True, custom_config: List[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру для поста в канале с возможностью кастомизации"""
    
    if custom_config:
        # Используем кастомную конфигурацию с сохранением структуры строк
        buttons = []
        
        for row_config in custom_config:
            if row_config.get("type") == "row":
                row_buttons = row_config.get("buttons", [])
                current_row = []
                
                for button_config in row_buttons:
                    if not button_config.get("enabled", True):
                        continue
                        
                    button_text = button_config["text"]
                    callback_data = button_config["callback_data"]
                    
                    # Для кнопок расширения добавляем счетчик
                    if button_config.get("type") == "extend":
                        if "1h" in callback_data:
                            button_text = f"{button_text} · {count1h}"
                        elif "12h" in callback_data:
                            button_text = f"{button_text} · {count12h}"
                        # Для других кнопок времени счетчик не добавляем
                    
                    # Для кнопки контакта проверяем разрешение
                    if button_config.get("type") == "contact" and not allow_contact:
                        continue
                        
                    current_row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))
                
                # Добавляем строку кнопок, если в ней есть кнопки
                if current_row:
                    buttons.append(current_row)
            
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        # Используем стандартную конфигурацию
        row1 = []
        
        if allow_contact:
            row1.extend([
                InlineKeyboardButton(text=f"➕1 ч · {count1h}", callback_data="ext:1h"),
                InlineKeyboardButton(text=f"➕12 ч · {count12h}", callback_data="ext:12h"),
                InlineKeyboardButton(text="💬 Поговорить", callback_data="contact"),
            ])
        else:
            row1.extend([
                InlineKeyboardButton(text=f"➕1 ч · {count1h}", callback_data="ext:1h"),
                InlineKeyboardButton(text=f"➕12 ч · {count12h}", callback_data="ext:12h"),
            ])
            
        return InlineKeyboardMarkup(inline_keyboard=[row1])
