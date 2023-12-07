import telebot
import sqlite3
from threading import Lock

conn = sqlite3.connect('user_balances.db', check_same_thread=False)
cursor = conn.cursor()
lock = Lock()

cursor.execute('''CREATE TABLE IF NOT EXISTS user_balances (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER
                )''')
conn.commit()

bot = telebot.TeleBot("6493355489:AAFS0U9cUNIhh3gwozXEMXD4233FCHa-KW4")


@bot.message_handler(func=lambda message: message.text == 'Поддержка')
def show_support(message):
    support_message = "Если у вас есть вопросы, свяжитесь со мной: @drakysik"
    bot.send_message(message.chat.id, support_message)


@bot.message_handler(commands=['start'])
def start(message):
    reply_markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
    buttons = ['Баланс', 'Ввести промокод', 'Играть', 'Запросить выигрыш', 'Создатели', 'Поддержка']
    reply_markup.add(*buttons)
    bot.reply_to(message, "Привет! Куда направимся?", reply_markup=reply_markup)


@bot.message_handler(func=lambda message: message.text == 'Создатели')
def show_creators(message):
    creators_message = "Создатели бота: Прозоров Алексей и Пушкин Максим"
    bot.reply_to(message, creators_message)

    user_id = message.chat.id
    with lock:
        cursor.execute('INSERT OR IGNORE INTO user_balances (user_id, balance) VALUES (?, ?)', (user_id, 0))
        conn.commit()


@bot.message_handler(func=lambda message: message.text == 'Баланс')
def check_balance(message):
    user_id = message.chat.id
    with lock:
        cursor.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

    if result is not None:
        balance = result[0]
        bot.reply_to(message, f"Ваш текущий баланс: {balance}")
    else:
        bot.reply_to(message, "Ваш баланс не найден. Возможно, вы не активировали промокод или не играли еще.")


@bot.message_handler(func=lambda message: message.text == 'Ввести промокод')
def activate_promo_code(message):
    user_id = message.chat.id

    msg = bot.reply_to(message, "Введите промокод:")
    bot.register_next_step_handler(msg, lambda msg: process_promo_code(msg, user_id))


def process_promo_code(message, user_id):
    promo_code = message.text.lower()

    with lock:
        cursor.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

    if result is None:
        with lock:
            cursor.execute('INSERT INTO user_balances (user_id, balance) VALUES (?, 0)', (user_id,))
            conn.commit()

    if promo_code == 'drakysb':
        cursor.execute('UPDATE user_balances SET balance = balance + 100 WHERE user_id = ?', (user_id,))
        conn.commit()

        cursor.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,))
        new_balance = cursor.fetchone()[0]
        bot.reply_to(message, "Промокод успешно активирован! Вам зачислено 100 монет.")
        bot.reply_to(message, f"Ваш текущий баланс: {new_balance}")
    else:
        bot.reply_to(message, "Неверный промокод!")


@bot.message_handler(func=lambda message: message.text == 'Играть')
def play_coin_flip(message):
    msg = bot.reply_to(message, "Выберите 'Орел' или 'Решка':")
    bot.register_next_step_handler(msg, process_coin_flip_choice)


def process_coin_flip_choice(message):
    choice = message.text.lower().strip()

    if choice in ['орел', 'решка']:
        msg = bot.reply_to(message, "Введите сумму вашей ставки:")
        bot.register_next_step_handler(msg, process_coin_flip_bet, choice)
    else:
        bot.reply_to(message, "Вы ввели некорректный выбор. Пожалуйста, выберите 'Орел' или 'Решка'.")


@bot.message_handler(func=lambda message: message.text == 'Играть')
def play_coin_flip(message):
    msg = bot.reply_to(message, "Выберите 'Орел' или 'Решка':")
    bot.register_next_step_handler(msg, process_coin_flip_choice)


def process_coin_flip_choice(message):
    choice = message.text.lower().strip()

    if choice in ['орел', 'решка']:
        msg = bot.reply_to(message, "Введите сумму вашей ставки:")
        bot.register_next_step_handler(msg, process_coin_flip_bet, choice)
    else:
        bot.reply_to(message, "Вы ввели некорректный выбор. Пожалуйста, выберите 'Орел' или 'Решка'.")


def process_coin_flip_bet(message, choice):
    import random

    bet_amount = message.text

    if bet_amount.isdigit():
        bet_amount = int(bet_amount)

        user_id = message.chat.id
        with lock:
            cursor.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()

        if result is not None:
            balance = result[0]

            if bet_amount > balance:
                bot.reply_to(message, "У вас недостаточно средств на балансе для совершения ставки.")
            else:
                coin = random.choice(['орел', 'решка'])

                if choice == coin:
                    with lock:
                        cursor.execute('UPDATE user_balances SET balance = balance + ? WHERE user_id = ?',
                                       (bet_amount, user_id))
                        conn.commit()

                    bot.reply_to(message,
                                 f"Вы выиграли! Результат: {coin}. Вам начислено {bet_amount * 2} монет.")
                else:
                    with lock:
                        cursor.execute('UPDATE user_balances SET balance = balance - ? WHERE user_id = ?',
                                       (bet_amount, user_id))
                        conn.commit()

                    bot.reply_to(message,
                                 f"Вы проиграли. Результат: {coin}. У вас списано {bet_amount} монет.")
        else:
            bot.reply_to(message, "Ваш баланс не найден. Возможно, вы не активировали промокод или не играли еще.")
    else:
        bot.reply_to(message, "Вы ввели некорректное значение. Пожалуйста, введите число.")


@bot.callback_query_handler(func=lambda call: True)
def handle_coin_flip_choice(call):
    choice = call.data
    process_coin_flip_choice(call.message, choice)


@bot.message_handler(func=lambda message: message.text == 'Запросить выигрыш')
def request_winnings(message):
    msg = bot.reply_to(message, "Введите сумму, которую вы хотите вывести:")
    bot.register_next_step_handler(msg, process_withdrawal_request)


def process_withdrawal_request(message):
    withdrawal_amount = message.text

    if withdrawal_amount.isdigit():
        withdrawal_amount = int(withdrawal_amount)

        user_id = message.chat.id
        with lock:
            cursor.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()

        if result is not None:
            balance = result[0]

            if withdrawal_amount <= balance:
                with lock:
                    cursor.execute('UPDATE user_balances SET balance = balance - ? WHERE user_id = ?',
                                   (withdrawal_amount, user_id))
                    conn.commit()

                withdrawal_info = f"Пользователь {message.chat.username} запрашивает вывод {withdrawal_amount} монет"
                bot.send_message(chat_id='@ruleto44', text=withdrawal_info)

                bot.reply_to(message,
                             f"Запрос на вывод суммы {withdrawal_amount} принят. Деньги будут отправлены")
            else:
                bot.reply_to(message, "Недостаточно средств на вашем балансе")
        else:
            bot.reply_to(message, "Ошибка получения информации о вашем балансе")
    else:
        bot.reply_to(message, "Пожалуйста, введите сумму в виде числа")


@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.reply_to(message, "Извините, я не понимаю ваш запрос. Пожалуйста, выберите один из пунктов главного меню.")


bot.polling(none_stop=True)
