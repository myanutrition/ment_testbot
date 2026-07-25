# -*- coding: utf-8 -*-
"""
Простое хранилище текущего прогресса пользователя по тесту:
номер вопроса, набранные баллы, номера вопросов из "рисковой" зоны,
на которые был дан неверный ответ. Хранится в памяти процесса — этого
достаточно для лид-магнита (если нужна устойчивость к перезапуску,
можно перенести в SQLite).
"""

# user_id -> {"index": int, "score": int, "wrong_risk": set[int]}
_progress: dict[int, dict] = {}


def start_quiz(user_id: int):
    _progress[user_id] = {"index": 0, "score": 0, "wrong_risk": set()}


def get_current_index(user_id: int) -> int:
    return _progress.get(user_id, {}).get("index", 0)


def advance(user_id: int):
    state = _progress.setdefault(user_id, {"index": 0, "score": 0, "wrong_risk": set()})
    state["index"] += 1


def register_answer(user_id: int, question_id: int, is_correct: bool, is_risk: bool):
    state = _progress.setdefault(user_id, {"index": 0, "score": 0, "wrong_risk": set()})
    if is_correct:
        state["score"] += 1
    elif is_risk:
        state["wrong_risk"].add(question_id)


def get_score(user_id: int) -> int:
    return _progress.get(user_id, {}).get("score", 0)


def get_wrong_risk(user_id: int) -> set:
    return _progress.get(user_id, {}).get("wrong_risk", set())


def clear(user_id: int):
    _progress.pop(user_id, None)
