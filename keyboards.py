from telebot import types
from config import ADMIN_CHAT_ID

def smu_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width = 4, resize_keyboard = True, one_time_keyboard = True)
    markup.add(
        '1', '2', '3', '4',
        '5', '6', '7', '8',
        '9', '10', '11', '12',
        '13'
    )
    return markup

def task_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width = 4, resize_keyboard = True, one_time_keyboard = True)
    markup.add('Разбивка', 'Съемка', 'Сгущение ГРО')
    return markup