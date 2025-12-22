import asyncio
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher()

bot_list = []
task_id_counter = 1
reminder_tasks: Dict[int, asyncio.Task] = {}  


START_MSG = "Привет, я бот помошник для создания задач"
TASK_LIST_EMPTY_MSG = "Список задач пуст."
ENTER_TASK_NUMBER_TO_DELETE_MSG = "Введите номер задачи для удаления"
ENTER_TASK_NUMBER_TO_EDIT_MSG = "Введите номер задачи для редактирования:"
TASK_DELETED_MSG = "Задача удалена."
TASK_UPDATED_MSG = "Задача обновлена."
INVALID_TASK_NUMBER_MSG = "Неверный номер. Попробуйте снова."
TASK_ADDED_MSG = "Задача добавлена"
CHOICE_ACTION_MSG = "Выберите действие"
ENTER_TASK_MSG = "Введите задачу в формате: <текст задачи> | <время HH:MM>\n\nПримеры:\nПозвонить маме | 18:00\nСделать уроки | 20:30\nКупить хлеб (без времени)"
INVALID_FORMAT_MSG = "Неверный формат! Введите: <текст задачи> | <время HH:MM>"
INVALID_TIME_MSG = "Неверное время! Используйте формат HH:MM (например, 14:30)"
REMINDER_MSG = "⏰ НАПОМИНАНИЕ: Через 1 час у вас задача: \"{}\""
REMINDER_SET_MSG = "✅ Напоминание установлено за 1 час до задачи"
NO_TIME_FOR_REMINDER_MSG = "⚠️ Напоминание не установлено: у задачи нет времени"

class UserState(StatesGroup):
    delete_task = State()
    edit_select = State()
    edit_input = State()
    add_state = State()

STATE_DELETE_TASK = UserState.delete_task
STATE_EDIT_SELECT = UserState.edit_select
STATE_EDIT_INPUT = UserState.edit_input
STATE_ADD = UserState.add_state

def create_main_keyboard():
    """Создает основную клавиатуру"""
    kb = [
        [types.KeyboardButton(text="Добавить задачу")],
        [types.KeyboardButton(text="Удалить задачу")],
        [types.KeyboardButton(text="Просмотр всех задач")],
        [types.KeyboardButton(text="Редактировать задачу")],
        [types.KeyboardButton(text="Мои напоминания")],
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder=CHOICE_ACTION_MSG
    )

def is_valid_time(time_str):
    """Проверяет, валидно ли время в формате HH:MM"""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def parse_task_input(text):
    """Парсит ввод пользователя на текст задачи и время"""
    text = text.strip()
    
    if '|' in text:
        parts = text.split('|', 1)
        task_text = parts[0].strip()
        time_part = parts[1].strip() if len(parts) > 1 else ""
        
        if time_part and is_valid_time(time_part):
            return task_text, time_part
        elif time_part: 
            return task_text, "invalid"
        else:  
            return task_text, None
    else:
        
        return text, None

def calculate_reminder_time(task_time_str: str) -> datetime:
    """Рассчитывает время напоминания (за 1 час до задачи)"""
    now = datetime.now()
    
    
    task_time = datetime.strptime(task_time_str, "%H:%M").replace(
        year=now.year,
        month=now.month,
        day=now.day
    )
    
    
    if task_time < now:
        task_time += timedelta(days=1)
    
    
    reminder_time = task_time - timedelta(hours=1)
    
    
    if reminder_time < now:
        return None
    
    return reminder_time

async def schedule_reminder(task_id: int, user_id: int, task_text: str, reminder_time: datetime):
    """Планирует напоминание на указанное время"""
    
    async def send_reminder():
        """Отправляет напоминание пользователю"""
        try:
            await bot.send_message(
                user_id,
                REMINDER_MSG.format(task_text)
            )
            logger.info(f"Напоминание отправлено пользователю {user_id} для задачи: {task_text}")
            
            
            if task_id in reminder_tasks:
                del reminder_tasks[task_id]
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания: {e}")
    
   
    delay = (reminder_time - datetime.now()).total_seconds()
    
    if delay > 0:
        
        task = asyncio.create_task(schedule_reminder_task(delay, send_reminder))
        reminder_tasks[task_id] = task
        logger.info(f"Напоминание запланировано на {reminder_time} (через {delay:.0f} сек)")
        return True
    else:
        return False

async def schedule_reminder_task(delay: float, callback):
    """Создает задачу с задержкой"""
    await asyncio.sleep(delay)
    await callback()

def cancel_reminder(task_id: int):
    """Отменяет запланированное напоминание"""
    if task_id in reminder_tasks:
        reminder_tasks[task_id].cancel()
        del reminder_tasks[task_id]
        logger.info(f"Напоминание для задачи {task_id} отменено")
        return True
    return False

def format_task_display(task, index):
    """Форматирует задачу для отображения"""
    task_display = f"{index}. {task['task']}"
    if task.get('time'):
        task_display += f" ⏰ {task['time']}"
        
        if task['id'] in reminder_tasks:
            task_display += " 🔔 (напоминание установлено)"
    return task_display

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = create_main_keyboard()
    await message.answer(START_MSG, reply_markup=keyboard)

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Команда для возврата в главное меню"""
    await state.clear()
    keyboard = create_main_keyboard()
    await message.answer("Главное меню:", reply_markup=keyboard)

@dp.message(F.text == "Добавить задачу")
async def add_a_task(message: types.Message, state: FSMContext):
    await message.reply(
        ENTER_TASK_MSG,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(STATE_ADD)

@dp.message(STATE_ADD)
async def process_task_input(message: types.Message, state: FSMContext):
    global bot_list, task_id_counter
    
    
    task_text, task_time = parse_task_input(message.text)
    
    
    if not task_text:
        await message.reply("Текст задачи не может быть пустым!")
        return
    
    if task_time == "invalid":
        await message.reply(INVALID_TIME_MSG)
        return
    
   
    task_id = task_id_counter
    task_data = {
        'id': task_id, 
        'task': task_text,
        'time': task_time,  
        'user_id': message.from_user.id
    }
    bot_list.append(task_data)
    task_id_counter += 1
    
    
    reply_text = ""
    if task_time:
        reply_text = f"{TASK_ADDED_MSG}: '{task_text}' на {task_time}"
        
       
        reminder_time = calculate_reminder_time(task_time)
        if reminder_time:
            scheduled = await schedule_reminder(
                task_id, 
                message.from_user.id, 
                task_text, 
                reminder_time
            )
            if scheduled:
                reply_text += f"\n{REMINDER_SET_MSG} ({reminder_time.strftime('%H:%M')})"
            else:
                reply_text += "\n⚠️ Напоминание не установлено (время слишком близко)"
        else:
            reply_text += f"\n{NO_TIME_FOR_REMINDER_MSG}"
    else:
        reply_text = f"{TASK_ADDED_MSG}: '{task_text}'"
    
  
    keyboard = create_main_keyboard()
    await message.reply(reply_text, reply_markup=keyboard)
    
    await state.clear()

@dp.message(F.text == "Просмотр всех задач")
async def show_tasks(message: types.Message):
    if not bot_list:
        await message.answer(TASK_LIST_EMPTY_MSG)
        return
    
    user_tasks = [task for task in bot_list if task.get('user_id') == message.from_user.id]
    
    if not user_tasks:
        await message.answer("У вас пока нет задач.")
        return
    
    tasks_text = ""
    for index, task in enumerate(user_tasks, start=1):
        tasks_text += format_task_display(task, index) + "\n"
    
    await message.answer(f"Ваш список:\n{tasks_text}")

@dp.message(F.text == "Мои напоминания")
async def show_reminders(message: types.Message):
    """Показывает все активные напоминания пользователя"""
    user_task_ids = [task['id'] for task in bot_list if task.get('user_id') == message.from_user.id]
    user_reminders = {task_id: task for task_id, task in reminder_tasks.items() 
                     if task_id in user_task_ids}
    
    if not user_reminders:
        await message.answer("У вас нет активных напоминаний.")
        return
    
    
    tasks_with_reminders = []
    for task in bot_list:
        if task['id'] in user_reminders and task.get('user_id') == message.from_user.id:
            tasks_with_reminders.append(task)
    
    if not tasks_with_reminders:
        await message.answer("У вас нет активных напоминаний.")
        return
    
    tasks_text = "🔔 Ваши активные напоминания:\n\n"
    for index, task in enumerate(tasks_with_reminders, start=1):
        tasks_text += f"{index}. {task['task']} ⏰ {task.get('time', 'без времени')}\n"
    
    await message.answer(tasks_text)

@dp.message(F.text == "Удалить задачу")
async def show_tasks_for_deletion(message: types.Message, state: FSMContext):
    
    user_tasks = [task for task in bot_list if task.get('user_id') == message.from_user.id]
    
    if not user_tasks:
        await message.answer("У вас нет задач для удаления.")
        return
    
    tasks_text = ""
    for index, task in enumerate(user_tasks, start=1):
        tasks_text += format_task_display(task, index) + "\n"
    
    await message.answer(
        f"{tasks_text}\n{ENTER_TASK_NUMBER_TO_DELETE_MSG}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(STATE_DELETE_TASK)

@dp.message(STATE_DELETE_TASK)
async def delete_task(message: types.Message, state: FSMContext):
    try:
        
        user_tasks = [task for task in bot_list if task.get('user_id') == message.from_user.id]
        
        task_number = int(message.text) - 1
        if 0 <= task_number < len(user_tasks):
            
            task_to_delete = user_tasks[task_number]
            
            
            cancel_reminder(task_to_delete['id'])
            
            bot_list[:] = [task for task in bot_list if task['id'] != task_to_delete['id']]
            
            
            keyboard = create_main_keyboard()
            await message.answer(TASK_DELETED_MSG, reply_markup=keyboard)
        else:
            await message.reply("Неверный номер задачи.")
    except ValueError:
        await message.reply("Пожалуйста, введите корректный номер.")
    
    await state.clear()

@dp.message(F.text == "Редактировать задачу")
async def edit_task_prompt(message: types.Message, state: FSMContext):
    
    user_tasks = [task for task in bot_list if task.get('user_id') == message.from_user.id]
    
    if not user_tasks:
        await message.answer("У вас нет задач для редактирования.")
        return
    
    tasks_text = ""
    for index, task in enumerate(user_tasks, start=1):
        tasks_text += format_task_display(task, index) + "\n"
    
    await message.answer(
        f"{tasks_text}\n{ENTER_TASK_NUMBER_TO_EDIT_MSG}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(STATE_EDIT_SELECT)

@dp.message(STATE_EDIT_SELECT)
async def edit_task_select(message: types.Message, state: FSMContext):
    
    user_tasks = [task for task in bot_list if task.get('user_id') == message.from_user.id]
    
    if not message.text.isdigit():
        await message.reply("Введите номер задачи.")
        return
    
    task_number = int(message.text)
    if 1 <= task_number <= len(user_tasks):
        task_to_edit = user_tasks[task_number - 1]
        await state.update_data(
            selected_task_id=task_to_edit['id'],
            old_time=task_to_edit.get('time')
        )
        
        current_time = task_to_edit.get('time', 'без времени')
        await message.answer(
            f"Текущая задача: {task_to_edit['task']}\n"
            f"Текущее время: {current_time}\n\n"
            f"{ENTER_TASK_MSG}",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(STATE_EDIT_INPUT)
    else:
        await message.reply(INVALID_TASK_NUMBER_MSG)

@dp.message(STATE_EDIT_INPUT)
async def edit_task_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get('selected_task_id')
    old_time = data.get('old_time')
    
    
    task_index = None
    task_to_edit = None
    for i, task in enumerate(bot_list):
        if task['id'] == task_id:
            task_index = i
            task_to_edit = task
            break
    
    if task_index is None or task_to_edit is None:
        keyboard = create_main_keyboard()
        await message.answer("Ошибка: задача не найдена.", reply_markup=keyboard)
        await state.clear()
        return
    
    
    task_text, new_time = parse_task_input(message.text)
    
    
    if not task_text:
        await message.reply("Текст задачи не может быть пустым!")
        return
    
    if new_time == "invalid":
        await message.reply(INVALID_TIME_MSG)
        return
    

    if old_time and task_id in reminder_tasks:
        cancel_reminder(task_id)
    
    
    task_to_edit['task'] = task_text
    task_to_edit['time'] = new_time
    
    
    reply_text = ""
    if new_time:
        reply_text = f"{TASK_UPDATED_MSG}: '{task_text}' на {new_time}"
        
        
        reminder_time = calculate_reminder_time(new_time)
        if reminder_time:
            scheduled = await schedule_reminder(
                task_id, 
                message.from_user.id, 
                task_text, 
                reminder_time
            )
            if scheduled:
                reply_text += f"\n{REMINDER_SET_MSG} ({reminder_time.strftime('%H:%M')})"
            else:
                reply_text += "\n⚠️ Напоминание не установлено (время слишком близко)"
        else:
            reply_text += f"\n{NO_TIME_FOR_REMINDER_MSG}"
    else:
        reply_text = f"{TASK_UPDATED_MSG}: '{task_text}'"
    
    
    keyboard = create_main_keyboard()
    await message.answer(reply_text, reply_markup=keyboard)
    
    await state.clear()

@dp.message(F.text.lower().in_(["меню", "menu", "отмена", "cancel", "назад", "back"]))
async def return_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = create_main_keyboard()
    await message.answer("Возвращаю в главное меню:", reply_markup=keyboard)

@dp.message(Command("test_reminder"))
async def test_reminder(message: types.Message):
    """Тестовая команда для проверки напоминаний"""
    test_time = (datetime.now() + timedelta(minutes=2)).strftime("%H:%M")
    await message.answer(f"Тест напоминания установлен на {test_time}")
    
    reminder_time = datetime.now() + timedelta(minutes=1)  
    await schedule_reminder(
        9999,  
        message.from_user.id,
        "ТЕСТОВАЯ ЗАДАЧА",
        reminder_time
    )

async def check_and_reschedule_reminders():
    """Периодически проверяет и перепланирует напоминания"""
    while True:
        await asyncio.sleep(60)  
        
        for task in bot_list:
            task_id = task['id']
            task_time = task.get('time')
            user_id = task.get('user_id')
            
            if task_time and user_id and task_id not in reminder_tasks:
                
                reminder_time = calculate_reminder_time(task_time)
                if reminder_time:
                    await schedule_reminder(
                        task_id,
                        user_id,
                        task['task'],
                        reminder_time
                    )

async def on_startup():
    """Запускается при старте бота"""
    logger.info("Бот запускается...")
    
    
    asyncio.create_task(check_and_reschedule_reminders())
    
    
    for task in bot_list:
        task_time = task.get('time')
        if task_time:
            reminder_time = calculate_reminder_time(task_time)
            if reminder_time:
                await schedule_reminder(
                    task['id'],
                    task.get('user_id', 0),
                    task['task'],
                    reminder_time
                )

async def main():
    
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())