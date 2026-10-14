def split_arguments(text):
    """Разделяет аргументы по запятым, не трогая текст в кавычках."""

    arguments = []
    current = ""
    quote = None

    for symbol in text:
        if symbol in ('"', "'"):
            if quote is None:
                quote = symbol
            elif quote == symbol:
                quote = None
            current += symbol
        elif symbol == "," and quote is None:
            arguments.append(current.strip())
            current = ""
        else:
            current += symbol

    if quote is not None:
        raise ValueError("Не закрыта кавычка в значении.")
    if current.strip():
        arguments.append(current.strip())
    return arguments


def parse_value(value):
    """Преобразует строковое значение в int, bool или str."""

    value = value.strip()
    if not value:
        raise ValueError("Передано пустое значение.")

    if value[0] in ('"', "'"):
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("Не закрыта кавычка в значении.")
        return value[1:-1]

    lowered_value = value.lower()
    if lowered_value == "true":
        return True
    if lowered_value == "false":
        return False
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def parse_values(text):
    """Разбирает список значений в круглых скобках."""

    text = text.strip()
    if not text.startswith("(") or not text.endswith(")"):
        raise ValueError("Значения должны находиться в круглых скобках.")
    inside = text[1:-1].strip()
    if not inside:
        return []
    return [parse_value(item) for item in split_arguments(inside)]


def parse_clause(text):
    """Превращает условие вида 'age = 18' в словарь."""

    column, separator, value = text.partition("=")
    if not separator or not column.strip() or not value.strip():
        raise ValueError("Условие должно иметь вид: столбец = значение.")
    return {column.strip(): parse_value(value)}


def parse_set_clause(text):
    """Разбирает одно или несколько значений после слова set."""

    result = {}
    for item in split_arguments(text):
        result.update(parse_clause(item))
    if not result:
        raise ValueError("После set не указаны значения.")
    return result
