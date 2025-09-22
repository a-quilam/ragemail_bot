from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from .start_payload import cmd_start_payload

router = Router()
router.message.register(cmd_start_payload, CommandStart())
