import time


def handle_db_errors(func):
    """Обрабатывает ошибки базы данных."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except Exception as error:
            print(f"Произошла непредвиденная ошибка: {error}")

        return None

    return wrapper


def confirm_action(action_name):
    """Запрашивает подтверждение действия."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            answer = input(f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ')
            if answer.lower() != "y":
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func):
    """Печатает время выполнения функции."""

    def wrapper(*args, **kwargs):
        started_at = time.monotonic()
        result = func(*args, **kwargs)
        elapsed_time = time.monotonic() - started_at
        print(f"Функция {func.__name__} выполнилась за {elapsed_time:.3f} секунд")
        return result

    return wrapper


def create_cacher():
    """Создает замыкание с кэшем."""

    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    return cache_result
