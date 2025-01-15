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

class DBInteractionExept(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return "DB interaction has problem: " ++ self.message


class DataBaseConnect:
    """
       Класс для работы с базой данных SQLite, включающий методы для создания таблиц, вставки данных и выполнения запросов.
    """

    def init_db(self) -> None:
        """
            Создает таблицы в базе данных, если они не существуют.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS User(
        User_id INTEGER PRIMARY KEY,
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


    def get_all_product_for_user(self, user_tg_id) -> list:
        """
               Возвращает список всех продуктов, отслеживаемых пользователем.

               :param user_tg_id: Telegram ID пользователя.
               :type user_tg_id: str
               :return: Список продуктов.
               :rtype: list
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''SELECT Product_sku FROM User 
        Inner Join User_product 
            on User.User_id= User_product.User_in_id
        Inner Join Product
            on User_product.Product_in_id = Product.Product_sku
                where user_tg_name = ?''', (user_tg_id,))
        result = list(map(lambda x: x[0], cursor.fetchall()))
        print(result)
        conn.commit()
        conn.close()

        return result

    def start_tracking_for_user(self, user_tg_id, product_data: parser.PriceInfo):
        """
            Устанавливает связь между продуктом и пользователем.
            Если пользователь или продукт не существуют, они добавляются в базу данных.

            :param user_tg_id: Telegram ID пользователя.
            :type user_tg_id: str
            :param product_data: Данные о продукте (объект PriceInfo).
            :type product_data: parser.PriceInfo
            :return: None
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        # Проверка наличия пользователя
        cursor.execute('SELECT User_id FROM User WHERE User_tg_name = ?', (user_tg_id,))
        info_user = cursor.fetchone()

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

        # Проверка наличия связи между пользователем и продуктом
        info_bind = cursor.execute('SELECT * FROM User_product WHERE Product_in_id = ? AND User_in_id = ?',
                            (info_product[0], info_user[0]))
        info_bind = cursor.fetchone()

        if info_bind is None:
            cursor.execute('INSERT INTO User_product (User_in_id, Product_in_id) VALUES (?, ?)',
                                (info_user[0], info_product[0]))

        conn.commit()
        conn.close()


    def insert_cost(self, product_data: parser.PriceInfo):
        """
        Вставляет данные о стоимости продукта в таблицу Product_cost.

        :param product_data: Данные о продукте (объект PriceInfo).
        :type product_data: parser.PriceInfo
        :return: None
        """


        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        try:
            # Проверка на None
            if product_data.sku is None or product_data.price is None or product_data.time is None:
                print("Одно или несколько значений отсутствуют!")
                return
            #print(product_data.time)
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

    def delete_data(self, user_tg_id, product_data: parser.PriceInfo):
        """
            Удаляет продукт для данного пользователя из базы данных. Если данный продукт отслеживал только
            один пользователь, то продукт удаляется из базы данных насовсем.

            :param user_tg_id: Идентификатор пользователя в Telegram.
            :type user_tg_id: str
            :param product_data: Объект, содержащий информацию о продукте.
            :type product_data: parser.PriceInfo
            :raises DBInteractionExept: Если продукт не отслеживается данным пользователем.
            :return: None
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        # Проверка 1. Смотрим на то отлеживает ли наш пользовтель этот товар
        if int(product_data.sku) not in self.get_all_product_for_user(user_tg_id):
            raise DBInteractionExept("No product for such user")
        else:
            cursor.execute('SELECT COUNT(*) FROM User'
                           ' inner join user_product on user_id = user_product.user_in_id'
                           ' inner join product on user_product.product_in_id = product_sku'
                           ' where Product_sku = ?', (int(product_data.sku),))
            res = cursor.fetchone()
            # Проверка 2. Смотрим на то, сколько пользовтелей отслеживает данный товар
            if (res[0] == 1):
                # Если только один, который и хочет удалить данный товар, то очиащем полностью

                # Удалили из таблицы связей
                cursor.execute('DELETE FROM  User_product where Product_in_id = ?', (int(product_data.sku),))
                # Удалили из таблицы продуктов
                cursor.execute('DELETE FROM  Product where Product_sku = ?', (int(product_data.sku),))
                # Удалили из таблицы цен
                cursor.execute('DELETE FROM  Product_cost where Product_sku = ?', (int(product_data.sku),))
            else:
                # Если еще несколько, то оставляем основые записи, удаляем только строки связывающей таблицы.
                cursor.execute('DELETE FROM  User_product where Product_in_id = ? and User_in_id = (select User_id from '
                               'User where User_tg_name = ?)', (int(product_data.sku),user_tg_id))
        conn.commit()
        conn.close()

    def drop_tables(self):
        """
            Удаляет все таблицы из базы данных.
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        cursor.execute('''DROP TABLE IF EXISTS User''')
        cursor.execute('''DROP TABLE IF EXISTS User_product''')
        cursor.execute('''DROP TABLE IF EXISTS Product''')
        cursor.execute('''DROP TABLE IF EXISTS Product_cost''')

        conn.commit()
        conn.close()

    def get_cost_by_sku(self, sku):
        """
               Возвращает данные о стоимости продукта по его артикулу.

               :param sku: Артикул продукта.
               :type sku: int
               :return: Данные о стоимости продукта.
               :rtype: list
        """
        conn = sqlite3.connect('purchases.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM Product_cost where Product_sku = ?", (int(sku),))
        except sqlite3.OperationalError:
            print("Такой таблицы не существует!")
            return
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result