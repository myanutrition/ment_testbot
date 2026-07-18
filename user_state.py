# -*- coding: utf-8 -*-
"""
Простое хранилище текущего прогресса пользователя по тесту.
Хранится в памяти процесса — этого достаточно для лид-магнита
(если нужна устойчивость к перезапуску, можно перенести в SQLite).
"""

# user_id -> текущий индекс вопроса (0-based)
_progress: dict[int, int] = {}


def start_quiz(user_id: int):
    _progress[user_id] = 0


def get_current_index(user_id: int) -> int:
    return _progress.get(user_id, 0)


def advance(user_id: int):
    _progress[user_id] = _progress.get(user_id, 0) + 1


def clear(user_id: int):
    _progress.pop(user_id, None)
