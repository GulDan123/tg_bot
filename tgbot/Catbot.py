import os
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = '7993126919:AAHGV2Px8RinjQ2EM44__cCbq7ofCNt_KgY'

if os.name == 'nt':  # Windows
    photos_dir = r'd:\tgbot'
else:  # Linux
    photos_dir = '/home/user/photos'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Отправь /photo, чтобы получить фотографию.')

async def send_random_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем все файлы в папке
    files = [f for f in os.listdir(photos_dir) if os.path.isfile(os.path.join(photos_dir, f))]
    if not files:
        await update.message.reply_text("Нет доступных фотографий.")
        return
    selected_file = random.choice(files)
    photo_path = os.path.join(photos_dir, selected_file)
    with open(photo_path, 'rb') as photo_file:
        await update.message.reply_photo(photo=photo_file, caption='Вот пример красивой картинки для рабочего стола!')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('photo', send_random_photo))
    print("Бот запущен")
    app.run_polling()
