# Primitive DB

`Primitive DB` — учебная консольная база данных на Python. Проект написан
в процедурном стиле и хранит метаданные и строки таблиц в JSON-файлах.

Поддерживаемые типы столбцов: `int`, `str` и `bool`. Столбец `ID:int`
создаётся автоматически.

## Установка и запуск

Для проекта нужны Python 3.12 и [uv](https://docs.astral.sh/uv/).

```bash
make install
make run
```

Те же команды без Makefile:

```bash
uv sync
uv run python -m primitive_db.main
```

После установки wheel проект также запускается командой `database`.

## Управление таблицами

```text
create_table users name:str age:int is_active:bool
list_tables
drop_table users
info users
```

Удаление таблицы считается опасной операцией, поэтому программа попросит
подтвердить её вводом `y`. Любой другой ответ отменяет действие.

## CRUD-операции

```text
insert into users values ("Sergei", 28, true)
select from users
select from users where age = 28
update users set age = 29 where name = "Sergei"
delete from users where ID = 1
```

Для `delete` также требуется подтверждение. Одинаковые запросы `select`
кэшируются с помощью замыкания. Время выполнения `select` и `insert`
выводится в консоль. Ошибки базы данных обрабатываются общим декоратором.

## Проверка проекта

```bash
make lint
make build
```

## Демонстрация

[![Демонстрация работы Primitive DB](https://asciinema.org/a/BxTDqpLQBi6gLquy.svg)](https://asciinema.org/a/BxTDqpLQBi6gLquy)

Локальная копия записи: [demo.cast](demo.cast).

Её можно посмотреть в терминале:

```bash
asciinema play demo.cast
```
