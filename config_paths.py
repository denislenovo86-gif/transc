"""
============================================================
🔥 ЦЕНТРАЛИЗОВАННАЯ КОНФИГУРАЦИЯ ПУТЕЙ
============================================================
Все пути к папкам и файлам указываются ЗДЕСЬ.
При переносе на другой компьютер — меняйте ТОЛЬКО ЭТОТ ФАЙЛ.

Просто укажите свои пути ниже и всё заработает.
============================================================
"""

from pathlib import Path

# ============================================
# 1. БАЗОВАЯ ПАПКА ПРОЕКТА
# ============================================
# По умолчанию — папка, где лежит этот файл
BASE_DIR = Path(__file__).parent

# ============================================
# 2. ПУТЬ К FFMPEG
# ============================================
# Укажите путь к папке BIN, где лежит ffmpeg.exe
FFMPEG_DIR = BASE_DIR / "ffmpeg-master-latest-win64-gpl" / "bin"

# ============================================
# 3. ПУТЬ К МОДЕЛИ VOSK
# ============================================
VOSK_MODEL_DIR = BASE_DIR / "vosk-model-small-ru-0.22"

# ============================================
# 4. ПАПКИ ДЛЯ СОХРАНЕНИЯ ФАЙЛОВ
# ============================================
AUDIO_DIR = BASE_DIR / "audio"
TRANSCRIPTIONS_DIR = BASE_DIR / "transcriptions"
VIDEOS_DIR = BASE_DIR / "videos"

# ============================================
# 5. ФАЙЛ С API КЛЮЧАМИ
# ============================================
ENV_FILE = BASE_DIR / ".env"

# ============================================
# 6. НАСТРОЙКИ СЕРВЕРА (для сайта)
# ============================================
WEB_PORT = 5000
WEB_HOST = "127.0.0.1"
WEB_DEBUG = False

# ============================================
# 7. НАСТРОЙКИ РАСПОЗНАВАНИЯ
# ============================================
SAMPLE_RATE = 16000
SEGMENT_DURATION = 5.0
MAX_GPT_TEXT_LENGTH = 3000

# ============================================
# 8. ЯЗЫК И ЛОКАЛИЗАЦИЯ
# ============================================
LANGUAGE = "ru"


# ============================================
# 9. СОЗДАНИЕ ПАПОК
# ============================================
def create_all_dirs():
    """Создаёт все необходимые папки"""
    for folder in [AUDIO_DIR, TRANSCRIPTIONS_DIR, VIDEOS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


try:
    create_all_dirs()
except Exception as e:
    print(f"⚠️ Ошибка создания папок: {e}")


# ============================================
# 10. ПРОВЕРКА ПУТЕЙ
# ============================================
def check_paths():
    """Проверяет, что все ключевые пути существуют"""
    results = {
        'BASE_DIR': BASE_DIR.exists(),
        'FFMPEG_DIR': FFMPEG_DIR.exists(),
        'VOSK_MODEL_DIR': VOSK_MODEL_DIR.exists(),
        'ENV_FILE': ENV_FILE.exists(),
    }

    for name, exists in results.items():
        status = "✅" if exists else "❌"
        print(f"{status} {name}: {results[name]}")

    return all(results.values())


if __name__ == "__main__":
    print("=" * 60)
    print("ПРОВЕРКА ПУТЕЙ")
    print("=" * 60)
    print(f"BASE_DIR:         {BASE_DIR}")
    print(f"FFMPEG_DIR:       {FFMPEG_DIR}")
    print(f"VOSK_MODEL_DIR:   {VOSK_MODEL_DIR}")
    print(f"AUDIO_DIR:        {AUDIO_DIR}")
    print(f"TRANSCRIPTIONS:   {TRANSCRIPTIONS_DIR}")
    print(f"ENV_FILE:         {ENV_FILE}")
    print("=" * 60)
    check_paths()