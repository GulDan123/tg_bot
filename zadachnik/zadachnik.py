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

class MyStates(StatesGroup):
    waiting_for_task_to_delete = State()
    waiting_for_task_to_edit_number = State()
    waiting_for_task_to_edit_text = State()
    waiting_for_new_task = State()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    buttons = [
        [types.KeyboardButton(text="Добавить задачу")],
        [types.KeyboardButton(text="Удалить задачу")],
        [types.KeyboardButton(text="Посмотреть задачи")],
        [types.KeyboardButton(text="Изменить задачу")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Что вы хотите сделать?"
    )
    await message.answer("Привет! Я бот для списка задач.", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Добавить задачу")
async def add_task_button(message: types.Message, state: FSMContext):
    await message.answer("Напишите вашу задачу:")
    await state.set_state(MyStates.waiting_for_new_task)

@dp.message(MyStates.waiting_for_new_task)
async def get_new_task(message: types.Message, state: FSMContext):
    global tasks, next_id
    
    if '|' in message.text:
        parts = message.text.split('|', 1)
        task_text = parts[0].strip()
        time_part = parts[1].strip() if len(parts) > 1 else ""
        
        try:
            if time_part:
                datetime.strptime(time_part, "%H:%M")
                task_time = time_part
            else:
                task_time = None
        except:
            task_time = None
            await message.answer("Время указано неправильно! Используйте формат ЧЧ:ММ")
            return
    else:
        task_text = message.text.strip()
        task_time = None
    
    new_task = {
        'id': next_id,
        'text': task_text,
        'time': task_time,
        'user': message.from_user.id
    }
    tasks.append(new_task)
    next_id += 1
    
    if task_time:
        await message.answer(f"Задача добавлена: '{task_text}' на {task_time}")
    else:
        await message.answer(f"Задача добавлена: '{task_text}'")
    
    await state.clear()
    await show_main_buttons(message)

@dp.message(lambda message: message.text == "Посмотреть задачи")
async def show_all_tasks(message: types.Message):
    if not tasks:
        await message.answer("У вас пока нет задач.")
        return
    
    user_tasks = []
    for task in tasks:
        if task['user'] == message.from_user.id:
            user_tasks.append(task)
    
    if not user_tasks:
        await message.answer("У вас пока нет задач.")
        return
    
    result = "Ваши задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        task_line = f"{i}. {task['text']}"
        if task['time']:
            task_line += f" (время: {task['time']})"
        result += task_line + "\n"
    
    await message.answer(result)

@dp.message(lambda message: message.text == "Удалить задачу")
async def delete_task_start(message: types.Message, state: FSMContext):
    user_tasks = []
    for task in tasks:
        if task['user'] == message.from_user.id:
            user_tasks.append(task)
    
    if not user_tasks:
        await message.answer("У вас нет задач для удаления.")
        return
    
    result = "Ваши задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        task_line = f"{i}. {task['text']}"
        if task['time']:
            task_line += f" (время: {task['time']})"
        result += task_line + "\n"
    
    result += "\nНапишите номер задачи для удаления:"
    await message.answer(result)
    await state.set_state(MyStates.waiting_for_task_to_delete)

@dp.message(MyStates.waiting_for_task_to_delete)
async def delete_task_confirm(message: types.Message, state: FSMContext):
    global tasks
    
    try:
        task_num = int(message.text)
        
        user_tasks = []
        for task in tasks:
            if task['user'] == message.from_user.id:
                user_tasks.append(task)
        
        if 1 <= task_num <= len(user_tasks):
            task_to_delete = user_tasks[task_num - 1]
            tasks = [task for task in tasks if task['id'] != task_to_delete['id']]
            await message.answer("Задача удалена!")
        else:
            await message.answer("Неправильный номер задачи.")
    
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
    
    await state.clear()
    await show_main_buttons(message)

@dp.message(lambda message: message.text == "Изменить задачу")
async def edit_task_start(message: types.Message, state: FSMContext):
    user_tasks = []
    for task in tasks:
        if task['user'] == message.from_user.id:
            user_tasks.append(task)
    
    if not user_tasks:
        await message.answer("У вас нет задач для изменения.")
        return
    
    result = "Ваши задачи:\n\n"
    for i, task in enumerate(user_tasks, 1):
        task_line = f"{i}. {task['text']}"
        if task['time']:
            task_line += f" (время: {task['time']})"
        result += task_line + "\n"
    
    result += "\nНапишите номер задачи для изменения:"
    await message.answer(result)
    await state.set_state(MyStates.waiting_for_task_to_edit_number)

@dp.message(MyStates.waiting_for_task_to_edit_number)
async def edit_task_select(message: types.Message, state: FSMContext):
    try:
        task_num = int(message.text)
        
        user_tasks = []
        for task in tasks:
            if task['user'] == message.from_user.id:
                user_tasks.append(task)
        
        if 1 <= task_num <= len(user_tasks):
            selected_task = user_tasks[task_num - 1]
            await state.update_data(task_id=selected_task['id'])
            
            await message.answer(
                f"Текущая задача: {selected_task['text']}\n"
                f"Напишите новый текст задачи (можно с временем через |):"
            )
            await state.set_state(MyStates.waiting_for_task_to_edit_text)
        else:
            await message.answer("Неправильный номер задачи.")
            await state.clear()
            await show_main_buttons(message)
    
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        await state.clear()
        await show_main_buttons(message)

@dp.message(MyStates.waiting_for_task_to_edit_text)
async def edit_task_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get('task_id')
    
    if not task_id:
        await message.answer("Ошибка: задача не найдена.")
        await state.clear()
        await show_main_buttons(message)
        return
    
    for i, task in enumerate(tasks):
        if task['id'] == task_id:
            if '|' in message.text:
                parts = message.text.split('|', 1)
                new_text = parts[0].strip()
                time_part = parts[1].strip() if len(parts) > 1 else ""
                
                try:
                    if time_part:
                        datetime.strptime(time_part, "%H:%M")
                        new_time = time_part
                    else:
                        new_time = None
                except:
                    await message.answer("Время указано неправильно! Используйте формат ЧЧ:ММ")
                    return
            else:
                new_text = message.text.strip()
                new_time = None
            
            tasks[i]['text'] = new_text
            tasks[i]['time'] = new_time
            
            if new_time:
                await message.answer(f"Задача изменена: '{new_text}' на {new_time}")
            else:
                await message.answer(f"Задача изменена: '{new_text}'")
            
            break
    
    await state.clear()
    await show_main_buttons(message)

async def show_main_buttons(message: types.Message):
    buttons = [
        [types.KeyboardButton(text="Добавить задачу")],
        [types.KeyboardButton(text="Удалить задачу")],
        [types.KeyboardButton(text="Посмотреть задачи")],
        [types.KeyboardButton(text="Изменить задачу")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Что вы хотите сделать?"
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())