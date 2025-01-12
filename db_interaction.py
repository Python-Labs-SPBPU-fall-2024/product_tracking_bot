import sqlite3
from datetime import datetime, date
import parser

# Адаптеры
def adapt_datetime_iso(val):
    return val.isoformat()

def adapt_date_iso(val):
    return val.isoformat()

# Конвертеры
def convert_datetime(val):
    return datetime.fromisoformat(val.decode())

def convert_date(val):
    return date.fromisoformat(val.decode())

# Регистрация адаптеров и конвертеров
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_adapter(date, adapt_date_iso)
sqlite3.register_converter("timestamp", convert_datetime)
sqlite3.register_converter("date", convert_date)


class DataBaseConnect:
    """
       Класс для работы с базой данных SQLite, включающий методы для создания таблиц, вставки данных и выполнения запросов.
    """

    # Поля сonn - соединение с бд.
    def __init__(self):
        self.conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.cursor = self.conn.cursor()
        print("Connection opened!")

    def __del__(self):
        self.conn.commit()
        self.conn.close()
        print("Connection closed!")

    def init_db(self) -> None:
        """
                Создает таблицы в базе данных, если они не существуют.
        """
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS User(
        User_id INTEGER   PRIMARY KEY,
        User_tg_name VARCHAR(32) NOT NULL)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS User_product(
        User_product_id INTEGER   PRIMARY KEY,
        User_in_id INT,
        Product_in_id INT,
        FOREIGN KEY (User_in_id) REFERENCES User (User_id),
        FOREIGN KEY (Product_in_id) REFERENCES Product (Product_sku))''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Product(
        Product_sku INT PRIMARY KEY NOT NULL)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Product_cost(
        Product_cost_id INTEGER PRIMARY KEY,
        Product_sku  INT NOT NULL,
        Date timestamp,
        Cost INT NOT NULL,
        FOREIGN KEY (Product_cost_id) REFERENCES Product (Product_sku))''')

        print("Tables created!")
        self.conn.commit()

    def get_all_product_for_user(self, user_tg_id) -> list:
        """
                Возвращает список всех продуктов, отслеживаемых пользователем.

                :param user_tg_id: Telegram ID пользователя.
                :return: Список продуктов.
        """
        self.cursor.execute('''SELECT Product_sku FROM User 
        Inner Join User_product 
            on User.User_id= User_product.User_in_id
        Inner Join Product
            on User_product.Product_in_id = Product.Product_sku
                where user_tg_name = ?''', (user_tg_id,))
        result = list(zip(*self.cursor.fetchall()))
        return result

    def start_tracking_for_user(self, user_tg_id, product_data: parser.PriceInfo):
        """
        Установка связи между продуктом и пользователем.
        Если пользователь или продукт не существуют, они добавляются в базу данных.

        :param user_tg_id: Telegram ID пользователя.
        :param product_data: Данные о продукте (объект PriceInfo).
        """
        # Проверка наличия пользователя
        self.cursor.execute('SELECT User_id FROM User WHERE User_tg_name = ?', (user_tg_id,))
        info_user = self.cursor.fetchone()
        print(info_user)
        if info_user is None:
            self.cursor.execute('INSERT INTO User (User_tg_name) VALUES (?)', (user_tg_id,))
            self.conn.commit()
            self.cursor.execute('SELECT User_id FROM User WHERE User_tg_name = ?', (user_tg_id,))
            info_user = self.cursor.fetchone()
        # Проверка наличия продукта
        self.cursor.execute('SELECT Product_sku FROM Product WHERE Product_sku = ?', (int(product_data.sku),))
        info_product = self.cursor.fetchone()
        if info_product is None:
            self.cursor.execute('INSERT INTO Product (Product_sku) VALUES (?)', (int(product_data.sku),))
            self.conn.commit()
            self.cursor.execute('SELECT Product_sku FROM Product WHERE Product_sku = ?', (int(product_data.sku),))
            info_product = self.cursor.fetchone()
        print(info_product)
        # Проверка наличия связи между пользователем и продуктом
        info_bind = self.cursor.execute('SELECT * FROM User_product WHERE Product_in_id = ? AND User_in_id = ?',
                            (info_product[0], info_user[0]))
        info_bind = self.cursor.fetchone()
        print(info_user[0], info_product[0])
        if info_bind is None:
            self.cursor.execute('INSERT INTO User_product (User_in_id, Product_in_id) VALUES (?, ?)',
                                (info_user[0], info_product[0]))
        print(info_bind)
        self.conn.commit()

    def insert_cost(self, product_data: parser.PriceInfo):
        """
           Вставляет данные о стоимости продукта в таблицу Product_cost.

           :param product_data: Данные о продукте (объект PriceInfo).
        """
        try:
            # Проверка на None
            if product_data.sku is None or product_data.price is None or product_data.time is None:
                print("Одно или несколько значений отсутствуют!")
                return
            print(product_data.time)
            self.cursor.execute('INSERT INTO Product_cost ( Product_sku, Date, Cost) VALUES (?, ?, ?)',
                 (int(product_data.sku), product_data.time, product_data.price))

            self.conn.commit()  # Коммит транзакции
        except sqlite3.OperationalError:
            print("Такой таблицы не существует!")
            return
        finally: self.conn.commit()

    def delete_data(self):
        """
            Заглушка для метода удаления данных. Не реализован
        """
        pass

    def drop_tables(self):
        """
            Удаляет все таблицы из базы данных.
        """
        self.cursor.execute('''DROP TABLE User''')
        self.cursor.execute('''DROP TABLE User_product''')
        self.cursor.execute('''DROP TABLE Product''')
        self.cursor.execute('''DROP TABLE Product_cost''')
        print("Tables Dropped!")

    def get_cost_by_sku(self, sku):
        """
            Возвращает данные о стоимости продукта по его арткулу.

            :param sku: Артикул продукта.
            :return: Данные о стоимости продукта.
        """
        try:
            self.cursor.execute("SELECT * FROM Product_cost where Product_sku = ?", (int(sku),))
        except sqlite3.OperationalError:
            print("Такой таблицы не существует!")
            return
        result = self.cursor.fetchall()
        print("Получил!:", result)
        return result


