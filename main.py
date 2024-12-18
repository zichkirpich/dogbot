import asyncio
import config
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# Get the database URL from the configuration file
DATABASE_URL = config.db_token

# Initialize the Aiogram Dispatcher
dp = Dispatcher()


# Create a state group for marking dogs as walked
class MarkDogState(StatesGroup):
    waiting_for_dog_name = State()

def get_number_emoji(number):
    emoji_map = {
        '1': '1️⃣',
        '2': '2️⃣',
        '3': '3️⃣'
    }
    return emoji_map.get(str(number), number)


replyButton1 = KeyboardButton(text="Didn't walk")
replyButton2 = KeyboardButton(text="Walked")
replyButton3 = KeyboardButton(text="Mark")
replyButton4 = KeyboardButton(text="Filter")

keyboard1 = ReplyKeyboardMarkup(
    keyboard=[
        [replyButton1, replyButton2, replyButton3, replyButton4]
    ],
    resize_keyboard=True
)

inButton1 = InlineKeyboardButton(text="1", callback_data="filter_1")
inButton2 = InlineKeyboardButton(text="2", callback_data="filter_2")
inButton3 = InlineKeyboardButton(text="3", callback_data="filter_3")

keyboard2 = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="filter_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="filter_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="filter_3")
        ],
        [
            InlineKeyboardButton(text="Weak", callback_data="weak"),
            InlineKeyboardButton(text="Normal", callback_data="normal"),
            InlineKeyboardButton(text="Strong", callback_data="strong")
        ]
    ]
)


def notWalked():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT NAME FROM DOGS WHERE ISWALKED IS FALSE")
    result = cursor.fetchall()
    names = list(map(lambda x: x[0], result))
    reply = "<b>Did not walk🥺:</b>\n" + "\n".join(names)
    cursor.close()
    conn.close()
    return reply


def walked():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT NAME FROM DOGS WHERE ISWALKED IS TRUE")
    result = cursor.fetchall()
    names = list(map(lambda x: x[0], result))
    reply = "<b>Walked😋:</b>\n" + "\n".join(names)
    cursor.close()
    conn.close()
    return reply


async def mark_dog_as_walked(msg: str):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT NAME FROM DOGS")
    result = cursor.fetchall()
    names = list(map(lambda x: x[0], result))
    namesLower = list(map(lambda x: x.lower(), names))
    splitted_msg = [name.strip() for name in msg.split(", ")]
    updated_dogs = []
    not_found_dogs = []


    for name in splitted_msg:
        if name.lower() in namesLower:
            upperName = []
            splitted_name = [name.strip() for name in name.split(" ")]
            for elem in splitted_name:
                nameList = list(elem)
                nameList[0] = nameList[0].upper()
                upperName.append(''.join(nameList))
            newName = ' '.join(upperName)
            cursor.execute("UPDATE DOGS SET ISWALKED = TRUE WHERE NAME = %s", (newName,))
            updated_dogs.append(name)
        else:
            not_found_dogs.append(name)
    conn.commit()
    cursor.close()
    conn.close()
    return {
        "updated": updated_dogs,
        "not_found": not_found_dogs
    }



# Handle the /start command
@dp.message(CommandStart())
async def cmd_start(msg: types.Message) -> None:
    await msg.answer(text="Hello! Welcome😉")


@dp.message(Command("walk"))
async def cmd_walk(msg: types.Message) -> None:
    await msg.answer("Choose an option", reply_markup=keyboard1)


@dp.message(Command("clear"))
async def cmd_clear(msg: types.Message) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    if msg.from_user.id in config.idList:
        cursor.execute("UPDATE DOGS SET ISWALKED = FALSE WHERE ISWALKED = TRUE")
        conn.commit()
        cursor.close()
        conn.close()
        await msg.answer("<b>Cleared successfully!😎</b>", parse_mode='html')
    else:
        await msg.answer("<b>You can't do that😶‍🌫️</b>", parse_mode='html')


@dp.message(Command("info"))
async def cmd_info(msg: types.Message) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM DOGS ORDER BY 2")
    result = cursor.fetchall()
    names = list(map(lambda x: x[0], result))
    reply = "<b>All dogs😋:</b>\n" + "\n".join(names)
    conn.commit()
    cursor.close()
    conn.close()
    await msg.answer(reply, parse_mode='html')


@dp.callback_query(lambda query: query.data.startswith("filter_") or query.data in ["weak", "normal", "strong"])
async def handle_callback(call: types.CallbackQuery):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        if call.data.startswith("filter_"):
            quantity = call.data.split("_")[1]
            cursor.execute("SELECT NAME FROM DOGS WHERE QUANTITY = %s AND ISWALKED IS FALSE", (quantity,))
            result_title = f"{get_number_emoji(quantity)}"
        elif call.data in ["weak", "normal", "strong"]:
            cursor.execute("SELECT NAME FROM DOGS WHERE FEATURE = %s AND ISWALKED IS FALSE ORDER BY QUANTITY", (call.data,))
            result_title = call.data.capitalize()

        result = cursor.fetchall()
        names = list(map(lambda x: x[0], result))
        result_text = f"<b>{result_title}:</b>\n" + "\n".join(names)

        await call.message.answer(result_text, parse_mode='html')
    except Exception as e:
        await call.message.answer(f"Error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    await call.answer()


@dp.message()
async def answer(message: types.Message, state: FSMContext) -> None:
    if message.text == "Didn't walk":
        result = str(notWalked())
        await message.answer(result, parse_mode='html')
    elif message.text == "Walked":
        result = str(walked())
        await message.answer(result, parse_mode='html')
    elif message.text == "Filter":
        await message.answer("<b>Enter filter:</b>", reply_markup=keyboard2, parse_mode='html')
    elif message.text == "Mark":
        if message.from_user.id in config.idList:
            await message.answer("<b>Please enter the names of dogs you want to mark as walked (separated by comma)🤓:</b>", parse_mode='html')
            await state.set_state(MarkDogState.waiting_for_dog_name)
        else:
            await message.answer("<b>You can't do that😶‍🌫️</b>", parse_mode='html')
    elif await state.get_state() == MarkDogState.waiting_for_dog_name:
        try:
            result = await mark_dog_as_walked(message.text)

            if result['updated']:
                await message.answer(f"<b>Dogs marked as walked🥳:</b> {', '.join(result['updated'])}", parse_mode='html')

            if result['not_found']:
                await message.answer(f"<b>Dogs not found😬:</b> {', '.join(result['not_found'])}", parse_mode='html')

            await state.clear()
        except Exception as e:
            await message.answer(str(e))
    else:
        await message.answer('<b>Try again😶‍🌫️</b>', parse_mode='html')


# Main function to start the bot
async def main() -> None:
    bot = Bot(config.bot_token)
    await dp.start_polling(bot)


if __name__ == '__main__':
    print("Bot started...")
    asyncio.run(main())