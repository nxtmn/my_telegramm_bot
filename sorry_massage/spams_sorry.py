# "Я всё проправиль! Пожалуйста - проверь свои напоминалочки, вдруг я что-то забыл 🐱"
from telegram import Bot
import asyncio

TOKEN = "MY_TOKEN_TELEGRAM" #Нужен реальный токен
USER_ID = 0000000000000000 #Указание ид вручную (будет доработка)
IMAGE_URL = "https://disk.yandex.ru/i/sUQJiDSpgfTyNg"

async def send_test_message():
    bot = Bot(token=TOKEN)
    message = "Я всё проправиль! Пожалуйста - проверь свои напоминалочки, вдруг я что-то забыл 🐱"
    await bot.send_photo(chat_id=USER_ID, photo=IMAGE_URL, caption=message)
    print("✅ Отправлено")

if __name__ == "__main__":
    asyncio.run(send_test_message())
