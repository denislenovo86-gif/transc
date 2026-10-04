"""
Патч для Vosk — переопределяем путь к DLL
"""
import os
import sys
from pathlib import Path

def patch_vosk():
    """Подменяем путь к DLL для Vosk"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        vosk_path = base_path / 'vosk'
        
        if vosk_path.exists():
            # Добавляем путь в sys.path
            if str(vosk_path) not in sys.path:
                sys.path.insert(0, str(vosk_path))
            
            # Добавляем в PATH
            os.environ["PATH"] = str(vosk_path) + os.pathsep + os.environ.get("PATH", "")
            
            # 🔥 ПЕРЕОПРЕДЕЛЯЕМ ФУНКЦИЮ open_dll в vosk
            try:
                import vosk
                original_open_dll = vosk.open_dll
                
                def patched_open_dll():
                    """Переопределённая функция open_dll"""
                    import os
                    from pathlib import Path
                    
                    # Ищем DLL в папке vosk
                    dll_path = vosk_path / 'libvosk.dll'
                    if dll_path.exists():
                        # Загружаем DLL напрямую
                        import ctypes
                        return ctypes.CDLL(str(dll_path))
                    
                    # Если не нашли — пробуем оригинальную
                    return original_open_dll()
                
                vosk.open_dll = patched_open_dll
                print(f"✅ Vosk патч применён: {vosk_path}")
            except Exception as e:
                print(f"⚠️ Ошибка патча Vosk: {e}")
            
            return True
    return False

# Применяем патч
patch_vosk()