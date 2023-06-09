# Виды mock объектов

### Введение

Прежде чем обсуждать Mock-объекты дадим характеристику хорошему модульному тесту:

- **быстрый** - не тратим время на ожидание
- **детерминированный** - одинаковый результат при одинаковых входных данных
- **прост в настройке** - не требует масштабного развертывания и больших усилий для разработчиков

Из этого вытекает необходимость тестовых дублеров и их назначение:

> **Тестовые дублеры -** это объекты-заглушки, которые имитируют или замещают реальные зависимости необходимые для тестирования системы.
> 

Замещаются зависимости, которые значительно замедляют тестирование, влияют на результат тестирования юнита или тяжело разворачиваются на локальном 

### Виды тестовых дублеров

1. пустышки (dummies)
2. стабы (stubs)
3. фейки (fakes)
4. моки (mocks)
5. шпионы (spies)

### Пустышка(*dummy)*

Самая пустая и примитивная заглушка, не имеет реализации, в основном используется, чтобы хоть как-то заполнить обязательные аргументы или коллекцию

*пример:*

```python
def test_private_method_with_dummy():
    """
    Используем None как dummy, потому что реализация кэша нас не интересует,
     а функция отрабатывает без его участия
     """
    dummy = None
    service = BusinessLogicService(cache_service=dummy)

    assert service._private_method_to_test(2) == 4

    assert service._private_method_to_test(1) == 2
```

### Стаб(stub)

Заглушка с фиксированным ответом в качестве реализации

*пример:*

```python
def test_avg_price_with_stub():
    """
    используем заглушку-стаб в виде статичной информации по ценам, чтобы сервис не пытался залезть в БД
    """
    service = BusinessLogicService(cache_service=None)
    # Заводим статичный список, чтобы проверять конкретную формулу расчета без тонкостей работы БД
    stub_for_prices = [(1000,), (1000,)]

    assert service._calculate_avg_price(stub_for_prices) == 1000
```

### Фейк(fake)

Заглушка с более примитивной и быстрой реализацией для удовлетворения требований к тестовому окружению(простота, скорость)

*пример:*

```python
def test_avg_price_with_fake():
    """ Тут используется несколько видов заглушек, но рассмотрим конкренто фейк кеша в виде словаря"""
    # Выставляем кеш как обычный словарь(он им по сути и является, ток в памяти другого процесса)
    service = BusinessLogicService(cache_service={})
    # Используем более легковесную реализацию базы данных в оперативной памяти тоже как фейк
    service.db = ":memory:"
    # Выполняем вычисление средней цены и проверяем, что наш кеш заполнился
    service.get_avg_price_with_cache()
    
    assert "avg_price" in service.cache_service
```

### Мок(mock)

Заглушка с реализацией близкой к исходному коду и позволяющая отслеживать поведение имитированной функции(объекта)

*пример:*

```python
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
```

### Шпион(spy)

заглушка, позволяющая отслеживать поведение имитированной функции(объекта), но не обладающая такого же качества реализацией

*пример:*

```python
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
```

### Почему моки хорошо и почему плохо?

Плохо:

- индикатор сильно связной архитектуры и плохого разделения на модули/функции
- Зачастую хороший мок-объект требует времени для реализации столько же сколько и тестируемый код

Хорошо:

- тесты занимают больше времени
- если заглушки примитивны, то время больше уделяется тестированию модуля, а не подготовкой к его тестам