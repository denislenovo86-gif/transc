"""
Модуль для работы с YandexGPT API
Настройки импортируются из config.py
"""

import os
import requests
import json
from typing import Optional
from pathlib import Path

# 🔥 Импортируем настройки из config
from config import MAX_GPT_TEXT_LENGTH, ENV_FILE

# Пробуем загрузить настройки из .env
try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    else:
        load_dotenv()
except ImportError:
    pass


class YandexGPT:
    """Клиент для YandexGPT API"""

    def __init__(self, api_key: str = None, folder_id: str = None):
        self.api_key = api_key or os.getenv("YANDEX_API_KEY")
        self.folder_id = folder_id or os.getenv("YANDEX_FOLDER_ID")

        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        if not self.api_key or not self.folder_id:
            print("⚠️ YandexGPT не настроен. Создайте файл .env с YANDEX_API_KEY и YANDEX_FOLDER_ID")

    def correct_text(self, text: str, temperature: float = 0.1) -> Optional[str]:
        """Исправляет текст с помощью YandexGPT"""
        if not self.api_key or not self.folder_id:
            print("❌ YandexGPT не настроен. Исправление текста невозможно.")
            return None

        try:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }

            system_prompt = """Ты - профессиональный редактор текста на русском языке.

ТВОЯ ГЛАВНАЯ ЗАДАЧА: ПРАВИЛЬНО РАССТАВИТЬ ЗНАКИ ПРЕПИНАНИЯ!

ОБЯЗАТЕЛЬНО:
1. Поставь запятые ВЕЗДЕ, где они нужны по правилам русского языка
2. Поставь точки в конце каждого предложения
3. Начинай каждое предложение с большой буквы
4. Исправь орфографические ошибки
5. Удали слова-паразиты

Выдавай ТОЛЬКО исправленный текст, без пояснений."""

            user_prompt = f"""Расставь ВСЕ знаки препинания и исправь ошибки:

{text}"""

            models_to_try = [
                f"gpt://{self.folder_id}/yandexgpt-lite",
                f"gpt://{self.folder_id}/yandexgpt-lite/latest",
                f"gpt://{self.folder_id}/yandexgpt",
                f"gpt://{self.folder_id}/yandexgpt/latest",
            ]

            last_error = None

            for model_uri in models_to_try:
                try:
                    print(f"🔄 Пробуем модель: {model_uri}")

                    data = {
                        "modelUri": model_uri,
                        "completionOptions": {
                            "stream": False,
                            "temperature": temperature,
                            "maxTokens": "4000"
                        },
                        "messages": [
                            {"role": "system", "text": system_prompt},
                            {"role": "user", "text": user_prompt}
                        ]
                    }

                    response = requests.post(
                        self.base_url,
                        headers=headers,
                        json=data,
                        timeout=60
                    )

                    print(f"📡 HTTP Status: {response.status_code}")

                    if response.status_code == 200:
                        result = response.json()
                        corrected = result['result']['alternatives'][0]['message']['text']
                        print(f"✅ Текст исправлен через YandexGPT")
                        return corrected
                    else:
                        last_error = response.text

                except Exception as e:
                    last_error = str(e)
                    continue

            print(f"❌ Все модели не сработали. Последняя ошибка: {last_error}")
            return None

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None


def correct_text_with_yandex(
    text: str,
    api_key: str = None,
    folder_id: str = None
) -> Optional[str]:
    """Упрощенная функция для исправления текста"""
    client = YandexGPT(api_key, folder_id)
    return client.correct_text(text)


def correct_long_text(
    text: str,
    chunk_size: int = 1500,
    api_key: str = None,
    folder_id: str = None
) -> str:
    """Исправляет длинный текст, разбивая на части"""
    if len(text) <= chunk_size:
        result = correct_text_with_yandex(text, api_key, folder_id)
        return result if result else text

    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) <= chunk_size:
            current_chunk.append(sentence)
            current_length += len(sentence)
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    print(f"📝 Текст разбит на {len(chunks)} частей")

    corrected_parts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"   Обработка части {i}/{len(chunks)}...")
        result = correct_text_with_yandex(chunk, api_key, folder_id)
        corrected_parts.append(result if result else chunk)

    return ' '.join(corrected_parts)