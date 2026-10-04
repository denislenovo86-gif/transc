import yt_dlp
from pathlib import Path
from typing import Tuple, Optional
from config import YT_DLP_BASE_OPTS, PLATFORM_OPTS, OUTPUT_DIRS
from utils.file_utils import sanitize_filename
from utils.validation import detect_platform


def download_audio(url: str) -> Tuple[Optional[Path], Optional[str]]:
    """Скачивает аудио с YouTube, Rutube или VK Video"""

    # Определяем платформу
    platform = detect_platform(url)
    if platform == 'unknown':
        print(f"Платформа не определена. Поддерживаются: YouTube, Rutube, VK Video")
        return None, None

    print(f"\nПлатформа: {platform.upper()}")

    # Получаем настройки для платформы
    platform_opts = PLATFORM_OPTS.get(platform, {})

    # Объединяем настройки
    opts = YT_DLP_BASE_OPTS.copy()
    opts.update(platform_opts)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Получаем информацию о видео
            print("Получение информации о видео...")
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Не удалось получить информацию о видео")

            title = info.get('title', 'audio')
            duration = info.get('duration', 0)

            print(f"Название: {title}")
            print(f"Длительность: {duration // 60}:{duration % 60:02d}")

            # Скачиваем
            print("\nНачинаем скачивание...")
            ydl.download([url])

            # Ищем скачанный файл
            safe_title = sanitize_filename(title)

            # Пробуем разные варианты имен файлов
            possible_names = [safe_title]
            if platform == 'rutube':
                possible_names.insert(0, f"rutube_{safe_title}")
            elif platform == 'vk':
                possible_names.insert(0, f"vk_{safe_title}")

            audio_file = None
            for name in possible_names:
                for ext in ['.wav', '.mp3', '.m4a', '.webm', '.opus']:
                    test_file = OUTPUT_DIRS["audio"] / f"{name}{ext}"
                    if test_file.exists():
                        audio_file = test_file
                        break
                if audio_file:
                    break

            # Если не нашли, ищем любой недавний файл
            if not audio_file:
                recent_files = sorted(
                    OUTPUT_DIRS["audio"].iterdir(),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                for f in recent_files:
                    if f.suffix in ['.wav', '.mp3', '.m4a', '.webm', '.opus']:
                        audio_file = f
                        break

            if not audio_file or not audio_file.exists():
                raise FileNotFoundError(f"Аудио файл не найден")

            file_size_mb = audio_file.stat().st_size / 1024 / 1024
            print(f"\n✓ Аудио скачано: {audio_file.name} ({file_size_mb:.2f} MB)")
            return audio_file, title

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            print("Ошибка: видео является приватным")
        elif "Video unavailable" in error_msg:
            print("Ошибка: видео недоступно")
        elif "login" in error_msg.lower() or "auth" in error_msg.lower():
            print("Ошибка: требуется авторизация")
        else:
            print(f"Ошибка скачивания: {error_msg}")

        return None, None

    except Exception as e:
        print(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        return None, None