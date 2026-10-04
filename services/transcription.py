"""
Транскрибация аудио с таймингами через Vosk
Все пути импортируются из config.py
"""

import wave
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# 🔥 Импортируем пути и настройки из config
from config import VOSK_MODEL_DIR, SAMPLE_RATE, SEGMENT_DURATION

# Импортируем Vosk
try:
    from vosk import Model, KaldiRecognizer
    print("✅ Vosk импортирован")
except Exception as e:
    print(f"⚠️ Ошибка Vosk: {e}")
    # Заглушки
    class Model:
        def __init__(self, path):
            pass
    class KaldiRecognizer:
        def __init__(self, model, rate):
            pass
        def AcceptWaveform(self, data):
            return False
        def Result(self):
            return '{"text": ""}'
        def FinalResult(self):
            return '{"text": ""}'
        def SetWords(self, val):
            pass


def transcribe_audio_with_timestamps(
    file_path: Path,
    model_path: Path = None
) -> Tuple[Optional[str], Optional[List[Dict]]]:
    """
    Транскрибирует аудио файл с временными метками
    Возвращает: (полный_текст, список_фрагментов_с_таймингами)
    """
    # Если путь не указан — используем из config
    if model_path is None:
        model_path = VOSK_MODEL_DIR

    try:
        if not model_path.exists():
            raise FileNotFoundError(f"Модель Vosk не найдена: {model_path}")

        print(f"Загрузка модели из {model_path}...")
        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.SetWords(True)

        print("Начинаем транскрибацию с таймингами...")

        full_text = []
        segments = []
        current_segment_words = []
        current_segment_text = []
        current_start = 0

        with wave.open(str(file_path), "rb") as wf:
            if wf.getnchannels() != 1:
                print(f"Внимание: аудио имеет {wf.getnchannels()} каналов")
            if wf.getframerate() != SAMPLE_RATE:
                print(f"Внимание: частота {wf.getframerate()} Гц (ожидается {SAMPLE_RATE})")

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if 'result' in result:
                        words = result['result']
                        if words:
                            current_segment_words.extend(words)
                            current_segment_text.append(
                                ' '.join([w.get('word', '') for w in words])
                            )

                            if len(current_segment_words) > 0:
                                last_word = current_segment_words[-1]
                                if last_word.get('end', 0) - current_start >= SEGMENT_DURATION:
                                    segment_text = ' '.join(current_segment_text)
                                    segment_text = ' '.join(segment_text.split())

                                    segments.append({
                                        'start': current_start,
                                        'end': last_word.get('end', current_start + SEGMENT_DURATION),
                                        'text': segment_text
                                    })
                                    full_text.append(segment_text)
                                    current_segment_words = []
                                    current_segment_text = []
                                    current_start = last_word.get('end', 0)

            # Финальный результат
            final_result = json.loads(recognizer.FinalResult())
            if 'result' in final_result:
                words = final_result['result']
                if words:
                    current_segment_words.extend(words)
                    current_segment_text.append(
                        ' '.join([w.get('word', '') for w in words])
                    )

                    if current_segment_words:
                        segment_text = ' '.join(current_segment_text)
                        segment_text = ' '.join(segment_text.split())

                        segments.append({
                            'start': current_start,
                            'end': current_segment_words[-1].get('end', 0),
                            'text': segment_text
                        })
                        full_text.append(segment_text)

        if not full_text:
            print("Внимание: текст не распознан")
            return None, None

        final_text = ' '.join(full_text)
        final_text = ' '.join(final_text.split())

        print(f"✓ Транскрибация завершена. Распознано {len(segments)} сегментов")
        print(f"✓ Всего символов: {len(final_text)}")
        return final_text, segments

    except FileNotFoundError as e:
        print(f"Ошибка: {e}")
        return None, None
    except Exception as e:
        print(f"Ошибка транскрибации: {e}")
        import traceback
        traceback.print_exc()
        return None, None