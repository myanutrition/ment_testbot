# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота — берётся ТОЛЬКО из переменной окружения (.env на сервере).
# Никогда не хранить токен в коде или в git.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Канал, подписку на который проверяем перед тестом.
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@mya_mentoring")

# ID администраторов (через запятую), у кого доступна команда /stats
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

# Ссылка на менторство
MENTORSHIP_URL = "https://myanutrition.ru/mentorstvo"

# Фото для приветственного сообщения.
# Вариант 1 (проще, но менее надёжно): file_id, полученный этим же ботом ранее.
START_PHOTO_FILE_ID = os.getenv("START_PHOTO_FILE_ID", "").strip()
# Вариант 2 (рекомендуется): файл фото лежит рядом с main.py
START_PHOTO_PATH = os.getenv("START_PHOTO_PATH", "start_photo.jpg")

# Путь к файлу базы данных статистики
DB_PATH = os.getenv("DB_PATH", "stats.db")
