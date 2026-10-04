"""
Коррекция и форматирование текста
Все настройки импортируются из config.py
"""

import re
from typing import List, Dict, Optional


def simple_correction(text: str) -> str:
    """Простая коррекция текста без внешних API"""
    if not text:
        return text

    # Убираем лишние запятые (если их слишком много)
    words = text.split()
    if len(words) > 0:
        comma_count = text.count(',')
        if comma_count > len(words) * 0.15:
            text = text.replace(',', '')

    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text).strip()

    # Убираем множественные точки
    text = re.sub(r'\.{2,}', '.', text)

    # Добавляем пробел после точки, если его нет
    text = re.sub(r'\.([А-ЯA-Z])', r'. \1', text)

    # Исправляем распространенные ошибки
    corrections = {
        'что бы': 'чтобы',
        'как бы': 'какбы',
        'в месте': 'вместе',
        'на пример': 'например',
        'из за': 'из-за',
        'во время': 'во время',
        'к стати': 'кстати',
        'в общем': 'в общем',
        'значит': 'значит',
    }

    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)

    # Первая буква с большой
    if text:
        text = text[0].upper() + text[1:]

    return text


def format_transcription_with_timestamps(
        segments: List[Dict],
        corrected_text: str = None
) -> str:
    """Форматирует транскрипцию с таймингами"""
    result = []
    result.append("=" * 60)
    result.append("ТРАНСКРИПЦИЯ ВИДЕО С ТАЙМИНГАМИ")
    result.append("=" * 60)
    result.append("")

    for i, seg in enumerate(segments, 1):
        start_min = int(seg['start'] // 60)
        start_sec = int(seg['start'] % 60)
        end_min = int(seg['end'] // 60)
        end_sec = int(seg['end'] % 60)

        time_str = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"
        # Убираем лишние запятые из текста сегмента
        segment_text = seg['text'].replace(',', ' ')
        segment_text = ' '.join(segment_text.split())
        result.append(f"{time_str} {segment_text}")

    result.append("")
    result.append("=" * 60)
    result.append("ИТОГОВЫЙ ТЕКСТ (ИСПРАВЛЕННЫЙ):")
    result.append("=" * 60)

    if corrected_text:
        # Убираем лишние запятые из исправленного текста
        corrected_text = corrected_text.replace(',', ' ')
        corrected_text = ' '.join(corrected_text.split())
        result.append(corrected_text)

    return '\n'.join(result)