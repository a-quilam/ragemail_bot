from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .cmd_end import cmd_end
from .pipe_private import pipe

router = Router()
router.message.register(cmd_end, Command("end"))
# НЕ обрабатываем кнопки - они должны обрабатываться специфичными обработчиками
router.message.register(pipe, ~F.text.startswith("✍️") & ~F.text.startswith("⚙️") & ~F.text.startswith("📊") & ~F.text.startswith("📌") & ~F.text.startswith("🔄") & ~F.text.startswith("🛡️") & ~F.text.startswith("👤") & ~F.text.startswith("🗑️") & ~F.text.startswith("➕") & ~F.text.startswith("📦") & ~F.text.startswith("🔙"))
