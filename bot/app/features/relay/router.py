from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .cmd_end import cmd_end
from .reply_handler import handle_reply

router = Router()
router.message.register(cmd_end, Command("end"))
# Обрабатываем реплаи на сообщения анонимного чата
router.message.register(handle_reply, F.reply_to_message)
