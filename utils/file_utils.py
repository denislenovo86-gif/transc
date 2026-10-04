import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов"""
    # Заменяем недопустимые символы на _
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Убираем лишние пробелы
    filename = ' '.join(filename.split())
    # Ограничиваем длину
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def ensure_directory_exists(path: Path) -> bool:
    """Создает директорию, если она не существует"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Ошибка создания директории {path}: {e}")
        return False