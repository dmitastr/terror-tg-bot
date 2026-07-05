from typing import Any, Sequence


def flatten_length(lst: Sequence[Any]) -> int:
    """Рекурсивно подсчитывает общее количество элементов в списке, включая вложенные списки."""
    count = 0
    for item in lst:
        if isinstance(item, list) or isinstance(item, tuple):
            count += flatten_length(item)
        else:
            count += 1
    return count
