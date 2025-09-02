from telebot import types
from config import ADMIN_CHAT_ID

def admin_keyboard_appr(app_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Выполнено", callback_data=f"approve_{app_id}"),
        types.InlineKeyboardButton("❌ Не выполнено", callback_data=f"reject_{app_id}"),
    )

    return markup

def admin_keyboard_ok(app_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Принято", callback_data=f"ok_{app_id}"),
        types.InlineKeyboardButton("❌ Не принято", callback_data=f"dont_{app_id}")
    )

    return markup