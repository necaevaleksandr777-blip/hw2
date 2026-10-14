from primitive_db.constants import ID_COLUMN, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

cache_select_result = create_cacher()


def get_schema(metadata, table_name):
    if table_name not in metadata:
        raise KeyError(table_name)

    stored_schema = metadata[table_name]
    if isinstance(stored_schema, dict):
        return stored_schema.copy()

    schema = {}
    for column in stored_schema:
        column_name, separator, column_type = column.partition(":")
        if not separator:
            raise ValueError(f"Некорректное описание столбца: {column}")
        schema[column_name] = column_type
    return schema


def validate_value(value, expected_type):
    if expected_type == "int":
        is_valid = isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "bool":
        is_valid = isinstance(value, bool)
    elif expected_type == "str":
        is_valid = isinstance(value, str)
    else:
        raise ValueError(f"Неизвестный тип данных: {expected_type}")

    if not is_valid:
        raise ValueError(f"Значение {value!r} должно иметь тип {expected_type}.")


def validate_changes(metadata, table_name, changes):
    schema = get_schema(metadata, table_name)
    for column_name, value in changes.items():
        if column_name not in schema:
            raise KeyError(column_name)
        if column_name == ID_COLUMN:
            raise ValueError("Значение ID нельзя изменять.")
        validate_value(value, schema[column_name])


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Создает новую таблицу и добавляет ее схему в метаданные."""

    if not table_name:
        raise ValueError("Не указано имя таблицы.")
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует.')
    if not columns:
        raise ValueError("Нужно указать хотя бы один столбец.")

    checked_columns = []
    column_names = {ID_COLUMN}
    for column in columns:
        column_name, separator, column_type = column.partition(":")
        if not separator or not column_name or not column_type:
            raise ValueError(f"Некорректное описание столбца: {column}")
        if column_name in column_names:
            raise ValueError(f'Столбец "{column_name}" уже указан.')
        if column_type not in VALID_TYPES:
            raise ValueError(
                f'Тип "{column_type}" не поддерживается. '
                f"Доступные типы: {', '.join(VALID_TYPES)}."
            )
        column_names.add(column_name)
        checked_columns.append(f"{column_name}:{column_type}")

    metadata[table_name] = [f"{ID_COLUMN}:int", *checked_columns]
    columns_text = ", ".join(metadata[table_name])
    print(f'Таблица "{table_name}" успешно создана со столбцами: {columns_text}')
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет таблицу из метаданных."""

    if table_name not in metadata:
        raise KeyError(table_name)
    del metadata[table_name]
    print(f'Таблица "{table_name}" успешно удалена.')
    return metadata


def list_tables(metadata):
    if not metadata:
        print("В базе данных пока нет таблиц.")
        return []
    for table_name in metadata:
        print(f"- {table_name}")
    return list(metadata)


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавляет новую запись и возвращает данные."""

    schema = get_schema(metadata, table_name)
    user_columns = [name for name in schema if name != ID_COLUMN]
    if len(values) != len(user_columns):
        raise ValueError(
            f"Ожидалось значений: {len(user_columns)}, получено: {len(values)}."
        )

    for column_name, value in zip(user_columns, values, strict=True):
        validate_value(value, schema[column_name])

    table_data = load_table_data(table_name)
    new_id = max((row.get(ID_COLUMN, 0) for row in table_data), default=0) + 1
    new_row = {ID_COLUMN: new_id}
    new_row.update(dict(zip(user_columns, values, strict=True)))
    table_data.append(new_row)
    print(f'Запись с ID={new_id} успешно добавлена в таблицу "{table_name}".')
    return table_data


def _make_select_key(table_data, where_clause):
    rows_key = tuple(tuple(sorted(row.items())) for row in table_data)
    where_key = tuple(sorted(where_clause.items())) if where_clause else None
    return rows_key, where_key


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Возвращает все записи или записи, по условию"""

    if where_clause and table_data:
        for column_name in where_clause:
            if column_name not in table_data[0]:
                raise KeyError(column_name)

    def find_rows():
        if not where_clause:
            return [row.copy() for row in table_data]
        return [
            row.copy()
            for row in table_data
            if all(row.get(key) == value for key, value in where_clause.items())
        ]

    cache_key = _make_select_key(table_data, where_clause)
    return cache_select_result(cache_key, find_rows)


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Изменяет записи по условию."""

    if table_data:
        known_columns = table_data[0]
        for column_name in (*set_clause, *where_clause):
            if column_name not in known_columns:
                raise KeyError(column_name)

    for row in table_data:
        matches = all(row.get(key) == value for key, value in where_clause.items())
        if matches:
            row.update(set_clause)
    return table_data


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удаляет записи по условию."""

    if table_data:
        for column_name in where_clause:
            if column_name not in table_data[0]:
                raise KeyError(column_name)
    return [
        row
        for row in table_data
        if not all(row.get(key) == value for key, value in where_clause.items())
    ]


@handle_db_errors
def info(metadata, table_name):
    """Печатает схему и колво записей таблицы."""

    schema = get_schema(metadata, table_name)
    table_data = load_table_data(table_name)
    columns_text = ", ".join(
        f"{column_name}:{column_type}" for column_name, column_type in schema.items()
    )
    print(f"Таблица: {table_name}")
    print(f"Столбцы: {columns_text}")
    print(f"Количество записей: {len(table_data)}")
    return schema
