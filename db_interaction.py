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
    def create_connection(self):
        self.conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.cursor = self.conn.cursor()
        print("Connection opened!")


    def init_db(self) -> None:
        """
                Создает таблицы в базе данных, если они не существуют.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS User(
        User_id INTEGER   PRIMARY KEY,
        User_tg_name VARCHAR(32) NOT NULL)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS User_product(
        User_product_id INTEGER   PRIMARY KEY,
        User_in_id INT,
        Product_in_id INT,
        FOREIGN KEY (User_in_id) REFERENCES User (User_id),
        FOREIGN KEY (Product_in_id) REFERENCES Product (Product_sku))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS Product(
        Product_sku INT PRIMARY KEY NOT NULL)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS Product_cost(
        Product_cost_id INTEGER PRIMARY KEY,
        Product_sku  INT NOT NULL,
        Date timestamp,
        Cost INT NOT NULL,
        FOREIGN KEY (Product_cost_id) REFERENCES Product (Product_sku))''')

        conn.commit()
        conn.close()
        print("Tables created!")
        print("Connection closed!")

    def get_all_product_for_user(self, user_tg_id) -> list:
        """
                Возвращает список всех продуктов, отслеживаемых пользователем.

                :param user_tg_id: Telegram ID пользователя.
                :return: Список продуктов.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''SELECT Product_sku FROM User 
        Inner Join User_product 
            on User.User_id= User_product.User_in_id
        Inner Join Product
            on User_product.Product_in_id = Product.Product_sku
                where user_tg_name = ?''', (user_tg_id,))
        result = list(zip(*cursor.fetchall()))
        conn.commit()
        conn.close()
        return result

    def start_tracking_for_user(self, user_tg_id, product_data: parser.PriceInfo):
        """
        Установка связи между продуктом и пользователем.
        Если пользователь или продукт не существуют, они добавляются в базу данных.

        :param user_tg_id: Telegram ID пользователя.
        :param product_data: Данные о продукте (объект PriceInfo).
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        # Проверка наличия пользователя
        cursor.execute('SELECT User_id FROM User WHERE User_tg_name = ?', (user_tg_id,))
        info_user = cursor.fetchone()
        print(info_user)
        if info_user is None:
            cursor.execute('INSERT INTO User (User_tg_name) VALUES (?)', (user_tg_id,))
            conn.commit()
            cursor.execute('SELECT User_id FROM User WHERE User_tg_name = ?', (user_tg_id,))
            info_user = cursor.fetchone()
        # Проверка наличия продукта
        cursor.execute('SELECT Product_sku FROM Product WHERE Product_sku = ?', (int(product_data.sku),))
        info_product = cursor.fetchone()
        if info_product is None:
            cursor.execute('INSERT INTO Product (Product_sku) VALUES (?)', (int(product_data.sku),))
            conn.commit()
            cursor.execute('SELECT Product_sku FROM Product WHERE Product_sku = ?', (int(product_data.sku),))
            info_product = cursor.fetchone()
        print(info_product)
        # Проверка наличия связи между пользователем и продуктом
        info_bind = cursor.execute('SELECT * FROM User_product WHERE Product_in_id = ? AND User_in_id = ?',
                            (info_product[0], info_user[0]))
        info_bind = cursor.fetchone()
        print(info_user[0], info_product[0])
        if info_bind is None:
            cursor.execute('INSERT INTO User_product (User_in_id, Product_in_id) VALUES (?, ?)',
                                (info_user[0], info_product[0]))
        print(info_bind)
        conn.commit()
        conn.close()


    def insert_cost(self, product_data: parser.PriceInfo):
        """
           Вставляет данные о стоимости продукта в таблицу Product_cost.

           :param product_data: Данные о продукте (объект PriceInfo).
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        try:
            # Проверка на None
            if product_data.sku is None or product_data.price is None or product_data.time is None:
                print("Одно или несколько значений отсутствуют!")
                return
            print(product_data.time)
            cursor.execute('INSERT INTO Product_cost ( Product_sku, Date, Cost) VALUES (?, ?, ?)',
                 (int(product_data.sku), product_data.time, product_data.price))

            conn.commit()  # Коммит транзакции
            conn.close()
        except sqlite3.OperationalError:
            print("Такой таблицы не существует!")
            return
        finally:
            conn.commit()
            conn.close()

    def delete_data(self):
        """
            Заглушка для метода удаления данных. Не реализован
        """
        pass

    def drop_tables(self):
        """
            Удаляет все таблицы из базы данных.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''DROP TABLE User''')
        cursor.execute('''DROP TABLE User_product''')
        cursor.execute('''DROP TABLE Product''')
        cursor.execute('''DROP TABLE Product_cost''')
        print("Tables Dropped!")

        conn.commit()
        conn.close()

    def get_cost_by_sku(self, sku):
        """
            Возвращает данные о стоимости продукта по его арткулу.

            :param sku: Артикул продукта.
            :return: Данные о стоимости продукта.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Product_cost where Product_sku = ?", (int(sku),))
        except sqlite3.OperationalError:
            print("Такой таблицы не существует!")
            return
        result = cursor.fetchall()
        print("Получил!:", result)
        conn.commit()
        conn.close()
        return result


