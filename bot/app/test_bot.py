import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.core.config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    logging.info(f"START received from {message.from_user.id}")
    await message.answer("Тестовый бот работает!")

@dp.message()
async def echo_handler(message: Message):
    logging.info(f"Message received: {message.text} from {message.from_user.id}")
    await message.answer(f"Получил: {message.text}")

async def main():
    logging.info("Starting test bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
