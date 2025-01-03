import re
from datetime import datetime
from typing import Optional, NamedTuple
import requests


class PriceInfo(NamedTuple):
    sku: Optional[str]
    price: Optional[int]
    time: Optional[datetime]


class PriceParser:
    def __init__(self, url: str) -> None:
        self.url = url
        self.sku = None
        self.time = None
        self.price = None

    def _extract_sku(self) -> None:
        reg_exp = r'^https://www\.wildberries\.ru/catalog/(\d{8,12})/detail\.aspx$'
        match = re.match(reg_exp, self.url)
        if match:
            self.sku = match.group(1)
            self.url = f'https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-115106&spp=0&nm={self.sku}'
        else:
            raise ValueError(f'Неверный формат URL: {self.url}')

    def parse_price(self) -> Optional[PriceInfo]:
        try:
            self._extract_sku()
            self.time = datetime.now().replace(microsecond=0)
            response = requests.get(self.url)
            response.raise_for_status()
            self.price = response.json().get('data', {}).get('products', [{}])[0].get('salePriceU', -1) // 100
            
            if self.price == -1:
                raise ValueError('Ошибка: не найдена цена товара!')
                
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
