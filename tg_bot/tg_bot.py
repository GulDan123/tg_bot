import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

BOT_TOKEN = "8419754884:AAHu3a61esoz9IVxdW_nCu1z-YZIpkqCDBs"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

bot_list = []
task_id_counter = 1


class UserState(StatesGroup):
    delete_task = State()
    edit_select = State()
    edit_input = State()
    add_state = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Добавить задачу")],
        [types.KeyboardButton(text="Удалить задачу")],
        [types.KeyboardButton(text="Просмотр всех задач")],
        [types.KeyboardButton(text="Редактировать задачу")],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    await message.answer("Привет, я бот помошник для создания задач", reply_markup=keyboard)

@dp.message(F.text == "Добавить задачу")
async def add_a_task(message: types.Message, state: FSMContext):
    global bot_list, task_id_counter
    await message.reply("Введите вашу задачу")
    await state.set_state(UserState.add_state)

@dp.message(UserState.add_state)
async def process_task_input(message: types.Message, state: FSMContext):
    global bot_list, task_id_counter
    bot_list.append({'id': task_id_counter, 'task': message.text})
    task_id_counter += 1
    await state.clear()
    await message.reply("Задача добавлена")

@dp.message(F.text == "Просмотр всех задач")
async def show_tasks(message: types.Message):
    if not bot_list:
        await message.answer("Список задач пуст.")
        return
    tasks_text = ""
    for index, task in enumerate(bot_list, start=1):
        tasks_text += f"{index}. {task['task']}\n"
    await message.answer(f"Ваш список:\n{tasks_text}")

@dp.message(F.text == "Удалить задачу")
async def show_tasks(message: types.Message, state: FSMContext):
    if not bot_list:
        await message.answer("Список задач пуст.")
        return
    tasks_text = ""
    for index, task in enumerate(bot_list, start=1):
        tasks_text += f"{index}. {task['task']}\n"
    await message.answer(f"Ваш список:\n{tasks_text}\nВведите номер задачи для удаления")
    await state.set_state(UserState.delete_task)
    
@dp.message(UserState.delete_task)
async def delete_task(message: types.Message, state: FSMContext):
    task_number = int(message.text) - 1
    if task_number < len(bot_list):
        del bot_list[task_number]
        await message.answer("Задача удалена.")
        await state.clear()




@dp.message(F.text == "Редактировать задачу")
async def edit_task_prompt(message: types.Message, state: FSMContext):
    if not bot_list:
        await message.answer("Список задач пуст.")
        return
    tasks_text = ""
    for index, task in enumerate(bot_list, start=1):
        tasks_text += f"{index}. {task['task']}\n"
    await message.answer(f"Ваш список:\n{tasks_text}\nВведите номер задачи для редактирования:")
    await state.set_state(UserState.edit_select)

@dp.message(UserState.edit_select)
async def edit_task_select(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.reply("Введите номер задачи:.")
        return
    task_number = int(message.text)
    if 1 <= task_number <= len(bot_list):
        await state.update_data(selected_task=task_number - 1)
        await message.answer("Введите новую задачу:")
        await state.set_state(UserState.edit_input)  
    else:
        await message.reply("Неверный номер. Попробуйте снова.")

@dp.message(UserState.edit_input)  
async def edit_task_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get('selected_task')
    if index is not None:
        bot_list[index]['task'] = message.text
        await message.answer("Задача обновлена.")
        await state.clear()
    else:
        await message.answer("Ошибка: не удалось определить задачу для редактирования.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())