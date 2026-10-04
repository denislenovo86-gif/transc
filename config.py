"""
Конфигурация проекта TranscribeFlow
Все пути импортируются из config_paths.py
"""

from pathlib import Path
import sys
import os

# 🔥 Импортируем все пути из config_paths.py
from config_paths import (
    BASE_DIR,
    FFMPEG_DIR,
    VOSK_MODEL_DIR,
    AUDIO_DIR,
    TRANSCRIPTIONS_DIR,
    VIDEOS_DIR,
    ENV_FILE,
    WEB_PORT,
    WEB_HOST,
    WEB_DEBUG,
    SAMPLE_RATE,
    SEGMENT_DURATION,
    MAX_GPT_TEXT_LENGTH,
    LANGUAGE,
    create_all_dirs,
)

# ============================================
# ОПРЕДЕЛЯЕМ, ГДЕ СОХРАНЯТЬ ФАЙЛЫ
# ============================================

if getattr(sys, 'frozen', False):
    USER_HOME = Path.home()
    APP_DATA_DIR = USER_HOME / 'TranscribeFlow'
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_BASE = APP_DATA_DIR
else:
    OUTPUT_BASE = BASE_DIR

# ============================================
# ДИРЕКТОРИИ ДЛЯ ВЫХОДНЫХ ФАЙЛОВ
# ============================================

OUTPUT_DIRS = {
    "audio": OUTPUT_BASE / "audio",
    "transcriptions": OUTPUT_BASE / "transcriptions",
    "videos": OUTPUT_BASE / "videos",
}

# Создаём директории
for dir_path in OUTPUT_DIRS.values():
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"⚠️ Не удалось создать {dir_path}: {e}")

# ============================================
# ПОДДЕРЖИВАЕМЫЕ ПЛАТФОРМЫ
# ============================================

SUPPORTED_PLATFORMS = {
    'youtube': ['youtube.com', 'youtu.be'],
    'rutube': ['rutube.ru'],
    'vk': ['vk.com', 'vkontakte.ru', 'vkvideo.ru']
}

# ============================================
# НАСТРОЙКИ YT-DLP
# ============================================

YT_DLP_BASE_OPTS = {
    'retries': 10,
    'socket_timeout': 30,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    },
    'quiet': False,
    'extract_flat': False,
}

# 🔥 НАСТРОЙКИ ДЛЯ СКАЧИВАНИЯ ТОЛЬКО АУДИО
# Скачиваем в mp3 — минимальный размер и максимальная скорость
# 🔥 НАСТРОЙКИ ДЛЯ СКАЧИВАНИЯ ТОЛЬКО АУДИО
AUDIO_FORMAT_OPTS = {
    # 🔥 Скачиваем ТОЛЬКО аудио (без видео)
    'format': 'worstaudio/worst',  # Запасной вариант — худшее качество (быстрее)
    'format_sort': ['+size', '+br'],  # Сортируем по размеру — сначала маленькие

    # 🔥 Ключевые опции для экономии трафика
    'noplaylist': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '64',  # 64 kbps — для речи хватит с головой

    # 🔥 Отключаем видео
    'videoformat': 'none',
    'skip_download': False,

    # 🔥 Постпроцессинг — конвертация в mp3
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '64',
        'nopostoverwrites': False,
    }],

    # 🔥 Удаляем оригинал после конвертации
    'keepvideo': False,
    'postprocessor_args': ['-threads', '4'],
}

# Настройки для разных платформ
PLATFORM_OPTS = {
    'youtube': {
        **AUDIO_FORMAT_OPTS,
        'outtmpl': str(OUTPUT_DIRS["audio"] / '%(title)s.%(ext)s'),
    },
    'rutube': {
        **AUDIO_FORMAT_OPTS,
        'outtmpl': str(OUTPUT_DIRS["audio"] / 'rutube_%(title)s.%(ext)s'),
    },
    'vk': {
        **AUDIO_FORMAT_OPTS,
        'outtmpl': str(OUTPUT_DIRS["audio"] / 'vk_%(title)s.%(ext)s'),
    }
}

# ============================================
# ЭКСПОРТ ВСЕХ ПЕРЕМЕННЫХ
# ============================================

__all__ = [
    'BASE_DIR',
    'FFMPEG_DIR',
    'VOSK_MODEL_DIR',
    'AUDIO_DIR',
    'TRANSCRIPTIONS_DIR',
    'VIDEOS_DIR',
    'ENV_FILE',
    'OUTPUT_BASE',
    'OUTPUT_DIRS',
    'SUPPORTED_PLATFORMS',
    'YT_DLP_BASE_OPTS',
    'AUDIO_FORMAT_OPTS',
    'PLATFORM_OPTS',
    'WEB_PORT',
    'WEB_HOST',
    'WEB_DEBUG',
    'SAMPLE_RATE',
    'SEGMENT_DURATION',
    'MAX_GPT_TEXT_LENGTH',
    'LANGUAGE',
]