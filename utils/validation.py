from config import SUPPORTED_PLATFORMS


def validate_url(url: str) -> bool:
    """Проверяет, является ли строка корректным URL поддерживаемой платформы"""
    if not url or not isinstance(url, str):
        return False

    url = url.strip().lower()

    # Проверяем все поддерживаемые платформы
    for platform, domains in SUPPORTED_PLATFORMS.items():
        for domain in domains:
            if domain in url:
                return True

    return False


def detect_platform(url: str) -> str:
    """Определяет платформу по URL"""
    url = url.strip().lower()

    for platform, domains in SUPPORTED_PLATFORMS.items():
        for domain in domains:
            if domain in url:
                return platform

    return 'unknown'