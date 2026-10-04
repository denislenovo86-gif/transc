"""
Скачивание ТОЛЬКО АУДИО с YouTube, Rutube, VK Video
"""

import yt_dlp
from pathlib import Path
from typing import Tuple, Optional

from config import YT_DLP_BASE_OPTS, PLATFORM_OPTS, OUTPUT_DIRS
from utils.file_utils import sanitize_filename
from utils.validation import detect_platform


def download_audio(url: str) -> Tuple[Optional[Path], Optional[str]]:
    """
    Скачивает ТОЛЬКО аудиодорожку с YouTube, Rutube или VK Video
    """
    # Определяем платформу
    platform = detect_platform(url)
    if platform == 'unknown':
        print(f"Платформа не определена. Поддерживаются: YouTube, Rutube, VK Video")
        return None, None

    print(f"\nПлатформа: {platform.upper()}")

    # 🔥 Получаем настройки для платформы
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

            # 🔥 Ищем ТОЛЬКО аудио формат
            audio_formats = []
            if 'formats' in info:
                for f in info['formats']:
                    # Ищем форматы БЕЗ видео
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        audio_formats.append(f)

                # Сортируем по размеру — сначала маленькие
                audio_formats.sort(key=lambda x: x.get('filesize', 0) or x.get('filesize_approx', 999999999))

            # 🔥 Если нашли аудиоформаты — используем самый маленький
            if audio_formats:
                best_audio = audio_formats[0]
                print(f"🎵 Найден аудиоформат: {best_audio.get('format_id')} ({best_audio.get('ext')})")
                print(f"   Размер: {best_audio.get('filesize', 0) / 1024 / 1024:.2f} MB")

                # Переопределяем формат
                opts['format'] = best_audio.get('format_id')
            else:
                # Если нет — используем fallback
                print("⚠️ Аудиоформаты не найдены, используем fallback")
                opts['format'] = 'worstaudio/worst'

            # 🔥 Скачиваем
            print("\n🎵 Скачиваем ТОЛЬКО аудиодорожку...")
            ydl.download([url])

            # Ищем скачанный файл
            safe_title = sanitize_filename(title)

            possible_names = [safe_title]
            if platform == 'rutube':
                possible_names.insert(0, f"rutube_{safe_title}")
            elif platform == 'vk':
                possible_names.insert(0, f"vk_{safe_title}")

            # 🔥 Ищем mp3
            audio_file = None
            for name in possible_names:
                for ext in ['.mp3', '.m4a', '.opus', '.webm', '.wav']:
                    test_file = OUTPUT_DIRS["audio"] / f"{name}{ext}"
                    if test_file.exists():
                        audio_file = test_file
                        break
                if audio_file:
                    break

            # Если не нашли — ищем любой недавний аудиофайл
            if not audio_file:
                recent_files = sorted(
                    OUTPUT_DIRS["audio"].iterdir(),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                for f in recent_files:
                    if f.suffix in ['.mp3', '.m4a', '.opus', '.webm', '.wav']:
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
        else:
            print(f"Ошибка скачивания: {error_msg}")

        return None, None

    except Exception as e:
        print(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        return None, None