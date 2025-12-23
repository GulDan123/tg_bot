import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from dotenv import load_dotenv
load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher()

tasks = []
next_id = 1
reminders = {}

START_MSG = "Привет! Я бот для задач"
EMPTY_TASKS_MSG = "У вас нет задач"
ADD_TASK_MSG = "Напишите задачу и время через | (например: Позвонить маме | 18:00)"
WRONG_TIME_MSG = "Неправильное время! Пишите так: 14:30"
TASK_ADDED_MSG = "Задача добавлена"
TASK_CHANGED_MSG = "Задача изменена"
TASK_DELETED_MSG = "Задача удалена"
REMINDER_MSG = "Напоминание: через час задача: {}"
REMINDER_SET_MSG = "Напоминание поставлено"

class BotStates(StatesGroup):
    adding_task = State()
    deleting_task = State()
    choosing_task_to_edit = State()
    editing_task = State()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    buttons = [
        [types.KeyboardButton(text="Добавить")],
        [types.KeyboardButton(text="Удалить")],
        [types.KeyboardButton(text="Посмотреть")],
        [types.KeyboardButton(text="Изменить")],
        [types.KeyboardButton(text="Напоминания")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    await message.answer(START_MSG, reply_markup=keyboard)

@dp.message(lambda m: m.text == "Добавить")
async def add_task_start(message: types.Message, state: FSMContext):
    await message.answer(ADD_TASK_MSG)
    await state.set_state(BotStates.adding_task)

@dp.message(BotStates.adding_task)
async def add_task_finish(message: types.Message, state: FSMContext):
    global tasks, next_id
    
    text = message.text
    
    if "|" in text:
        parts = text.split("|", 1)
        name = parts[0].strip()
        time_text = parts[1].strip()
        
        try:
            datetime.strptime(time_text, "%H:%M")
            time_ok = True
        except:
            time_ok = False
        
        if not time_ok:
            await message.answer(WRONG_TIME_MSG)
            return
    else:
        name = text.strip()
        time_text = None
    
    new_task = {
        "id": next_id,
        "name": name,
        "time": time_text,
        "user": message.from_user.id
    }
    
    tasks.append(new_task)
    next_id += 1
    
    if time_text:
        await message.answer(f"{TASK_ADDED_MSG}: {name} в {time_text}")
        await set_reminder(new_task["id"], message.from_user.id, name, time_text)
    else:
        await message.answer(f"{TASK_ADDED_MSG}: {name}")
    
    await state.clear()
    await show_buttons(message)

async def set_reminder(task_id, user_id, task_name, task_time):
    from datetime import timedelta
    
    try:
        now = datetime.now()
        task_dt = datetime.strptime(task_time, "%H:%M")
        task_dt = task_dt.replace(year=now.year, month=now.month, day=now.day)
        
        if task_dt < now:
            task_dt = task_dt + timedelta(days=1)
        
        reminder_dt = task_dt - timedelta(hours=1)
        
        if reminder_dt < now:
            return
        
        wait_seconds = (reminder_dt - now).total_seconds()
        
        async def send_reminder():
            await asyncio.sleep(wait_seconds)
            try:
                await bot.send_message(user_id, REMINDER_MSG.format(task_name))
            except:
                pass
        
        task = asyncio.create_task(send_reminder())
        reminders[task_id] = task
        
        await asyncio.sleep(0.1)
        
    except:
        pass

@dp.message(lambda m: m.text == "Посмотреть")
async def show_tasks_handler(message: types.Message):
    if not tasks:
        await message.answer(EMPTY_TASKS_MSG)
        return
    
    user_tasks = [t for t in tasks if t["user"] == message.from_user.id]
    
    if not user_tasks:
        await message.answer(EMPTY_TASKS_MSG)
        return
    
    result = "Ваши задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        line = f"{i}. {task['name']}"
        if task["time"]:
            line += f" ({task['time']})"
        result += line + "\n"
    
    await message.answer(result)

@dp.message(lambda m: m.text == "Удалить")
async def delete_task_start(message: types.Message, state: FSMContext):
    user_tasks = [t for t in tasks if t["user"] == message.from_user.id]
    
    if not user_tasks:
        await message.answer(EMPTY_TASKS_MSG)
        return
    
    result = "Выберите номер задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        line = f"{i}. {task['name']}"
        if task["time"]:
            line += f" ({task['time']})"
        result += line + "\n"
    
    await message.answer(result)
    await state.set_state(BotStates.deleting_task)

@dp.message(BotStates.deleting_task)
async def delete_task_finish(message: types.Message, state: FSMContext):
    global tasks
    
    try:
        num = int(message.text)
    except:
        await message.answer("Введите число")
        return
    
    user_tasks = [t for t in tasks if t["user"] == message.from_user.id]
    
    if num < 1 or num > len(user_tasks):
        await message.answer("Нет такой задачи")
        await state.clear()
        await show_buttons(message)
        return
    
    task_to_remove = user_tasks[num - 1]
    
    if task_to_remove["id"] in reminders:
        reminders[task_to_remove["id"]].cancel()
        del reminders[task_to_remove["id"]]
    
    tasks = [t for t in tasks if t["id"] != task_to_remove["id"]]
    
    await message.answer(TASK_DELETED_MSG)
    await state.clear()
    await show_buttons(message)

@dp.message(lambda m: m.text == "Изменить")
async def edit_task_start(message: types.Message, state: FSMContext):
    user_tasks = [t for t in tasks if t["user"] == message.from_user.id]
    
    if not user_tasks:
        await message.answer(EMPTY_TASKS_MSG)
        return
    
    result = "Выберите номер задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        line = f"{i}. {task['name']}"
        if task["time"]:
            line += f" ({task['time']})"
        result += line + "\n"
    
    await message.answer(result)
    await state.set_state(BotStates.choosing_task_to_edit)

@dp.message(BotStates.choosing_task_to_edit)
async def edit_task_choose(message: types.Message, state: FSMContext):
    try:
        num = int(message.text)
    except:
        await message.answer("Введите число")
        return
    
    user_tasks = [t for t in tasks if t["user"] == message.from_user.id]
    
    if num < 1 or num > len(user_tasks):
        await message.answer("Нет такой задачи")
        await state.clear()
        await show_buttons(message)
        return
    
    task_to_edit = user_tasks[num - 1]
    await state.update_data(task_id=task_to_edit["id"])
    
    await message.answer(f"Сейчас: {task_to_edit['name']}\nВведите новый текст:")
    await state.set_state(BotStates.editing_task)

@dp.message(BotStates.editing_task)
async def edit_task_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    
    if not task_id:
        await message.answer("Ошибка")
        await state.clear()
        await show_buttons(message)
        return
    
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            old_time = task["time"]
            
            text = message.text
            
            if "|" in text:
                parts = text.split("|", 1)
                new_name = parts[0].strip()
                new_time = parts[1].strip()
                
                try:
                    datetime.strptime(new_time, "%H:%M")
                    time_ok = True
                except:
                    time_ok = False
                
                if not time_ok:
                    await message.answer(WRONG_TIME_MSG)
                    return
            else:
                new_name = text.strip()
                new_time = None
            
            tasks[i]["name"] = new_name
            tasks[i]["time"] = new_time
            
            if task_id in reminders:
                reminders[task_id].cancel()
                del reminders[task_id]
            
            if new_time:
                await set_reminder(task_id, task["user"], new_name, new_time)
            
            await message.answer(TASK_CHANGED_MSG)
            break
    
    await state.clear()
    await show_buttons(message)

@dp.message(lambda m: m.text == "Напоминания")
async def show_reminders_handler(message: types.Message):
    user_task_ids = [t["id"] for t in tasks if t["user"] == message.from_user.id]
    user_reminders = [rid for rid in reminders if rid in user_task_ids]
    
    if not user_reminders:
        await message.answer("Нет напоминаний")
        return
    
    result = "Ваши напоминания:\n\n"
    for task_id in user_reminders:
        for task in tasks:
            if task["id"] == task_id:
                result += f"• {task['name']} ({task.get('time', 'без времени')})\n"
                break
    
    await message.answer(result)

async def show_buttons(message: types.Message):
    buttons = [
        [types.KeyboardButton(text="Добавить")],
        [types.KeyboardButton(text="Удалить")],
        [types.KeyboardButton(text="Посмотреть")],
        [types.KeyboardButton(text="Изменить")],
        [types.KeyboardButton(text="Напоминания")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

@dp.message(Command("menu"))
async def menu_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await show_buttons(message)

async def main():
    print("Бот работает")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())