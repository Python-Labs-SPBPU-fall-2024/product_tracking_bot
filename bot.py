
import asyncio
import time
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import aiohttp
import sys
import os
from typing import Dict, List
import db_interaction

from datetime import datetime, timedelta
from collections import OrderedDict
import parser


######################################################
API_TOKEN = '7913942098:AAHXAlrBleOpFjPv3mq4gcSD68jkmvaFPAc'  # Замените на ваш токен
bot = AsyncTeleBot(API_TOKEN)
######################################################


# Состояние отслеживания для каждого пользователя (товары)
tracking_states = {}
# Очередь товаров для отслеживания
tracking_queue: Dict[int, List[dict]] = {}  # {chat_id: [{id:1, name: "...", sku:"..."}, {}]}
# Словарь для ожидания ссылок
waiting_for_links = {}

# Максимальное количество товаров
MAX_ITEMS = 5

# Словарь для хранения ожидаемых названий
waiting_for_name = {}

# Словарь для ожидания количества дней
waiting_for_days = {}

#база данных
db = db_interaction.DataBaseConnect()
db.init_db()


# Функция для извлечения артикула из ссылки
def extract_article_from_link(link):
    try:
        parser_obj = parser.PriceParser(link)
        price_info = parser_obj.parse_price()
        if price_info:
            return price_info.sku
        return None
    except Exception as e:
        print(f"Error extracting article: {e}")
        return None




@bot.message_handler(commands=['start'])
async def handle_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Начать отслеживание")
    markup.add(item1)
    await bot.send_message(message.chat.id,
                           'Привет! Я бот, который поможет тебе отслеживать цену на товары с Wb! Для того, чтобы начать отслеживание нажмите кнопку ниже.',
                           reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Начать отслеживание")
async def handle_otslegivanie_button(message):
    waiting_for_links[message.chat.id] = True
    # Убираем кнопку "Начать отслеживание", отправляя клавиатуру без кнопок
    markup = types.ReplyKeyboardRemove()
    await bot.send_message(message.chat.id,
                           "Отлично! Теперь, пожалуйста, пришлите список ссылок на товары (не более 5), которые вы хотите отслеживать (каждая ссылка с новой строки).",
                           reply_markup=markup)


async def track_prices(chat_id: int):
    while True:  # Keep it running until tracking_queue[chat_id] is empty or some stop condition
        if tracking_states.get(chat_id, False) and chat_id in tracking_queue:
            for item in tracking_queue[chat_id]:
                parser_obj = parser.PriceParser(f'https://www.wildberries.ru/catalog/{item["sku"]}/detail.aspx')
                price_info = parser_obj.parse_price()

                if price_info:
                    db.insert_cost(price_info)
                else:
                    await bot.send_message(chat_id, f"Не удалось получить цену для товара {item['name']}")
        else:
            print(f"Отслеживание цен для пользователя {chat_id} остановлено.")
            break
        print(f"Обновление цен для пользователя {chat_id} завершено. Пауза на 24 часа.")
        await asyncio.sleep(24*60*60)

@bot.message_handler(func=lambda message: message.chat.id in waiting_for_links and waiting_for_links[message.chat.id])
async def handle_links_input(message):
    try:
        chat_id = message.chat.id
        if chat_id not in tracking_queue:
            tracking_queue[chat_id] = []

        links = message.text.splitlines()
        links = list(OrderedDict.fromkeys([link.strip() for link in links]))

        added_count = 0
        if len(links) > MAX_ITEMS:
            await bot.send_message(chat_id,
                                   f"Вы ввели более {MAX_ITEMS} ссылок. Будут добавлены только первые {MAX_ITEMS} товаров.")
            links = links[:MAX_ITEMS]

        for link in links:  # Iterating in the order of user input
            article = extract_article_from_link(link.strip())
            if article and article.isdigit():
                if not any(item['sku'] == article for item in tracking_queue[chat_id]):
                    if len(tracking_queue[chat_id]) < MAX_ITEMS:
                        item_id = len(tracking_queue[chat_id]) + 1
                        for item in tracking_queue[chat_id]:
                            if (item_id == item["id"]):
                                item_id += 1
                        tracking_queue[chat_id].append({"id": item_id, "sku": article, "name": f"Товар {item_id}"})
                        added_count += 1
                        tracking_states[chat_id] = True
                        parser_obj = parser.PriceParser(link)
                        price_info = parser_obj.parse_price()
                        if price_info:
                            db.start_tracking_for_user(str(chat_id), price_info)
                    else:
                        await bot.send_message(chat_id,
                                               f"Достигнуто максимальное количество товаров ({MAX_ITEMS}). Пропускаем {link}")
                else:
                    await bot.send_message(chat_id, f"Ссылка {link} уже добавлена.")
            else:
                await bot.send_message(chat_id, f"Не удалось извлечь артикул из {link}, проверьте корректность ссылки.")

        del waiting_for_links[chat_id]

        if added_count > 0 or len(tracking_queue[chat_id]) == 5:
             asyncio.create_task(track_prices(chat_id)) # Launch tracking
             markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
             item1 = types.KeyboardButton("Прекратить отслеживание")
             item2 = types.KeyboardButton("Получить цену сейчас")
             item3 = types.KeyboardButton("Получить цену за все время")
             item4 = types.KeyboardButton("Добавить еще ссылки")
             item5 = types.KeyboardButton("Изменить название товара")
             markup.add(item1, item2, item3, item4, item5)
             await bot.send_message(chat_id, f"Отслеживание запущено для {added_count} товаров. Что вы хотите сделать?",
                                   reply_markup=markup)
        else:
            await bot.send_message(chat_id,
                                   "Ни один товар не был добавлен. Проверьте список ссылок и попробуйте еще раз.")
            waiting_for_links[chat_id] = True
            markup = types.ReplyKeyboardRemove()
            await bot.send_message(chat_id,
                                   "Пожалуйста, пришлите список ссылок на товары, которые вы хотите отслеживать (каждая ссылка с новой строки).",
                                   reply_markup=markup)
    except Exception as e:
        print(f"Error in handle_links_input: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Изменить название товара")
async def handle_change_name_button(message):
    try:
        chat_id = message.chat.id
        if tracking_states.get(chat_id, False) and chat_id in tracking_queue and tracking_queue[chat_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for item in tracking_queue[chat_id]:
                markup.add(types.KeyboardButton(f"Сменить {item['name']}"))
            markup.add(types.KeyboardButton("Назад в главное меню"))
            await bot.send_message(chat_id, "Выберите товар для изменения названия:", reply_markup=markup)
        else:
            await bot.send_message(chat_id, "Сначала нужно запустить отслеживание и ввести артикул.")
    except Exception as e:
        print(f"Error in handle_change_name_button: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")
@bot.message_handler(func=lambda message: message.text == "Назад в главное меню")
async def handle_back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Прекратить отслеживание")
    item2 = types.KeyboardButton("Получить цену сейчас")
    item3 = types.KeyboardButton("Получить цену за период")
    item4 = types.KeyboardButton("Добавить еще ссылки")
    item5 = types.KeyboardButton("Изменить название товара")
    markup.add(item1, item2, item3, item4, item5)
    await bot.send_message(message.chat.id, "Что вы хотите сделать?", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.startswith("Сменить "))
async def handle_change_item_name(message):
    try:
        chat_id = message.chat.id
        item_name_to_change = message.text.replace("Сменить ", "")

        if chat_id in tracking_queue:
            for item in tracking_queue[chat_id]:
                if item['name'] == item_name_to_change:
                    waiting_for_name[chat_id] = item['id']
                    await bot.send_message(chat_id, f"Введите новое название для {item_name_to_change}:",
                                           reply_markup=types.ReplyKeyboardRemove())
                    return
        await bot.send_message(chat_id, "Товар не найден в списке отслеживания.")

    except Exception as e:
        print(f"Error in handle_change_item_name: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.chat.id in waiting_for_name)
async def handle_new_name_input(message):
    try:
        chat_id = message.chat.id
        item_id = waiting_for_name.get(chat_id)

        if item_id and chat_id in tracking_queue:
            for item in tracking_queue[chat_id]:
                if item['id'] == item_id:
                    item['name'] = message.text
                    await bot.send_message(chat_id, f"Название товара успешно изменено на {message.text}")
                    del waiting_for_name[chat_id]  # Очищаем ожидание имени
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton("Прекратить отслеживание")
                    item2 = types.KeyboardButton("Получить цену сейчас")
                    item3 = types.KeyboardButton("Получить цену за период")
                    item4 = types.KeyboardButton("Добавить еще ссылки")
                    item5 = types.KeyboardButton("Изменить название товара")
                    markup.add(item1, item2, item3, item4, item5)
                    await bot.send_message(chat_id, f"Что вы хотите сделать?", reply_markup=markup)
                    return
            await bot.send_message(chat_id, "Товар не найден в списке отслеживания.")
        else:
            await bot.send_message(chat_id, "Произошла ошибка.")

    except Exception as e:
        print(f"Error in handle_new_name_input: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Добавить еще ссылки")
async def handle_add_links_button(message):
    try:
        if tracking_states.get(message.chat.id, False):
            waiting_for_links[message.chat.id] = True
            markup = types.ReplyKeyboardRemove()
            await bot.send_message(message.chat.id, "Пришлите список новых ссылок:", reply_markup=markup)
        else:
            await bot.send_message(message.chat.id, "Сначала нужно запустить отслеживание.")
    except Exception as e:
        print(f"Error in handle_add_links_button: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Прекратить отслеживание")
async def handle_stop_tracking_button(message):
    try:
        chat_id = message.chat.id
        if chat_id in tracking_queue and tracking_queue[chat_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for item in tracking_queue[chat_id]:
                markup.add(types.KeyboardButton(f"Отменить {item['name']}"))
            markup.add(types.KeyboardButton("Удалить все"))
            markup.add(types.KeyboardButton("Назад в главное меню"))
            await bot.send_message(chat_id, "Выберите какой товар отменить или отмените все", reply_markup=markup)

        else:
            tracking_states[message.chat.id] = False

            if message.chat.id in tracking_queue:
                del tracking_queue[message.chat.id]

            # Очищаем базу данных



            await bot.send_message(message.chat.id, "Отслеживание остановлено для всех товаров!")
            # Возвращаем пользователя в начало
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Начать отслеживание")
            markup.add(item1)
            await bot.send_message(message.chat.id, "Для начала нового отслеживания нажмите кнопку ниже:",
                                   reply_markup=markup)
    except Exception as e:
        print(f"Error in handle_stop_tracking_button: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text.startswith("Отменить "))
async def handle_stop_specific_item(message):
    try:
        chat_id = message.chat.id
        if chat_id in tracking_queue:
            item_name_to_remove = message.text.replace("Отменить ", "")
            for item in tracking_queue[chat_id]:
                if item['name'] == item_name_to_remove:
                    parser_obj = parser.PriceParser(f'https://www.wildberries.ru/catalog/{item["sku"]}/detail.aspx')
                    price_info = parser_obj.parse_price()
                    db.delete_data(str(chat_id), price_info)
                    tracking_queue[chat_id].remove(item)

                    await bot.send_message(chat_id, f"Отслеживание товара {item_name_to_remove} остановлено.")

                    if not tracking_queue[chat_id]:
                        tracking_states[chat_id] = False
                        del tracking_queue[chat_id]
                        await bot.send_message(message.chat.id, "Список отслеживания пуст.")

                        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                        item1 = types.KeyboardButton("Начать отслеживание")
                        markup.add(item1)
                        await bot.send_message(message.chat.id, "Для начала нового отслеживания нажмите кнопку ниже:",
                                               reply_markup=markup)
                    else:
                        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                        item1 = types.KeyboardButton("Прекратить отслеживание")
                        item2 = types.KeyboardButton("Получить цену сейчас")
                        item3 = types.KeyboardButton("Получить цену за период")
                        item4 = types.KeyboardButton("Добавить еще ссылки")
                        item5 = types.KeyboardButton("Изменить название товара")
                        markup.add(item1, item2, item3, item4, item5)
                        await bot.send_message(message.chat.id, f"Что вы хотите сделать?", reply_markup=markup)
                    return
            await bot.send_message(chat_id, "Товар не найден в списке отслеживания.")

    except Exception as e:
        print(f"Error in handle_stop_specific_item: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Удалить все")
async def handle_stop_all_tracking(message):
    try:
        chat_id = message.chat.id
        tracking_states[chat_id] = False

        for item in tracking_queue[chat_id]:
            parser_obj = parser.PriceParser(f'https://www.wildberries.ru/catalog/{item["sku"]}/detail.aspx')
            price_info = parser_obj.parse_price()
            db.delete_data(str(chat_id), price_info)


        if chat_id in tracking_queue:
            del tracking_queue[chat_id]
        # Очищаем базу данных

        await bot.send_message(message.chat.id, "Отслеживание всех товаров остановлено!")
        # Возвращаем пользователя в начало
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Начать отслеживание")
        markup.add(item1)
        await bot.send_message(message.chat.id, "Для начала нового отслеживания нажмите кнопку ниже:",
                               reply_markup=markup)
    except Exception as e:
        print(f"Error in handle_stop_all_tracking: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Получить цену сейчас")
async def handle_get_current_price_button(message):
    try:
        chat_id = message.chat.id
        if tracking_states.get(chat_id, False) and chat_id in tracking_queue and tracking_queue[chat_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for item in tracking_queue[chat_id]:
                markup.add(types.KeyboardButton(f"Цена сейчас {item['name']}"))
            markup.add(types.KeyboardButton("Назад в главное меню"))
            await bot.send_message(chat_id, "Выберите товар для получения цены:", reply_markup=markup)
        else:
            await bot.send_message(chat_id, "Сначала нужно запустить отслеживание и ввести артикул.")
    except Exception as e:
        print(f"Error in handle_get_current_price_button: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text.startswith("Цена сейчас "))
async def handle_get_current_price(message):
    try:
        chat_id = message.chat.id
        item_name = message.text.replace("Цена сейчас ", "")
        if tracking_states.get(chat_id, False) and chat_id in tracking_queue:
            for item in tracking_queue[chat_id]:
                if item['name'] == item_name:
                    parser_obj = parser.PriceParser(f'https://www.wildberries.ru/catalog/{item["sku"]}/detail.aspx')
                    price_info = parser_obj.parse_price()

                    if price_info:
                        db.insert_cost(price_info)
                        await bot.send_message(chat_id, f"Текущая цена товара {item['name']}: {price_info.price}")
                    else:
                        await bot.send_message(chat_id, f"Не удалось получить цену для товара {item['name']}")

                    # Возвращаемся в меню
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton("Прекратить отслеживание")
                    item2 = types.KeyboardButton("Получить цену сейчас")
                    item3 = types.KeyboardButton("Получить цену за период")
                    item4 = types.KeyboardButton("Добавить еще ссылки")
                    item5 = types.KeyboardButton("Изменить название товара")
                    markup.add(item1, item2, item3, item4, item5)
                    await bot.send_message(chat_id, "Что вы хотите сделать?", reply_markup=markup)

                    return
        await bot.send_message(chat_id, "Сначала нужно запустить отслеживание и ввести артикул.")
    except Exception as e:
        print(f"Error in handle_get_current_price: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == "Получить цену за период")
async def handle_get_all_time_price_button(message):
    try:
        chat_id = message.chat.id
        if tracking_states.get(chat_id, False) and chat_id in tracking_queue and tracking_queue[chat_id]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for item in tracking_queue[chat_id]:
                markup.add(types.KeyboardButton(f"Цена за период {item['name']}"))
            markup.add(types.KeyboardButton("Назад в главное меню"))
            await bot.send_message(chat_id, "Выберите товар для получения цены:", reply_markup=markup)
        else:
            await bot.send_message(chat_id, "Сначала нужно запустить отслеживание и ввести артикул.")
    except Exception as e:
        print(f"Error in handle_get_all_time_price_button: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")



@bot.message_handler(func=lambda message: message.text.startswith("Цена за период "))
async def handle_get_all_time_price(message):
    try:
        chat_id = message.chat.id
        item_name = message.text.replace("Цена за период ", "")

        if tracking_states.get(chat_id, False) and chat_id in tracking_queue:
            for item in tracking_queue[chat_id]:
                if item['name'] == item_name:
                    waiting_for_days[chat_id] = item['sku']
                    await bot.send_message(chat_id, "Введите количество дней за которые вы хотите получить цену:", reply_markup=types.ReplyKeyboardRemove())
                    return
            await bot.send_message(chat_id, "Товар не найден в списке отслеживания.")
        else:
            await bot.send_message(chat_id, "Сначала нужно запустить отслеживание и ввести артикул.")
    except Exception as e:
        print(f"Error in handle_get_all_time_price: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")

@bot.message_handler(func=lambda message: message.chat.id in waiting_for_days)
async def handle_days_input(message):
    try:
        chat_id = message.chat.id
        sku = waiting_for_days.get(chat_id)
        days = message.text

        if not days.isdigit():
            await bot.send_message(chat_id, "Пожалуйста, введите корректное число дней (целое число).")
            return
        days = int(days)
        if days < 1:
             await bot.send_message(chat_id, "Пожалуйста, введите число не меньше 0.")
             return
        days = days-1
        prices = db.get_cost_by_sku(sku)
        print(prices)  # Добавлено для отладки
        if prices:
            first_date = prices[0][2].date()  # Get the first date from the list as date object
            time_diff = datetime.now().date() - first_date  # Get the time difference as days
            time_diff_days = time_diff.days


            if time_diff_days < days:
                if first_date:
                    await bot.send_message(chat_id,
                                           f"Нет данных о ценах для товара {sku} за последние {days} дней. Информация собрана за {time_diff_days + 1} дней.")
                else:
                    await bot.send_message(chat_id, f"Нет данных о ценах для товара {sku}.")
            else:
                  if days == 0:
                      filtered_prices = [p for p in prices if p[2].date() == datetime.now().date()]
                  else:
                      cutoff_date = datetime.now() - timedelta(days=days)
                      filtered_prices = [p for p in prices if p[2].date() >= cutoff_date.date()]

                  if filtered_prices:
                      price_str = "\n".join(
                          [f"{p[3]} - {datetime.strftime(p[2], '%Y-%m-%d %H:%M')}" for p in filtered_prices])
                      await bot.send_message(chat_id,
                                             f"История цен для товара {sku} за последние {days} дней:\n{price_str}")
                  else:
                      await bot.send_message(chat_id,
                                             f"Нет данных о ценах для товара {sku} за последние {days} дней.")

        else:
                await bot.send_message(chat_id, f"Нет данных о ценах для товара {sku}.")
        del waiting_for_days[chat_id]
            # Возвращаемся в меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Прекратить отслеживание")
        item2 = types.KeyboardButton("Получить цену сейчас")
        item3 = types.KeyboardButton("Получить цену за период")
        item4 = types.KeyboardButton("Добавить еще ссылки")
        item5 = types.KeyboardButton("Изменить название товара")
        markup.add(item1, item2, item3, item4, item5)
        await bot.send_message(chat_id, "Что вы хотите сделать?", reply_markup=markup)

    except Exception as e:
        print(f"Error in handle_days_input: {e}")
        await bot.send_message(message.chat.id,
                               "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


async def main():
    await bot.polling(none_stop=True)


if __name__ == '__main__':
    asyncio.run(main())
