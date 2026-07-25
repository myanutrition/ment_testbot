# -*- coding: utf-8 -*-
"""
Все хендлеры бота в одном файле:
- /start и приветствие с фото
- проверка подписки на канал
- прохождение теста
- команда /stats для админа
"""
import asyncio
import logging
import os

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest

import config
import user_state
from quiz_data import (
    QUESTIONS,
    INTRO_TEXT,
    MENTORSHIP_PITCH,
    RISK_QUESTION_IDS,
    RISK_WARNING_TEXT,
    get_result_level,
)
from database import (
    log_event,
    EVENT_BOT_OPENED,
    EVENT_QUIZ_STARTED,
    EVENT_QUIZ_COMPLETED,
    EVENT_MENTORSHIP_CLICKED,
)

router = Router()
logger = logging.getLogger(__name__)

TOTAL_QUESTIONS = len(QUESTIONS)
NOT_MEMBER_STATUSES = {"left", "kicked"}


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Начать", callback_data="begin_flow")]]
    )


def _check_sub_kb() -> InlineKeyboardMarkup:
    channel = config.CHANNEL_USERNAME.lstrip("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Перейти на канал", url=f"https://t.me/{channel}")],
            [InlineKeyboardButton(text="✅ Я подписался(-ась)", callback_data="begin_flow")],
        ]
    )


def _question_kb(index: int) -> InlineKeyboardMarkup:
    q = QUESTIONS[index]
    letters = list(q["options"].keys())
    buttons = [
        InlineKeyboardButton(text=letter, callback_data=f"ans:{index}:{letter}")
        for letter in letters
    ]
    # Раскладываем кнопки по 2 в ряд
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _next_kb(index: int) -> InlineKeyboardMarkup:
    is_last = index == TOTAL_QUESTIONS - 1
    label = "Показать результат 🎉" if is_last else "Далее ➡️"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"next:{index}")]]
    )


def _mentorship_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Подробнее о менторстве", callback_data="mentorship_click")]
        ]
    )


def _mentorship_link_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Перейти на сайт →", url=config.MENTORSHIP_URL)]]
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    log_event(message.from_user.id, EVENT_BOT_OPENED)

    kb = _start_kb()
    photo = None
    if config.START_PHOTO_FILE_ID:
        photo = config.START_PHOTO_FILE_ID
    elif os.path.exists(config.START_PHOTO_PATH):
        photo = FSInputFile(config.START_PHOTO_PATH)

    if photo:
        await message.answer_photo(photo=photo, caption=INTRO_TEXT, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(INTRO_TEXT, reply_markup=kb, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Проверка подписки
# ---------------------------------------------------------------------------

async def check_subscription(bot: Bot, user_id: int) -> bool:
    """
    Возвращает True, если пользователь подписан на config.CHANNEL_USERNAME.
    Бот должен быть добавлен в канал администратором.
    """
    try:
        member = await bot.get_chat_member(chat_id=config.CHANNEL_USERNAME, user_id=user_id)
        return member.status not in NOT_MEMBER_STATUSES
    except TelegramBadRequest as e:
        logger.error("Не удалось проверить подписку на %s: %s", config.CHANNEL_USERNAME, e)
        return False


@router.callback_query(F.data == "begin_flow")
async def on_begin_flow(callback: CallbackQuery):
    is_subscribed = await check_subscription(callback.bot, callback.from_user.id)
    await callback.answer()

    if is_subscribed:
        await callback.message.answer("✅ Подписка подтверждена! Начинаем тест.")
        await send_question(callback.message, callback.from_user.id, first=True)
    else:
        await callback.message.answer(
            "Чтобы пройти тест, подпишись на канал 👇", reply_markup=_check_sub_kb()
        )


# ---------------------------------------------------------------------------
# Тест
# ---------------------------------------------------------------------------

async def send_question(message: Message, user_id: int, first: bool = False):
    if first:
        user_state.start_quiz(user_id)
        log_event(user_id, EVENT_QUIZ_STARTED)

    index = user_state.get_current_index(user_id)
    q = QUESTIONS[index]

    options_text = "\n".join(f"{letter}. {text}" for letter, text in q["options"].items())
    text = (
        f"<b>Вопрос {index + 1} из {TOTAL_QUESTIONS}</b>\n\n"
        f"{q['question']}\n\n"
        f"{options_text}"
    )
    await message.answer(text, reply_markup=_question_kb(index), parse_mode="HTML")


@router.callback_query(F.data.startswith("ans:"))
async def on_answer(callback: CallbackQuery):
    _, idx_str, letter = callback.data.split(":")
    index = int(idx_str)
    q = QUESTIONS[index]
    correct = q["correct"]
    is_correct = letter == correct
    is_risk = q["id"] in RISK_QUESTION_IDS

    user_state.register_answer(callback.from_user.id, q["id"], is_correct, is_risk)

    await callback.answer("Верно! ✅" if is_correct else f"Правильный ответ: {correct}")

    verdict = "✅ Верно!" if is_correct else f"Правильный ответ: <b>{correct}</b>"
    text = f"{verdict}\n\n<b>Разбор:</b>\n{q['explanation']}"
    await callback.message.answer(text, reply_markup=_next_kb(index), parse_mode="HTML")


@router.callback_query(F.data.startswith("next:"))
async def on_next(callback: CallbackQuery):
    _, idx_str = callback.data.split(":")
    index = int(idx_str)
    user_id = callback.from_user.id
    await callback.answer()

    if index >= TOTAL_QUESTIONS - 1:
        log_event(user_id, EVENT_QUIZ_COMPLETED)

        score = user_state.get_score(user_id)
        wrong_risk = sorted(user_state.get_wrong_risk(user_id))
        user_state.clear(user_id)

        level = get_result_level(score)
        result_text = (
            f"🎯 <b>Ваш результат: {score} из {TOTAL_QUESTIONS}</b>\n\n"
            f"{level['emoji']} <b>{level['title']}</b>\n\n"
            f"{level['body']}\n\n"
            f"<b>Итог:</b>\n{level['itog']}"
        )
        await callback.message.answer(
            result_text, reply_markup=_mentorship_kb(), parse_mode="HTML"
        )

        if wrong_risk:
            await asyncio.sleep(2)
            numbers = ", ".join(str(n) for n in wrong_risk)
            await callback.message.answer(
                RISK_WARNING_TEXT.format(numbers=numbers), parse_mode="HTML"
            )

        await asyncio.sleep(2)
        await callback.message.answer(MENTORSHIP_PITCH, reply_markup=_mentorship_kb(), parse_mode="HTML")
    else:
        user_state.advance(user_id)
        await send_question(callback.message, user_id, first=False)


@router.callback_query(F.data == "mentorship_click")
async def on_mentorship_click(callback: CallbackQuery):
    log_event(callback.from_user.id, EVENT_MENTORSHIP_CLICKED)
    await callback.answer()
    await callback.message.answer("Вот ссылка 👇", reply_markup=_mentorship_link_kb())


# ---------------------------------------------------------------------------
# /stats (только для админов)
# ---------------------------------------------------------------------------

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    from database import get_stats

    s = get_stats()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"Открыли бота: <b>{s['opened']}</b>\n"
        f"Начали тест: <b>{s['started']}</b>\n"
        f"Закончили тест: <b>{s['completed']}</b>\n"
        f"Кликнули «Подробнее о менторстве»: <b>{s['mentorship_clicks']}</b>"
    )
    await message.answer(text, parse_mode="HTML")
