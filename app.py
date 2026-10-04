"""
TranscribeFlow Web — Веб-сервер
Все пути импортируются из config.py
"""
import os
import sys
import json
import threading
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS

# 🔥 Добавляем корневую папку в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 🔥 ИМПОРТИРУЕМ ВСЕ ПУТИ ИЗ CONFIG
from config import (
    BASE_DIR, FFMPEG_DIR, VOSK_MODEL_DIR,
    OUTPUT_DIRS, OUTPUT_BASE,
    WEB_PORT, WEB_HOST, WEB_DEBUG,
    SUPPORTED_PLATFORMS,
)

from services import download_audio, transcribe_audio_with_timestamps
from services.yandex_gpt import YandexGPT, correct_text_with_yandex, correct_long_text
from services.text_correction import format_transcription_with_timestamps, simple_correction
from utils.audio_utils import convert_to_wav
from utils.file_utils import sanitize_filename, ensure_directory_exists
from utils.validation import validate_url, detect_platform
from utils.punctuation_utils import process_transcription
import subprocess

# ============================================
# ИНИЦИАЛИЗАЦИЯ FLASK
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'transcriber-secret-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
CORS(app)

# ============================================
# СОЗДАНИЕ ПАПОК
# ============================================

UPLOAD_FOLDER = BASE_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

STATIC_FOLDER = BASE_DIR / 'static'
STATIC_FOLDER.mkdir(exist_ok=True)

TEMPLATES_FOLDER = BASE_DIR / 'templates'
TEMPLATES_FOLDER.mkdir(exist_ok=True)

# Хранилище для статусов задач
tasks = {}


# ============================================
# НАСТРОЙКА ОКРУЖЕНИЯ
# ============================================

def setup_environment() -> bool:
    """Настройка окружения перед запуском"""
    print("\n=== Настройка окружения ===")

    # Проверяем FFmpeg
    ffmpeg_path = str(FFMPEG_DIR)
    if ffmpeg_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print(f"✓ FFmpeg найден: {ffmpeg_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"✗ FFmpeg не найден по пути: {ffmpeg_path}")
        print("  Убедитесь, что FFmpeg установлен и путь указан правильно")

    # Создаем директории
    for name, path in OUTPUT_DIRS.items():
        if ensure_directory_exists(path):
            print(f"✓ Директория {name}: {path}")
        else:
            print(f"✗ Не удалось создать директорию {name}")
            return False

    # Проверяем модель Vosk
    print(f"\nПроверка модели Vosk:")
    print(f"Путь к модели: {VOSK_MODEL_DIR}")

    if VOSK_MODEL_DIR.exists():
        print(f"✓ Модель Vosk найдена: {VOSK_MODEL_DIR}")
        total_size = sum(f.stat().st_size for f in VOSK_MODEL_DIR.rglob('*') if f.is_file()) / 1024 / 1024
        print(f"  Размер модели: {total_size:.1f} MB")
    else:
        print(f"✗ Модель Vosk не найдена: {VOSK_MODEL_DIR}")
        print("\n  Как установить модель Vosk:")
        print("  1. Скачайте модель с https://alphacephei.com/vosk/models")
        print("  2. Выберите русскоязычную модель (vosk-model-small-ru-0.22)")
        print("  3. Распакуйте архив в папку проекта")
        return False

    return True


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def extract_video_id(url: str, platform: str) -> str:
    """Извлекает ID видео из URL"""
    if platform == 'youtube':
        parsed = urlparse(url)
        if 'youtu.be' in url:
            return parsed.path.lstrip('/')
        query = parse_qs(parsed.query)
        return query.get('v', [''])[0]
    elif platform == 'rutube':
        match = re.search(r'/video/([a-f0-9]+)', url)
        return match.group(1) if match else ''
    elif platform == 'vk':
        match = re.search(r'video-?(\d+_\d+)', url)
        return match.group(1) if match else ''
    return ''


def get_video_info(url: str) -> dict:
    """Получает информацию о видео для предпросмотра"""
    try:
        import yt_dlp
        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                return {
                    'title': info.get('title', 'Без названия'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'channel': info.get('uploader', 'Неизвестный канал'),
                    'platform': detect_platform(url)
                }
    except Exception as e:
        print(f"Ошибка получения информации о видео: {e}")
    return None


# ============================================
# ФОНОВАЯ ОБРАБОТКА ВИДЕО
# ============================================

def process_video(url: str, task_id: str, use_gpt: bool = True):
    """Фоновый процесс транскрибации видео"""
    try:
        print(f"🔵 [TASK {task_id}] Начинаем обработку видео: {url}")

        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['message'] = 'Начинаем обработку видео...'
        tasks[task_id]['progress'] = 0

        # 1. Скачивание
        print(f"🔵 [TASK {task_id}] Скачивание аудио...")
        tasks[task_id]['message'] = 'Скачивание аудио...'
        tasks[task_id]['progress'] = 10
        audio_file, title = download_audio(url)

        if not audio_file or not audio_file.exists():
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = 'Не удалось скачать аудио'
            tasks[task_id]['progress'] = 0
            print(f"🔴 [TASK {task_id}] ОШИБКА: не удалось скачать аудио")
            return

        tasks[task_id]['title'] = title
        tasks[task_id]['message'] = f'Аудио скачано: {audio_file.name}'
        tasks[task_id]['progress'] = 25
        print(f"✅ [TASK {task_id}] Аудио скачано: {audio_file.name}")

        # 2. Конвертация
        print(f"🔵 [TASK {task_id}] Конвертация в WAV...")
        tasks[task_id]['message'] = 'Конвертация аудио в WAV...'
        tasks[task_id]['progress'] = 30
        wav_file = OUTPUT_DIRS["audio"] / f"converted_{audio_file.stem}.wav"
        success, error = convert_to_wav(str(audio_file), str(wav_file))

        if not success:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = f'Ошибка конвертации: {error}'
            tasks[task_id]['progress'] = 0
            print(f"🔴 [TASK {task_id}] ОШИБКА конвертации: {error}")
            return

        tasks[task_id]['message'] = 'Аудио сконвертировано'
        tasks[task_id]['progress'] = 40
        print(f"✅ [TASK {task_id}] Аудио сконвертировано")

        # 3. Транскрибация
        print(f"🔵 [TASK {task_id}] Начинаем транскрибацию...")
        tasks[task_id]['message'] = 'Транскрибация аудио (это может занять время)...'
        tasks[task_id]['progress'] = 50

        transcription, segments = transcribe_audio_with_timestamps(wav_file, VOSK_MODEL_DIR)

        if not transcription or not segments:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = 'Не удалось распознать текст'
            tasks[task_id]['progress'] = 0
            print(f"🔴 [TASK {task_id}] ОШИБКА: транскрибация вернула None")
            return

        tasks[task_id]['message'] = f'Распознано {len(segments)} сегментов'
        tasks[task_id]['progress'] = 70
        print(f"✅ [TASK {task_id}] Транскрибация завершена, {len(segments)} сегментов")

        # 4. Исправление текста
        print(f"🔵 [TASK {task_id}] Исправление текста...")
        tasks[task_id]['message'] = 'Исправление текста...'
        tasks[task_id]['progress'] = 80

        if use_gpt:
            yandex_client = YandexGPT()
            if len(transcription) > 3000:
                corrected_text = correct_long_text(transcription)
            else:
                corrected_text = yandex_client.correct_text(transcription)
        else:
            corrected_text = None

        if corrected_text is None:
            corrected_text = simple_correction(transcription)
            tasks[task_id]['message'] = 'Текст исправлен (базовая коррекция)'
        else:
            tasks[task_id]['message'] = 'Текст исправлен (YandexGPT)'

        print(f"✅ [TASK {task_id}] Текст исправлен")

        # 5. Пост-процессинг
        tasks[task_id]['message'] = 'Расстановка знаков препинания...'
        corrected_text = process_transcription(corrected_text)
        print(f"✅ [TASK {task_id}] Знаки препинания расставлены")

        # 6. Форматирование
        formatted_output = format_transcription_with_timestamps(segments, corrected_text)

        # 7. Сохранение
        safe_title = sanitize_filename(title)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.txt"
        output_file = OUTPUT_DIRS["transcriptions"] / filename

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_output)

        # 8. Сохраняем результат
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['message'] = 'Готово!'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['result'] = {
            'text': corrected_text,
            'segments': segments,
            'segments_count': len(segments),
            'char_count': len(corrected_text),
            'filename': filename,
            'filepath': str(output_file),
            'title': title
        }

        print(f"✅ [TASK {task_id}] ГОТОВО! Результат сохранен: {filename}")

        # Очистка временных файлов
        try:
            if audio_file.exists():
                audio_file.unlink()
            if wav_file.exists():
                wav_file.unlink()
            print(f"✅ [TASK {task_id}] Временные файлы удалены")
        except Exception as e:
            print(f"⚠️ [TASK {task_id}] Не удалось удалить временные файлы: {e}")

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = f'Ошибка: {str(e)}'
        tasks[task_id]['progress'] = 0
        print(f"🔴 [TASK {task_id}] КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        tasks[task_id]['traceback'] = traceback.format_exc()


# ============================================
# МАРШРУТЫ FLASK
# ============================================

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Получение информации о видео для предпросмотра"""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    if not validate_url(url):
        return jsonify({'error': 'Некорректный URL'}), 400

    info = get_video_info(url)
    if info:
        return jsonify(info)
    return jsonify({'error': 'Не удалось получить информацию о видео'}), 404


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """Запуск транскрибации"""
    data = request.get_json()
    url = data.get('url', '').strip()
    use_gpt = data.get('use_gpt', True)

    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    if not validate_url(url):
        return jsonify({'error': 'Некорректный URL. Поддерживаются YouTube, Rutube, VK Video'}), 400

    # Создаем задачу
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    tasks[task_id] = {
        'status': 'pending',
        'message': 'Задача создана',
        'progress': 0,
        'url': url,
        'use_gpt': use_gpt,
        'created_at': datetime.now().isoformat()
    }

    # Запускаем в фоновом потоке
    thread = threading.Thread(target=process_video, args=(url, task_id, use_gpt))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id, 'status': 'pending'})


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Получение статуса задачи"""
    if task_id not in tasks:
        return jsonify({'error': 'Задача не найдена'}), 404

    task = tasks[task_id]
    response = {
        'status': task.get('status', 'unknown'),
        'message': task.get('message', ''),
        'progress': task.get('progress', 0),
        'title': task.get('title', '')
    }

    if task.get('status') == 'completed':
        response['result'] = task.get('result', {})

    if task.get('status') == 'error':
        response['error_message'] = task.get('message', '')

    return jsonify(response)


@app.route('/api/download/<filename>')
def download_file(filename):
    """Скачивание результата"""
    file_path = OUTPUT_DIRS["transcriptions"] / filename
    if not file_path.exists():
        return jsonify({'error': 'Файл не найден'}), 404

    return send_file(file_path, as_attachment=True, download_name=filename)


@app.route('/api/check')
def check_environment():
    """Проверка окружения"""
    env_status = {
        'ffmpeg': False,
        'vosk': False,
        'yandex_gpt': False,
        'ready': False
    }

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        env_status['ffmpeg'] = True
    except:
        pass

    if VOSK_MODEL_DIR.exists():
        env_status['vosk'] = True

    try:
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv("YANDEX_API_KEY") and os.getenv("YANDEX_FOLDER_ID"):
            env_status['yandex_gpt'] = True
    except:
        pass

    env_status['ready'] = all([env_status['ffmpeg'], env_status['vosk']])
    return jsonify(env_status)


# ============================================
# ЗАПУСК СЕРВЕРА
# ============================================

if __name__ == '__main__':
    if setup_environment():
        print("=" * 60)
        print("🚀 TranscribeFlow v2.0")
        print(f"🌐 Веб-интерфейс: http://{WEB_HOST}:{WEB_PORT}")
        print("📹 Поддержка: YouTube | Rutube | VK Video")
        print("=" * 60)
        app.run(debug=WEB_DEBUG, host=WEB_HOST, port=WEB_PORT)
    else:
        print("❌ Ошибка настройки окружения. Проверьте FFmpeg и Vosk.")