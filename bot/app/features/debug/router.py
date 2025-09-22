from aiogram import Router, types
from aiogram.filters import StateFilter
from app.fsm.admin_states import CreateBoxStates
import logging

router = Router()

# Отладочный обработчик удален - он конфликтовал с основными обработчиками
