import sys
import os
from pathlib import Path
from config import FFMPEG_DIR, VOSK_MODEL_DIR, OUTPUT_DIRS, SUPPORTED_PLATFORMS
from services import download_audio, transcribe_audio_with_timestamps
from services.yandex_gpt import YandexGPT, correct_text_with_yandex, correct_long_text
from services.text_correction import format_transcription_with_timestamps, simple_correction
from utils.audio_utils import convert_to_wav
from utils.file_utils import sanitize_filename, ensure_directory_exists
from utils.validation import validate_url, detect_platform
from utils.punctuation_utils import process_transcription
import subprocess


def setup_environment() -> bool:
    """Настройка окружения перед запуском"""
    print("\n=== Настройка окружения ===")

    # Проверяем FFmpeg
    ffmpeg_path = str(FFMPEG_DIR)
    if ffmpeg_path not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]

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


def show_supported_platforms():
    """Показывает поддерживаемые платформы"""
    print("\nПоддерживаемые платформы:")
    for platform, domains in SUPPORTED_PLATFORMS.items():
        print(f"  • {platform.upper()}: {', '.join(domains)}")


def main():
    print("=" * 50)
    print("     Универсальный Транскрибатор v2.0")
    print("     Поддержка: YouTube | Rutube | VK Video")
    print("     ✨ НОВО: Тайминги + Нейрокоррекция (YandexGPT)")
    print("=" * 50)

    # Настройка окружения
    if not setup_environment():
        print("\nОшибка настройки окружения. Завершение работы.")
        sys.exit(1)

    show_supported_platforms()

    print("\n" + "=" * 50)
    url = input("Введите URL видео: ").strip()

    if not validate_url(url):
        print("Ошибка: некорректный URL")
        print("Поддерживаются ссылки с YouTube, Rutube и VK Video")
        sys.exit(1)

    platform = detect_platform(url)
    print(f"Определена платформа: {platform.upper()}")

    # Скачивание аудио
    print("\n" + "=" * 50)
    print("[1/3] Скачивание аудио")
    print("-" * 50)

    audio_file, title = download_audio(url)
    if not audio_file or not audio_file.exists():
        print("Ошибка: не удалось скачать аудио")
        sys.exit(1)

    print(f"✓ Аудио скачано: {audio_file.name}")

    # Конвертация в нужный формат
    print("\n" + "=" * 50)
    print("[2/3] Конвертация аудио")
    print("-" * 50)

    wav_file = OUTPUT_DIRS["audio"] / f"converted_{audio_file.stem}.wav"
    success, error = convert_to_wav(str(audio_file), str(wav_file))

    if not success:
        print(f"Ошибка конвертации: {error}")
        sys.exit(1)

    print(f"✓ Аудио сконвертировано: {wav_file.name}")

    # Транскрибация с таймингами
    print("\n" + "=" * 50)
    print("[3/3] Транскрибация аудио с таймингами")
    print("-" * 50)

    transcription, segments = transcribe_audio_with_timestamps(wav_file, VOSK_MODEL_DIR)

    if not transcription or not segments:
        print("Ошибка: не удалось распознать текст")
        sys.exit(1)

    # Исправление текста через YandexGPT или простую коррекцию
    print("\n" + "=" * 50)
    print("📝 Исправление текста: расстановка запятых и коррекция смысла")
    print("-" * 50)

    # Создаем клиент YandexGPT
    yandex_client = YandexGPT()

    # Проверяем длину текста
    if len(transcription) > 3000:
        print(f"⚠️ Текст длинный ({len(transcription)} символов), разбиваем на части...")
        corrected_text = correct_long_text(transcription)
    else:
        # Пробуем исправить через YandexGPT
        corrected_text = yandex_client.correct_text(transcription)

    # Если YandexGPT не настроен или ошибка - используем простую коррекцию
    if corrected_text is None:
        print("ℹ️ Используем встроенную коррекцию (без нейросети)")
        corrected_text = simple_correction(transcription)
    else:
        print("✅ Текст исправлен через YandexGPT")

    # ПРИНУДИТЕЛЬНО расставляем знаки препинания (пост-процессинг)
    print("🔧 Принудительная расстановка знаков препинания...")
    corrected_text = process_transcription(corrected_text)
    print("✅ Знаки препинания расставлены")

    # Форматирование с таймингами
    formatted_output = format_transcription_with_timestamps(segments, corrected_text)

    # Сохранение результата
    safe_title = sanitize_filename(title)[:50]
    output_file = OUTPUT_DIRS["transcriptions"] / f"{safe_title}_with_timestamps.txt"

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        print(f"✓ Результат сохранен: {output_file}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        sys.exit(1)

    # Вывод результата
    print("\n" + "=" * 50)
    print("Результат транскрибации (первые 500 символов):")
    print("-" * 50)

    preview = corrected_text[:500]
    if len(corrected_text) > 500:
        preview += "..."
    print(preview)

    print("\n" + "=" * 50)
    print(f"Полный текст с таймингами сохранен в: {output_file}")
    print(f"Размер текста: {len(transcription)} символов")
    print(f"Количество сегментов: {len(segments)}")

    # Очистка временных файлов
    try:
        if audio_file.exists():
            audio_file.unlink()
        if wav_file.exists():
            wav_file.unlink()
        print("\n✓ Временные файлы удалены")
    except Exception as e:
        print(f"\nВнимание: не удалось удалить временные файлы: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\nНепредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)