"""Консольный цикл и обработка команд пользователя."""

import shlex

from prettytable import PrettyTable

from primitive_db.constants import ID_COLUMN, META_FILE
from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    get_schema,
    info,
    insert,
    list_tables,
    select,
    update,
    validate_changes,
    validate_value,
)
from primitive_db.parser import parse_clause, parse_set_clause, parse_values
from primitive_db.utils import (
    delete_table_data,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def print_help():
    """Печатает справку по доступным командам."""

    print("\n***Операции с данными***\n")
    print("Функции:")
    print("create_table <таблица> <столбец:тип> ... - создать таблицу")
    print("list_tables - показать список всех таблиц")
    print("drop_table <таблица> - удалить таблицу")
    print("insert into <таблица> values (...) - добавить запись")
    print("select from <таблица> [where столбец = значение] - чтение")
    print("update <таблица> set столбец = значение where ... - обновление")
    print("delete from <таблица> where столбец = значение - удаление")
    print("info <таблица> - информация о таблице")
    print("help - справочная информация")
    print("exit - выход из программы\n")


def print_table(rows, columns):
    """Печатает данные в виде таблицы."""

    table = PrettyTable()
    table.field_names = columns
    for row in rows:
        table.add_row([row.get(column, "") for column in columns])
    print(table)


def _require_argument_count(arguments, minimum, example):
    """Проверяет количество аргументов."""

    if len(arguments) < minimum:
        raise ValueError(f"Некорректная команда. Пример: {example}")


def _text_after(command, marker):
    """Возвращает часть команды после служебного слова."""

    marker_position = command.lower().find(marker)
    if marker_position == -1:
        raise ValueError(f"В команде отсутствует {marker.strip()}.")
    return command[marker_position + len(marker) :].strip()


def _handle_create(metadata, arguments):
    """Обрабатывает создание таблицы."""

    _require_argument_count(
        arguments,
        3,
        "create_table users name:str age:int",
    )
    result = create_table(metadata, arguments[1], arguments[2:])
    if result is not None:
        save_metadata(META_FILE, result)
        save_table_data(arguments[1], [])


def _handle_drop(metadata, arguments):
    """Обрабатывает удаление таблицы."""

    _require_argument_count(arguments, 2, "drop_table users")
    table_name = arguments[1]
    result = drop_table(metadata, table_name)
    if result is not None:
        save_metadata(META_FILE, result)
        delete_table_data(table_name)


def _handle_insert(metadata, command, arguments):
    """Обрабатывает добавление записи."""

    _require_argument_count(
        arguments,
        5,
        'insert into users values ("Ivan", 20, true)',
    )
    if arguments[1].lower() != "into" or arguments[3].lower() != "values":
        raise ValueError("Некорректный синтаксис команды insert.")
    table_name = arguments[2]
    values = parse_values(_text_after(command, " values "))
    result = insert(metadata, table_name, values)
    if result is not None:
        save_table_data(table_name, result)


def _handle_select(metadata, command, arguments):
    """Обрабатывает выборку записей."""

    _require_argument_count(arguments, 3, "select from users")
    if arguments[1].lower() != "from":
        raise ValueError("После select должно быть слово from.")
    table_name = arguments[2]
    schema = get_schema(metadata, table_name)
    where_clause = None
    if " where " in command.lower():
        where_clause = parse_clause(_text_after(command, " where "))
        for column_name, value in where_clause.items():
            if column_name not in schema:
                raise KeyError(column_name)
            validate_value(value, schema[column_name])
    rows = select(load_table_data(table_name), where_clause)
    if rows is not None:
        print_table(rows, list(schema))


def _handle_update(metadata, command, arguments):
    """Обрабатывает обновление записей."""

    _require_argument_count(
        arguments,
        8,
        'update users set age = 21 where name = "Ivan"',
    )
    lowered_command = command.lower()
    set_position = lowered_command.find(" set ")
    where_position = lowered_command.find(" where ")
    if set_position == -1 or where_position < set_position:
        raise ValueError("Команда update должна содержать set и where.")

    table_name = arguments[1]
    set_text = command[set_position + len(" set ") : where_position]
    where_text = command[where_position + len(" where ") :]
    set_clause = parse_set_clause(set_text)
    where_clause = parse_clause(where_text)
    validate_changes(metadata, table_name, set_clause)

    schema = get_schema(metadata, table_name)
    for column_name, value in where_clause.items():
        if column_name not in schema:
            raise KeyError(column_name)
        validate_value(value, schema[column_name])

    table_data = load_table_data(table_name)
    changed_ids = [
        row.get(ID_COLUMN)
        for row in table_data
        if all(row.get(key) == value for key, value in where_clause.items())
    ]
    result = update(table_data, set_clause, where_clause)
    if result is not None:
        save_table_data(table_name, result)
        if changed_ids:
            for row_id in changed_ids:
                print(
                    f'Запись с ID={row_id} в таблице "{table_name}" успешно обновлена.'
                )
        else:
            print("Подходящие записи не найдены.")


def _handle_delete(metadata, command, arguments):
    """Обрабатывает удаление записей."""

    _require_argument_count(
        arguments,
        7,
        "delete from users where ID = 1",
    )
    if arguments[1].lower() != "from" or " where " not in command.lower():
        raise ValueError("Команда delete должна содержать from и where.")
    table_name = arguments[2]
    schema = get_schema(metadata, table_name)
    where_clause = parse_clause(_text_after(command, " where "))
    for column_name, value in where_clause.items():
        if column_name not in schema:
            raise KeyError(column_name)
        validate_value(value, schema[column_name])

    table_data = load_table_data(table_name)
    deleted_ids = [
        row.get(ID_COLUMN)
        for row in table_data
        if all(row.get(key) == value for key, value in where_clause.items())
    ]
    result = delete(table_data, where_clause)
    if result is not None:
        save_table_data(table_name, result)
        if deleted_ids:
            for row_id in deleted_ids:
                print(
                    f'Запись с ID={row_id} успешно удалена из таблицы "{table_name}".'
                )
        else:
            print("Подходящие записи не найдены.")


def process_command(command, metadata):
    """Разбирает и выполняет команду."""

    arguments = shlex.split(command)
    if not arguments:
        return True

    command_name = arguments[0].lower()
    if command_name == "exit":
        print("До свидания!")
        return False
    if command_name == "help":
        print_help()
    elif command_name == "create_table":
        _handle_create(metadata, arguments)
    elif command_name == "list_tables":
        list_tables(metadata)
    elif command_name == "drop_table":
        _handle_drop(metadata, arguments)
    elif command_name == "insert":
        _handle_insert(metadata, command, arguments)
    elif command_name == "select":
        _handle_select(metadata, command, arguments)
    elif command_name == "update":
        _handle_update(metadata, command, arguments)
    elif command_name == "delete":
        _handle_delete(metadata, command, arguments)
    elif command_name == "info":
        _require_argument_count(arguments, 2, "info users")
        info(metadata, arguments[1])
    else:
        print(f"Функции {arguments[0]} нет. Попробуйте снова.")
    return True


def run():
    """Запускает основной цикл программы."""

    print_help()
    while True:
        metadata = load_metadata(META_FILE)
        try:
            command = input(">>>Введите команду: ").strip()
            if not process_command(command, metadata):
                break
        except (ValueError, KeyError) as error:
            print(f"Некорректное значение: {error}. Попробуйте снова.")
