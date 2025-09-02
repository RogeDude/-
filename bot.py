import telebot
import re
import time
import sqlite3
from telebot import types
from config import TOKEN, ADMIN_CHAT_ID
from validators import is_valid_phone
from storage import user_data, applications
from keyboards import smu_keyboard, task_keyboard
from admin import admin_keyboard_appr, admin_keyboard_ok
from rules import rules

bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('geodesy_bot.db')
    cursor = conn.cursor()
    
    # Создание таблицы пользователей (без изменений)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      user_id INTEGER PRIMARY KEY,
                      username TEXT,
                      first_name TEXT,
                      registration_date TEXT)''')
    
    # Измененная таблица заявок - timestamp теперь TEXT в нужном формате
    cursor.execute('''CREATE TABLE IF NOT EXISTS applications (
                      app_id TEXT PRIMARY KEY,
                      user_id INTEGER,
                      smu TEXT,
                      object TEXT,
                      task TEXT,
                      comment TEXT,
                      phone TEXT,
                      contact_name TEXT,
                      status TEXT,
                      timestamp TEXT,
                      FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    
    conn.commit()
    conn.close()

# Функция для добавления пользователя в БД
def add_user_to_db(user_id, username, first_name):
    conn = sqlite3.connect('geodesy_bot.db')
    cursor = conn.cursor()
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        registration_date = time.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?)', 
                      (user_id, username, first_name, registration_date))
    
    conn.commit()
    conn.close()

# Функция для добавления заявки в БД
def add_application_to_db(app_data):
    conn = sqlite3.connect('geodesy_bot.db')
    cursor = conn.cursor()
    
    # Форматируем время в нужный формат перед сохранением
    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(app_data['timestamp']))
    
    cursor.execute('''INSERT INTO applications VALUES 
                     (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (app_data['app_id'],
                   app_data['user_id'],
                   app_data['smu'],
                   app_data['object'],
                   app_data['task'],
                   app_data['comment'],
                   app_data['phone'],
                   app_data['contact_name'],
                   app_data['status'],
                   formatted_time))  # Сохраняем отформатированное время
    
    conn.commit()
    conn.close()

# Функция для обновления статуса заявки в БД
def update_application_status(app_id, new_status):
    conn = sqlite3.connect('geodesy_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE applications SET status = ? WHERE app_id = ?', 
                  (new_status, app_id))
    
    # Обновляем также в оперативной памяти, если заявка там есть
    if app_id in applications:
        applications[app_id]['status'] = new_status
    
    conn.commit()
    conn.close()

def send_to_admin(text):
    """Универсальная функция отправки сообщений админу"""
    bot.send_message(ADMIN_CHAT_ID, text, parse_mode='Markdown')

################### Команды ####################

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, "Возможные команды:\n"
                     "/start - Начало составления заявки\n"
                     "/help - Вывода всех доступных обычному пользователю команд\n"
                     "/rules - Показывает правила заполнения заявки а также работу с ботом\n"
                     "/administrators - Показывает текущих администраторов")

@bot.message_handler(commands=['start'])
def start(message):
    # Добавляем пользователя в базу данных
    add_user_to_db(
        message.from_user.id,
        message.from_user.username or "неизвестно",
        message.from_user.first_name or "неизвестно"
    )
    
    user_data[message.chat.id] = {
        'user_info': {
            'id': message.from_user.id,
            'username': message.from_user.username or "неизвестно",
            'first_name': message.from_user.first_name or "неизвестно"
        },
        'user_id': message.from_user.id
    }

    bot.send_message(message.chat.id, rules)
    bot.send_message(message.chat.id,
                    "📋 Привет! Это бот для подачи заявок службе геодезии.\n"
                    "Пожалуйста, выберите свой СМУ:",
                    reply_markup=smu_keyboard())
    bot.register_next_step_handler(message, get_smu)

@bot.message_handler(commands=['rules'])
def start(message):
    bot.send_message(message.chat.id, rules)

@bot.message_handler(commands=['administrators'])
def help_command(message):
    bot.send_message(message.chat.id, "@DelfsDaniel - Волков Д.А. Ведущий специалист службы геодезии")

################### Обработка заявки ####################

def get_smu(message):
    chat_id = message.chat.id
    user_data[chat_id]['smu'] = message.text
    bot.send_message(chat_id, "🏢 Укажите объект:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_object)

def get_object(message):
    chat_id = message.chat.id
    user_data[chat_id]['object'] = message.text
    bot.send_message(chat_id, "🔧 Вид работ:", reply_markup=task_keyboard())
    bot.register_next_step_handler(message, get_task)

def get_task(message):
    chat_id = message.chat.id
    user_data[chat_id]['task'] = message.text
    bot.send_message(chat_id, "📝 Укажите комментарий к виду работ а также дом/хостел:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_comment)

def get_comment(message):
    chat_id = message.chat.id
    user_data[chat_id]['comment'] = message.text
    bot.send_message(chat_id, "📱 Введите номер телефона ответственного на объекте:")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    chat_id = message.chat.id
    phone = message.text
    
    if not is_valid_phone(phone):
        bot.send_message(chat_id, "❌ Некорректный номер. Введите снова:")
        bot.register_next_step_handler(message, get_phone)
        return
    
    user_data[chat_id]['phone'] = phone
    bot.send_message(chat_id, "👤 ФИО ответственного на объекте:")
    bot.register_next_step_handler(message, get_contact_name)

def get_contact_name(message):
    chat_id = message.chat.id
    
    # Проверяем, что все необходимые данные собраны
    if chat_id not in user_data or 'contact_name' in user_data[chat_id]:
        bot.send_message(chat_id, "❌ Произошла ошибка при обработке заявки. Пожалуйста, начните заново с /start")
        return
    
    user_data[chat_id]['contact_name'] = message.text
    
    # Генерируем ID заявки
    app_id = str(int(time.time()))
    
    # Формируем полные данные заявки
    application = {
        'app_id': app_id,
        'user_id': message.from_user.id,
        'user_info': {
            'id': message.from_user.id,
            'username': message.from_user.username or "неизвестно",
            'first_name': message.from_user.first_name or "неизвестно"
        },
        'smu': user_data[chat_id].get('smu', 'не указано'),
        'object': user_data[chat_id].get('object', 'не указано'),
        'task': user_data[chat_id].get('task', 'не указано'),
        'comment': user_data[chat_id].get('comment', 'нет'),
        'phone': user_data[chat_id].get('phone', 'не указан'),
        'contact_name': user_data[chat_id].get('contact_name', 'не указано'),
        'status': 'Ожидает...',
        'timestamp': time.time()
    }
    
    # Сохраняем в оперативную память
    applications[app_id] = application
    
    # Сохраняем в базу данных
    try:
        add_user_to_db(
            message.from_user.id,
            message.from_user.username or "неизвестно",
            message.from_user.first_name or "неизвестно"
        )
        add_application_to_db(application)
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")
        bot.send_message(chat_id, "⚠️ Произошла ошибка при сохранении заявки. Попробуйте позже.")
        return
    
    # Формируем сообщение для админа
    try:
        application_text = format_application(app_id)
        bot.send_message(chat_id, "✅ Заявка успешно создана! Спасибо.")
        bot.send_message(
            ADMIN_CHAT_ID,
            application_text,
            parse_mode='Markdown',
            reply_markup=admin_keyboard_ok(app_id)
        )
    except Exception as e:
        print(f"Ошибка при отправке заявки: {e}")
        bot.send_message(chat_id, "⚠️ Заявка создана, но не отправлена администратору. Свяжитесь с ним отдельно.")
    
    # Очищаем временные данные
    if chat_id in user_data:
        del user_data[chat_id]

def format_application(app_id):
    # Сначала проверяем в оперативной памяти
    app = applications.get(app_id)
    
    if not app:
        # Если нет в памяти, загружаем из БД
        conn = None
        try:
            conn = sqlite3.connect('geodesy_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, smu, object, task, comment, phone, contact_name, status, timestamp 
                FROM applications WHERE app_id = ?
            ''', (app_id,))
            app_data = cursor.fetchone()
            
            if not app_data:
                return "❌ Заявка не найдена"
            
            cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (app_data[0],))
            user_data = cursor.fetchone()
            
            app = {
                'user_info': {
                    'id': app_data[0],
                    'username': user_data[0] if user_data else "неизвестно",
                    'first_name': user_data[1] if user_data else "неизвестно"
                },
                'smu': app_data[1],
                'object': app_data[2],
                'task': app_data[3],
                'comment': app_data[4],
                'phone': app_data[5],
                'contact_name': app_data[6],
                'status': app_data[7],
                'timestamp': app_data[8],
                'user_id': app_data[0]
            }
            
            # Сохраняем в память для будущих обращений
            applications[app_id] = app
            
        except Exception as e:
            print(f"Ошибка при получении заявки из БД: {e}")
            return "❌ Ошибка при получении данных заявки"
        finally:
            if conn:
                conn.close()
    
    # Форматируем сообщение
    status_icons = {
        'Ожидает...': '🟡',
        'Выполнено': '✅',
        'Не выполнено': '❌',
        'Заявка принята': '🟢',
        'Заявка отклонена': '❌'
    }
    
    return (
        f"📄 *Новая заявка*\n\n"
        f"👤 *Отправитель:*\n"
        f"ID: `{app['user_info']['id']}`\n"
        f"Username: @{app['user_info']['username']}\n"
        f"Имя: {app['user_info']['first_name']}\n\n"
        f"📌 *СМУ:* {app['smu']}\n"
        f"🏢 *Объект:* {app['object']}\n"
        f"🔧 *Вид работ:* {app['task']}\n"
        f"📝 *Комментарий:* {app['comment']}\n"
        f"📱 *Телефон:* {app['phone']}\n"
        f"👥 *ФИО ответственного:* {app['contact_name']}\n\n"
        f"🕒 *Время подачи:* {time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(float(app['timestamp']))) if isinstance(app['timestamp'], (int, float)) else app['timestamp']}\n"
        f"🔘 *Статус:* {status_icons.get(app['status'], '🟡')} {app['status']}"
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if not call.data or '_' not in call.data:
            bot.answer_callback_query(call.id, "Неверный формат callback данных")
            return
            
        action, app_id = call.data.split('_', 1)
        
        # Пытаемся получить заявку из памяти или БД
        app = applications.get(app_id)
        if not app:
            conn = None
            try:
                conn = sqlite3.connect('geodesy_bot.db')
                cursor = conn.cursor()
                
                # Получаем данные заявки
                cursor.execute('''
                    SELECT user_id, smu, object, task, comment, phone, contact_name, status, timestamp 
                    FROM applications WHERE app_id = ?
                ''', (app_id,))
                app_data = cursor.fetchone()
                
                if not app_data:
                    bot.answer_callback_query(call.id, "Заявка не найдена!")
                    return
                
                # Получаем информацию о пользователе
                cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (app_data[0],))
                user_data = cursor.fetchone()
                
                # Формируем полную структуру заявки
                app = {
                    'user_info': {
                        'id': app_data[0],
                        'username': user_data[0] if user_data else "неизвестно",
                        'first_name': user_data[1] if user_data else "неизвестно"
                    },
                    'user_id': app_data[0],
                    'smu': app_data[1],
                    'object': app_data[2],
                    'task': app_data[3],
                    'comment': app_data[4],
                    'phone': app_data[5],
                    'contact_name': app_data[6],
                    'status': app_data[7],
                    'timestamp': app_data[8]
                }
                
                # Сохраняем в оперативную память
                applications[app_id] = app
                
            except Exception as e:
                print(f"Ошибка при получении заявки из БД: {e}")
                bot.answer_callback_query(call.id, "Ошибка при загрузке заявки")
                return
            finally:
                if conn:
                    conn.close()
        
        # Остальной код обработки callback...
        status_map = {
            'approve': 'Выполнено',
            'reject': 'Не выполнено',
            'ok': 'Заявка принята',
            'dont': 'Заявка отклонена'
        }
        
        if action not in status_map:
            bot.answer_callback_query(call.id, "Неизвестное действие")
            return
            
        new_status = status_map[action]
        app['status'] = new_status
        
        # Обновляем статус в БД
        try:
            update_application_status(app_id, new_status)
        except Exception as e:
            print(f"Ошибка при обновлении статуса в БД: {e}")
            bot.answer_callback_query(call.id, "Ошибка при сохранении статуса")
            return
        
        # Отправляем уведомление пользователю
        try:
            user_id = app['user_id']
            messages = {
                'approve': "✅ Ваша заявка выполнена!",
                'reject': "❌ Ваша заявка не выполнена.\nПожалуйста, свяжитесь с администратором.",
                'ok': "❗ Ваша заявка просмотрена и принята.",
                'dont': "❗ Ваша заявка не принята и была отклонена."
            }
            bot.send_message(user_id, messages[action])
        except Exception as e:
            print(f"Ошибка при отправке уведомления пользователю: {e}")
        
        # Обновляем сообщение у админа
        try:
            reply_markup = None
            if action == 'ok':
                reply_markup = admin_keyboard_appr(app_id)
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=format_application(app_id),
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            bot.answer_callback_query(call.id, f"Статус изменен на: {new_status}")
        except Exception as e:
            print(f"Ошибка при обновлении сообщения админа: {e}")
            bot.answer_callback_query(call.id, "Ошибка при обновлении сообщения")
            
    except Exception as e:
        print(f"Ошибка обработки callback: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

if __name__ == '__main__':
    # Инициализируем базу данных при запуске
    init_db()
    print("Бот запущен и ожидает сообщений...")
    bot.polling(none_stop=True)