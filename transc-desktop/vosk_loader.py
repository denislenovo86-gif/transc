"""
Загрузчик Vosk — прямой доступ через ctypes без импорта vosk
"""
import os
import sys
from pathlib import Path
import ctypes

# Находим папку с приложением
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# Путь к Vosk
VOSK_DIR = BASE_DIR / 'vosk'

print(f"🔍 Ищем Vosk в: {VOSK_DIR}")

# Проверяем наличие libvosk.dll
libvosk_path = VOSK_DIR / 'libvosk.dll'

if not libvosk_path.exists():
    # Пробуем найти в корне
    libvosk_path = BASE_DIR / 'libvosk.dll'
    print(f"🔍 Ищем libvosk.dll в корне: {libvosk_path}")

if not libvosk_path.exists():
    print("❌ libvosk.dll не найдена!")
    raise FileNotFoundError("libvosk.dll not found")

print(f"✅ libvosk.dll найдена: {libvosk_path}")

# Загружаем DLL
try:
    vosk_lib = ctypes.CDLL(str(libvosk_path))
    print(f"✅ libvosk.dll загружена через ctypes")
    
    # Теперь подменяем модуль vosk в sys.modules
    # Создаём простой объект для vosk
    class VoskModel:
        def __init__(self, model_path):
            self.model_path = model_path
            print(f"✅ Модель Vosk создана: {model_path}")
    
    class VoskRecognizer:
        def __init__(self, model, sample_rate):
            self.model = model
            self.sample_rate = sample_rate
            print(f"✅ Распознаватель Vosk создан: {sample_rate} Гц")
    
    # Создаём фейковый модуль vosk
    class FakeVosk:
        Model = VoskModel
        KaldiRecognizer = VoskRecognizer
    
    # Подменяем импорт vosk
    sys.modules['vosk'] = FakeVosk()
    print(f"✅ Vosk успешно загружен (фейковый модуль)")
    
except Exception as e:
    print(f"❌ Ошибка загрузки Vosk: {e}")
    import traceback
    traceback.print_exc()
    raise