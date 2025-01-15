# Лабораторная работа №4 (Вариант 1)

## Проект: Телеграм-бот для отслеживания цен на товары с Wildberries

### Описание проекта
Данный проект представляет собой телеграм-бота, который предоставляет пользователям информацию о текущей цене любого товара с маркетплейса Wildberries по предоставленной ссылке. Бот также позволяет пользователям получать историю изменения цен на товары за определённый период (n дней).

### Использованные технологии

Для парсинга информации, решение использует requests, библиотека для выполнения HTTP-запросов. А также библиотеки для работы с JSON-файлами,которые являются форматом данных, используемым для обмена информацией с API Wildberries.

В работе бот использует встроенную СУБД SQLite для хранения данных, о ценах товаров, и информации о пользователях и тех товаров, которые они отслеживают.

### Установка и запуск
```bash
git clone <https://github.com/Python-Labs-SPBPU-fall-2024/product_tracking_bot.git>
cd <product_tracking_bot>
pip install -r requirements.txt
```
#### Конфигурация 
Перед запуском бота необходимо создать файл config.py и указать в нем токен вашего бота, полученный от BotFather в Telegram
```bash
# config.py
token = "YOUR_BOT_TOKEN_HERE"
```


### Реализуемые функции
1. **Телеграм-бот**: Основной интерфейс взаимодействия с пользователем.
2. **Парсинг информации**: Извлечение данных о товарах и их ценах с сайта Wildberries.
3. **Хранение данных в базе**: Сохранение информации о товарах и их ценах для дальнейшего анализа и предоставления истории изменений.

### Структура проекта
- parser.py --- функции парсинга данных о товаре с сайта Wildberries. Необходимые структуры данных для обмена информацией между модулями телеграмм-бота
- db_interaction  --- класс, подключения к базе данных, инкапсулирующий методы записи, чтения и удаления данных в базе, хронящие данные о пользователях и товарах

### Описание коммитов
| Название  | Описание                                                                 |
|-----------|--------------------------------------------------------------------------|
| `docs`    | Обновление документации проекта, включая инструкции по установке и использованию. |
| `feat`    | Добавление нового функционала, например, возможность получения истории цен. |
| `fix`     | Исправление ошибок, найденных в коде или в работе бота.                 |
| `refactor`| Оптимизация и улучшение кода без изменения его функциональности.         |
| `revert`  | Откат изменений на предыдущую стабильную версию.                        |
| `style`   | Исправления по кодстайлу, включая форматирование, отступы и другие стилистические правки. |
