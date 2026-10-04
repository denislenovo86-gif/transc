"""
Утилиты для работы с аудио
Конвертация в WAV для Vosk
"""

from pydub import AudioSegment
from pathlib import Path
from typing import Tuple


def convert_to_wav(input_path: str, output_path: str) -> Tuple[bool, str]:
    """
    Конвертирует аудио в формат WAV (16kHz, моно) для Vosk
    Поддерживает mp3, m4a, opus, webm, wav
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Определяем формат по расширению
        ext = input_path.suffix.lower()

        print(f"🔄 Конвертация {ext} → WAV...")

        if ext == '.mp3':
            audio = AudioSegment.from_mp3(str(input_path))
        elif ext == '.wav':
            audio = AudioSegment.from_wav(str(input_path))
        elif ext == '.m4a':
            audio = AudioSegment.from_file(str(input_path), format='m4a')
        elif ext == '.opus':
            audio = AudioSegment.from_file(str(input_path), format='opus')
        elif ext == '.webm':
            audio = AudioSegment.from_file(str(input_path), format='webm')
        else:
            return False, f"Неподдерживаемый формат: {ext}"

        # 🔥 Конвертируем в нужный формат для Vosk
        # 16000 Гц, 1 канал (моно), 16-бит
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        # Сохраняем
        audio.export(str(output_path), format="wav")

        print(f"✅ Конвертация завершена: {output_path.name}")
        return True, ""

    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")
        return False, str(e)