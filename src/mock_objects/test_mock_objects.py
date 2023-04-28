import os
import sqlite3
from unittest import mock
from unittest.mock import MagicMock

import requests


def get_prices_from_db(db_name):
    """ тяжеловесная страшная функция запроса в БД, которую не хочется использовать в тестах"""
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS prices (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          price FLOAT NOT NULL 
                        );
                        """)
    cursor.execute("""
    INSERT INTO prices (name, price) VALUES
     ("рис", 1000),
     ("греча", 5000),
     ("макароны", 3000);
    """)
    cursor.execute("""SELECT price FROM prices;""")
    result = cursor.fetchall()
    if db_name != ":memory:":
        os.unlink(db_name)
    return result


class BusinessLogicService():
    """ Класс-сервис с бизнес-логикой, которую мы хотим протестировать"""

    def __init__(self, cache_service, *args, **kwargs):
        # гипотетический модуль кэша, например Redis, который должен быть запущен отдельным процессом
        self.cache_service = cache_service
        self.db = kwargs.get("db_name", "huge_db.db")

    def _private_method_to_test(self, value):
        """ Приватная функция, которая умножает четные числа на 2, а нечетные увеличивает на 1, в кэш не записывает"""
        return value * 2 if value % 2 == 0 else value + 1

    def _calculate_avg_price(self, all_prices):
        """ Функция расчета средней цены со списком кортежей в качестве аргумента """
        avg_price = sum([row[0] for row in all_prices]) / len(all_prices)
        return avg_price

    def get_avg_price(self):
        """ Функция для расчета средней цены по всей табличке БД """
        all_prices = get_prices_from_db(self.db)
        avg_price = self._calculate_avg_price(all_prices)
        return avg_price

    def get_avg_price_with_cache(self):
        """ Функция для расчета средней цены по всей табличке БД, которая записывает результат в кэш """
        all_prices = get_prices_from_db(self.db)
        avg_price = self._calculate_avg_price(all_prices)
        self.cache_service["avg_price"] = avg_price
        return avg_price

    def get_avg_price_from_external_api(self):
        """ Функция по расчету средней стоимости по информации из внешнего API """
        prices = requests.get("www.88005553535.ru")
        prices = prices.json().get("prices", [])
        list_of_prices = [(row["price"],) for row in prices]
        return self._calculate_avg_price(list_of_prices)


def test_private_method_with_dummy():
    """
    Используем None как dummy, потому что реализация кэша нас не интересует,
     а функция отрабатывает без его участия
     """
    dummy = None
    service = BusinessLogicService(cache_service=dummy)

    assert service._private_method_to_test(2) == 4

    assert service._private_method_to_test(1) == 2


def test_avg_price_with_stub():
    """
    используем заглушку-стаб в виде статичной информации по ценам, чтобы сервис не пытался залезть в БД
    """
    service = BusinessLogicService(cache_service=None)
    # Заводим статичный список, чтобы проверять конкретную формулу расчета без тонкостей работы БД
    stub_for_prices = [(1000,), (1000,)]

    assert service._calculate_avg_price(stub_for_prices) == 1000


def test_avg_price_with_fake():
    """ Тут используется несколько видов заглушек, но рассмотрим конкренто фейк кеша в виде словаря"""
    # Выставляем кеш как обычный словарь(он им по сути и является, ток в памяти другого процесса)
    service = BusinessLogicService(cache_service={})
    # Используем более легковесную реализацию базы данных в оперативной памяти тоже как фейк
    service.db = ":memory:"
    # Выполняем вычисление средней цены и проверяем, что наш кеш заполнился
    service.get_avg_price_with_cache()

    assert "avg_price" in service.cache_service


def test_avg_price_with_mock():
    """
    Тут используем два мока чтобы покрыть зависимости из нашей функции - для класса Response и
     для функции get() из пакета requests
    """
    # определяем через специальный класс, что это мок и что спецификация копируется из класса Response
    mocked_response = MagicMock(spec=requests.Response)
    # через значение return_value меняем результат функции json()  на наш заранее собранный датасет
    mocked_response.json.return_value = {
        "prices":
            [
                {"price": 1000},
                {"price": 1000},
                {"price": 1000},
            ]
    }
    # теперь используем мок, чтобы модуль запросов использовал наш конкретный ответ
    mocked_requests = requests
    mocked_requests.get = MagicMock(return_value=mocked_response)

    service = BusinessLogicService(cache_service=None)

    assert service.get_avg_price_from_external_api() == 1000 # 3000 / 3 == 1000


def test_external_api_avg_price_with_spy():
    """
    Используем методы мок-объектов python чтобы имитировать spy объект для отслеживания выполнения инструкций
    """
    # Патчим наш сервис и конкретный метод, чтобы знать наверняка: используется он или нет
    with mock.patch.object(BusinessLogicService, '_calculate_avg_price', return_value=0) as mock_method:
        service = BusinessLogicService(cache_service={})
        service.get_avg_price()
        # проверка - вызывался наш метод при вычислениях или нет
        mock_method.assert_called()
