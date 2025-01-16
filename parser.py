import re
from datetime import datetime
from typing import Optional, NamedTuple
import requests


class PriceInfo(NamedTuple):
    """
    Класс для хранения информации о цене товара.

    Attributes:
        sku (Optional[str]): Артикул товара.
        price (Optional[int]): Цена товара в рублях.
        time (Optional[datetime]): Время запроса цены.
    """
    sku: Optional[str]
    price: Optional[int]
    time: Optional[datetime]


class PriceParser:
    """
    Класс для парсинга цены товара с сайта Wildberries.

    Attributes:
        url (str): URL товара на Wildberries.
        sku (Optional[str]): Артикул товара.
        time (Optional[datetime]): Время запроса цены.
        price (Optional[int]): Цена товара в рублях.
    """

    def __init__(self, url: str) -> None:
        """
        Инициализация PriceParser.

        Args:
            url (str): URL товара на Wildberries.
        """
        # Удаляем строку запроса из url
        self.url = url.split('?')[0]
        self.sku = None
        self.time = None
        self.price = None

    def _extract_sku(self) -> None:
        """
        Извлечение артикул (SKU) товара из URL.

        Raises:
            ValueError: Если формат URL неверный.
        """
        # Регулярное выражение для проверки формата URL
        reg_exp = r'^https://(www\.)?wildberries\.ru/catalog/(\d{8,12})/detail\.aspx$'
        match = re.match(reg_exp, self.url)

        if match:
            # Извлекаем SKU из второй группы
            self.sku = match.group(2)
            # Формируем API URL для запроса цены
            self.url = f'https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-115106&spp=0&nm={self.sku}'
        else:
            raise ValueError(f'Неверный формат URL: {self.url}')

    def parse_price(self) -> Optional[PriceInfo]:
        """
        Парсинг цены товара.

        Returns:
            Optional[PriceInfo]: Объект PriceInfo с информацией о цене,
            или None в случае ошибки.

        Raises:
            ValueError: Если цена товара не найдена.
        """
        try:
            # Извлекаем SKU из URL
            self._extract_sku()
            self.time = datetime.now().replace(microsecond=0)

            # Выполняем GET-запрос для получения данных о товаре
            response = requests.get(self.url)
            response.raise_for_status()  # Проверяем на наличие ошибок в ответе

            # Извлекаем цену из JSON-ответа
            self.price = response.json().get('data', {}).get('products', [{}])[0].get('salePriceU', -1) // 100

            if self.price == -1:
                raise ValueError('Ошибка: не найдена цена товара!')

            # Возвращаем информацию о цене
            return PriceInfo(sku=self.sku, price=self.price, time=self.time)

        except ValueError as e:
            print(f'{e}')
        except requests.exceptions.RequestException as e:
            print(f'Ошибка при выполнении запроса: {e}')
        except (IndexError, KeyError):
            print('Ошибка: не удалось получить данные о продукте.')
        except Exception as e:
            print(f'Непредвиденная ошибка: {e}')

        return None

