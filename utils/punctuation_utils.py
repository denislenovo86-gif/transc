"""
Утилиты для принудительной расстановки знаков препинания
"""
import re
from typing import List, Dict, Optional


def add_punctuation(text: str) -> str:
    """
    Принудительно расставляет знаки препинания в тексте
    """
    if not text:
        return text

    # 1. Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Убираем запятые, которые стоят через каждое слово (ошибка распознавания)
    # Если в тексте больше 3 запятых на 10 слов - это ошибка
    words = text.split()
    if len(words) > 0:
        comma_count = text.count(',')
        # Если запятых больше 20% от слов - удаляем лишние
        if comma_count > len(words) * 0.2:
            # Убираем все запятые и пробуем расставить заново
            text = text.replace(',', '')
            text = re.sub(r'\s+', ' ', text).strip()

    # 3. Добавляем точку в конце, если её нет
    if text and text[-1] not in '.!?':
        text += '.'

    # 4. Каждое предложение начинаем с большой буквы
    sentences = re.split(r'(?<=[.!?])\s+', text)
    corrected_sentences = []

    for sent in sentences:
        if sent:
            # Первая буква заглавная
            sent = sent[0].upper() + sent[1:] if len(sent) > 1 else sent.upper()
            corrected_sentences.append(sent)

    return ' '.join(corrected_sentences)


def add_commas(text: str) -> str:
    """
    Расставляет запятые в предложении по основным правилам (без перебора)
    """
    if not text:
        return text

    # Сначала убираем все существующие запятые (чтобы избежать дублирования)
    # Но сохраняем точки и другие знаки
    text = text.replace(',', '')
    text = re.sub(r'\s+', ' ', text).strip()

    # Расставляем запятые заново по правилам
    # Запятая перед союзами (только если они не в начале предложения)
    conjunctions = ['что', 'чтобы', 'когда', 'если', 'потому что', 'так как', 'хотя', 'будто', 'пока', 'как', 'где', 'куда', 'откуда']
    for conj in conjunctions:
        # Ищем союз в середине предложения (не в начале)
        pattern = r'(\s)({})(\s)'.format(conj)
        text = re.sub(pattern, r', \2 ', text)

    # Запятая перед "но", "а", "да" (в значении "но")
    text = re.sub(r'\s(но|а)\s', r', \1 ', text)

    # Запятая перед "который", "которая", "которое"
    text = re.sub(r'\s(который|которая|которое|которые)\s', r', \1 ', text)

    # Убираем двойные запятые
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r',\s+,\s+', ', ', text)

    # Убираем запятые в начале предложения
    text = re.sub(r'^,\s+', '', text)

    return text


def fix_case(text: str) -> str:
    """
    Исправляет регистр букв (первая буква предложения заглавная)
    """
    if not text:
        return text

    sentences = re.split(r'(?<=[.!?])\s+', text)
    fixed = []

    for sent in sentences:
        if sent:
            sent = sent.strip()
            if sent:
                sent = sent[0].upper() + sent[1:] if len(sent) > 1 else sent.upper()
                fixed.append(sent)

    return '. '.join(fixed) if fixed else text


def process_transcription(text: str) -> str:
    """
    Полная обработка транскрипции: исправление регистра + запятые + точки
    """
    if not text:
        return text

    # Сначала убираем лишние запятые
    text = text.replace(',', ' ')
    text = re.sub(r'\s+', ' ', text).strip()

    # Исправляем регистр
    text = fix_case(text)

    # Расставляем запятые
    text = add_commas(text)

    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text).strip()

    # Добавляем точку в конце
    if text and text[-1] not in '.!?':
        text += '.'

    return text