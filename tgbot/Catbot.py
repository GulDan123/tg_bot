import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Ваш токен бота
TOKEN = '7993126919:AAHGV2Px8RinjQ2EM44__cCbq7ofCNt_KgY'

# Список картинок, которые бот может отправлять
photo_paths = [
    r'd:\tgbot\photo.jpg',
    r'd:\tgbot\photo1.jpg',
    r'd:\tgbot\photo2.jpg',
    r'd:\tgbot\photo3.jpg',
    r'd:\tgbot\photo4.jpg',
    r'd:\tgbot\photo5.jpg',
    r'd:\tgbot\photo6.jpg',
    r'd:\tgbot\photo7.jpg',
    r'd:\tgbot\photo8.jpg',
    r'd:\tgbot\photo9.jpg'
]


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я твой первый Telegram-бот. Отправь /photo, чтобы получить фотографию.')

# Обработчик команды /photo
async def send_random_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_photo = random.choice(photo_paths)  # используем photo_paths
    with open(selected_photo, 'rb') as photo_file:
        await update.message.reply_photo(photo=photo_file, caption='Вот пример красивой картинки для рабочего стола!')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('photo', send_random_photo))
    print("Бот запущен")
    app.run_polling()