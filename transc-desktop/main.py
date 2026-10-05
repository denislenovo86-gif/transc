"""
TranscribeFlow Desktop — Универсальный Транскрибатор v2.0
Все пути импортируются из config.py
"""
import sys
import os
from pathlib import Path
import threading
import requests

# 🔥 Добавляем родительскую папку в путь
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# 🔥 ИМПОРТИРУЕМ ВСЕ ПУТИ ИЗ CONFIG
from config import (
    BASE_DIR, FFMPEG_DIR, VOSK_MODEL_DIR,
    OUTPUT_DIRS, OUTPUT_BASE,
    SAMPLE_RATE, SEGMENT_DURATION, MAX_GPT_TEXT_LENGTH,
)

# ============================================
# НАСТРОЙКА ПУТЕЙ
# ============================================

# Vosk модель
if VOSK_MODEL_DIR.exists():
    os.environ["PATH"] = str(VOSK_MODEL_DIR) + os.pathsep + os.environ.get("PATH", "")
    if str(VOSK_MODEL_DIR) not in sys.path:
        sys.path.insert(0, str(VOSK_MODEL_DIR))
    print(f"✅ Модель Vosk: {VOSK_MODEL_DIR}")
else:
    print(f"⚠️ Модель Vosk не найдена: {VOSK_MODEL_DIR}")

# FFmpeg
if FFMPEG_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")
    print(f"✅ FFmpeg: {FFMPEG_DIR}")
else:
    print(f"⚠️ FFmpeg не найден: {FFMPEG_DIR}")

# ============================================
# ИМПОРТЫ
# ============================================

import subprocess
import traceback
from datetime import datetime

from services import download_audio, transcribe_audio_with_timestamps
from services.yandex_gpt import YandexGPT, correct_text_with_yandex, correct_long_text
from services.text_correction import format_transcription_with_timestamps, simple_correction
from utils.audio_utils import convert_to_wav
from utils.file_utils import sanitize_filename
from utils.validation import validate_url, detect_platform
from utils.punctuation_utils import process_transcription

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import subprocess
import traceback
from datetime import datetime

parent_dir = BASE_DIR.parent
sys.path.append(str(parent_dir))

from config import FFMPEG_DIR as CONFIG_FFMPEG_DIR, VOSK_MODEL_DIR, OUTPUT_DIRS
from services import download_audio, transcribe_audio_with_timestamps
from services.yandex_gpt import YandexGPT, correct_text_with_yandex, correct_long_text
from services.text_correction import format_transcription_with_timestamps, simple_correction
from utils.audio_utils import convert_to_wav
from utils.file_utils import sanitize_filename
from utils.validation import validate_url, detect_platform
from utils.punctuation_utils import process_transcription

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
# комментарий для выполнения 3 лабы

# ============================================
# ГРАДИЕНТНЫЙ ТЕКСТ
# ============================================

class GradientLabel(QLabel):
    def __init__(self, text, color1="#FF5500", color2="#FF6B6B", parent=None):
        super().__init__(text, parent)
        self.color1 = QColor(color1)
        self.color2 = QColor(color2)
        self.setTextFormat(Qt.RichText)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
        painter.setFont(self.font())
        painter.drawText(self.rect().adjusted(2, 2, 0, 0), self.alignment() | Qt.TextWordWrap, self.text())

        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, self.color1)
        gradient.setColorAt(1, self.color2)

        painter.setPen(QPen(gradient, 1))
        painter.setFont(self.font())
        painter.drawText(self.rect(), self.alignment() | Qt.TextWordWrap, self.text())


# ============================================
# ГРАДИЕНТНАЯ РАМКА С ЧЁРНЫМ ФОНОМ
# ============================================

class GradientBorderWidget(QWidget):
    def __init__(self, parent=None, color1="#FF5500", color2="#FF6B6B", border_width=2, radius=14):
        super().__init__(parent)
        self.color1 = QColor(color1)
        self.color2 = QColor(color2)
        self.border_width = border_width
        self.radius = radius
        self.setAttribute(Qt.WA_StyledBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, self.color1)
        gradient.setColorAt(1, self.color2)

        # ЧЁРНЫЙ фон
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self.radius, self.radius)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(gradient, self.border_width))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), self.radius, self.radius)


# ============================================
# ЗАГРУЗКА ИНФОРМАЦИИ О ВИДЕО
# ============================================

def get_video_info_async(url, callback):
    def fetch():
        try:
            import yt_dlp
            opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignore_errors': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    platform = detect_platform(url)
                    platform_names = {
                        'youtube': 'YouTube',
                        'rutube': 'Rutube',
                        'vk': 'VK Video'
                    }
                    callback({
                        'title': info.get('title', 'Видео')[:60],
                        'channel': info.get('uploader', 'Автор')[:30],
                        'platform': platform_names.get(platform, 'Видео'),
                        'thumbnail': info.get('thumbnail', ''),
                        'success': True
                    })
                else:
                    callback({'success': False})
        except Exception as e:
            print(f"Ошибка: {e}")
            callback({'success': False})

    thread = threading.Thread(target=fetch, daemon=True)
    thread.start()


# ============================================
# WORKER THREAD
# ============================================

class WorkerThread(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, url, use_gpt=True):
        super().__init__()
        self.url = url
        self.use_gpt = use_gpt

    def run(self):
        try:
            self.progress.emit(5, "Начинаем обработку видео...")
            self.progress.emit(10, "Скачивание аудио...")

            result = download_audio(self.url)
            if not result or not result[0]:
                self.error.emit("Не удалось скачать аудио")
                return

            audio_file, title = result
            self.progress.emit(25, f"Аудио скачано: {audio_file.name}")
            self.progress.emit(30, "Конвертация в WAV...")

            wav_file = OUTPUT_DIRS["audio"] / f"converted_{audio_file.stem}.wav"
            success, error = convert_to_wav(str(audio_file), str(wav_file))
            if not success:
                self.error.emit(f"Ошибка конвертации: {error}")
                return

            self.progress.emit(40, "Аудио сконвертировано")
            self.progress.emit(50, "Транскрибация...")

            transcription, segments = transcribe_audio_with_timestamps(wav_file, VOSK_MODEL_DIR)
            if not transcription or not segments:
                self.error.emit("Не удалось распознать текст")
                return

            self.progress.emit(70, f"Распознано {len(segments)} сегментов")
            self.progress.emit(80, "Исправление текста...")

            if self.use_gpt:
                try:
                    yandex_client = YandexGPT()
                    corrected_text = yandex_client.correct_text(transcription) if len(transcription) <= 3000 else correct_long_text(transcription)
                except:
                    corrected_text = None
            else:
                corrected_text = None

            if corrected_text is None:
                corrected_text = simple_correction(transcription)
                self.progress.emit(85, "Базовая коррекция")
            else:
                self.progress.emit(85, "Коррекция YandexGPT")

            self.progress.emit(90, "Расстановка знаков...")
            corrected_text = process_transcription(corrected_text)

            safe_title = sanitize_filename(title)[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_title}_{timestamp}.txt"
            output_file = OUTPUT_DIRS["transcriptions"] / filename

            formatted_output = format_transcription_with_timestamps(segments, corrected_text)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_output)

            try:
                if audio_file.exists(): audio_file.unlink()
                if wav_file.exists(): wav_file.unlink()
            except: pass

            self.progress.emit(100, "Готово!")
            self.finished.emit({
                'text': corrected_text,
                'segments': segments,
                'segments_count': len(segments),
                'char_count': len(corrected_text),
                'filename': filename,
                'title': title
            })
        except Exception as e:
            self.error.emit(str(e))


# ============================================
# ГЛАВНОЕ ОКНО
# ============================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TranscribeFlow")
        self.setMinimumSize(950, 750)
        self.setStyleSheet("""
            QMainWindow { background: #0A0A0A; }
            QLabel { color: #F0E6D3; }
        """)
        self.setWindowFlags(Qt.FramelessWindowHint)

        central = QWidget()
        central.setStyleSheet("background: #0A0A0A;")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя полоса
        title_bar = QWidget()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet("background: #0A0A0A; border-bottom: 1px solid rgba(255,255,255,0.05);")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(24, 0, 16, 0)

        title_label = QLabel("🎙️ TranscribeFlow")
        title_label.setStyleSheet("color: #F0E6D3; font-weight: 600; font-size: 16px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        for btn_text, func in [("─", self.showMinimized), ("☐", self.toggle_maximized), ("✕", self.close)]:
            btn = QPushButton(btn_text)
            btn.setFixedSize(50, 34)
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; color: #F0E6D3; font-size: 17px; border-radius: 6px; }
                QPushButton:hover { background: rgba(255,255,255,0.08); }
            """)
            if btn_text == "✕":
                btn.setStyleSheet(btn.styleSheet() + "QPushButton:hover { background: #FF5500; color: #0A0A0A; }")
            btn.clicked.connect(func)
            title_layout.addWidget(btn)

        main_layout.addWidget(title_bar)

        # Скролл
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: rgba(255,255,255,0.03); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,85,0,0.3); border-radius: 4px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,85,0,0.5); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        container = QWidget()
        container.setStyleSheet("background: #0A0A0A;")
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignTop)
        container_layout.setContentsMargins(60, 20, 60, 30)
        container_layout.setSpacing(20)

        # Заголовок
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setAlignment(Qt.AlignCenter)
        top_row.setSpacing(12)
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet("background: #FF5500; border-radius: 6px;")
        top_row.addWidget(dot)
        label = QLabel("ТРАНСКРИБАТОР")
        label.setStyleSheet("font-size: 13px; font-weight: 700; letter-spacing: 0.2em; color: #FF5500;")
        top_row.addWidget(label)
        header_layout.addLayout(top_row)

        title = GradientLabel('Видео в текст за секунды', "#FF5500", "#FF6B6B")
        title.setStyleSheet("font-size: 34px; font-weight: 800;")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("Вставьте ссылку — получите точную расшифровку с таймингами")
        subtitle.setStyleSheet("font-size: 15px; color: #6A6A6A; font-weight: 400;")
        subtitle.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle)

        container_layout.addWidget(header)

        # Карточка
        self.card = GradientBorderWidget(color1="#FF5500", color2="#FF6B6B", border_width=2, radius=24)
        self.card.setStyleSheet("""
            background: transparent;
            border: none;
            border-radius: 24px;
            padding: 30px;
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(18)

        # Ввод
        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        input_wrapper = GradientBorderWidget(color1="#FF5500", color2="#FF6B6B", border_width=2, radius=14)
        input_wrapper.setStyleSheet("""
            background: transparent;
            border: none;
            border-radius: 14px;
        """)
        input_wrapper_layout = QHBoxLayout(input_wrapper)
        input_wrapper_layout.setContentsMargins(16, 0, 16, 0)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на видео...")
        self.url_input.setStyleSheet("background: transparent; border: none; color: #F0E6D3; font-size: 16px; padding: 16px 0;")
        self.url_input.textChanged.connect(self.on_url_changed)
        input_wrapper_layout.addWidget(self.url_input)

        self.load_btn = QPushButton("🔍")
        self.load_btn.setFixedSize(38, 38)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,85,0,0.15);
                border: 1px solid #FF5500;
                border-radius: 10px;
                color: #FF5500;
                font-size: 16px;
            }
            QPushButton:hover { background: rgba(255,85,0,0.25); }
        """)
        self.load_btn.clicked.connect(self.force_load_preview)
        input_wrapper_layout.addWidget(self.load_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(24, 24)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: none;
                border-radius: 12px;
                color: #4A4A4A;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(255,85,0,0.2); color: #FF5500; }
        """)
        self.clear_btn.clicked.connect(lambda: self.url_input.clear())
        self.clear_btn.hide()
        input_wrapper_layout.addWidget(self.clear_btn)

        input_row.addWidget(input_wrapper, 1)

        self.transcribe_btn = QPushButton("▶  Транскрибировать")
        self.transcribe_btn.setStyleSheet("""
            QPushButton {
                background: #FF5500;
                border: none;
                border-radius: 14px;
                padding: 0 32px;
                color: #0A0A0A;
                font-size: 15px;
                font-weight: 700;
                min-height: 54px;
            }
            QPushButton:hover { background: #E64D00; }
            QPushButton:disabled { background: #3A3A3A; color: #6A6A6A; }
        """)
        self.transcribe_btn.clicked.connect(self.start_transcription)
        input_row.addWidget(self.transcribe_btn)

        card_layout.addLayout(input_row)

        # Превью
        self.preview_widget = QWidget()
        self.preview_widget.setVisible(False)
        preview_layout = QHBoxLayout(self.preview_widget)
        preview_layout.setSpacing(20)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(600, 338)
        self.thumbnail.setStyleSheet("border-radius: 12px; background: #1A1A1A; font-size: 48px; color: #FF5500;")
        self.thumbnail.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.thumbnail)

        preview_info = QWidget()
        preview_info_layout = QVBoxLayout(preview_info)
        preview_info_layout.setSpacing(4)

        self.preview_title = QLabel("")
        self.preview_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #F0E6D3;")
        preview_info_layout.addWidget(self.preview_title)

        self.preview_channel = QLabel("")
        self.preview_channel.setStyleSheet("font-size: 14px; color: #6A6A6A;")
        preview_info_layout.addWidget(self.preview_channel)

        self.preview_platform = QLabel("")
        self.preview_platform.setStyleSheet("font-size: 12px; font-weight: 700; padding: 3px 14px; border-radius: 6px; background: rgba(255,0,0,0.12); color: #FF4444;")
        preview_info_layout.addWidget(self.preview_platform)

        preview_layout.addWidget(preview_info, 1)
        card_layout.addWidget(self.preview_widget)

        # Разделитель
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: #1E1E1E; max-height: 1px;")
        card_layout.addWidget(divider)

        # Футер
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self.use_gpt_check = QCheckBox()
        self.use_gpt_check.setChecked(True)
        self.use_gpt_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid #FF5500;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background: #FF5500;
                border-color: #FF5500;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: #0A0A0A;
                font-size: 15px;
                font-weight: 700;
            }
        """)
        footer_layout.addWidget(self.use_gpt_check)

        checkbox_text = QLabel("Использовать YandexGPT для коррекции")
        checkbox_text.setStyleSheet("font-size: 14px; font-weight: 500; color: #C8B89A;")
        footer_layout.addWidget(checkbox_text)
        footer_layout.addStretch()

        # Бейджи
        badges_widget = QWidget()
        badges_layout = QHBoxLayout(badges_widget)
        badges_layout.setSpacing(10)
        badges_layout.setContentsMargins(0, 0, 0, 0)

        hint = QLabel("Поддерживаем:")
        hint.setStyleSheet("font-size: 13px; color: #3A3A3A; font-weight: 500;")
        badges_layout.addWidget(hint)

        for name, color in [("YouTube", "#FF2020"), ("Rutube", "#00C8E0"), ("VK Video", "#4A90FF")]:
            badge = QLabel(name)
            badge.setStyleSheet(f"""
                padding: 4px 14px;
                border-radius: 8px;
                background: rgba({self._hex_to_rgb(color)}, 0.10);
                color: {color};
                font-size: 12px;
                font-weight: 700;
                border: 1px solid rgba({self._hex_to_rgb(color)}, 0.15);
            """)
            badges_layout.addWidget(badge)

        footer_layout.addWidget(badges_widget)
        card_layout.addWidget(footer)

        container_layout.addWidget(self.card)

        # Прогресс
        self.progress_widget = QWidget()
        self.progress_widget.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.06);
                border: none;
                border-radius: 10px;
                height: 6px;
            }
            QProgressBar::chunk {
                background: #FF5500;
                border-radius: 10px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Подготовка...")
        self.progress_label.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 14px;")
        progress_layout.addWidget(self.progress_label)

        container_layout.addWidget(self.progress_widget)

        # Результат
        self.result_widget = QWidget()
        self.result_widget.setVisible(False)
        result_layout = QVBoxLayout(self.result_widget)
        result_layout.setSpacing(12)

        result_header = QHBoxLayout()
        result_title = QLabel("📄 Результат транскрибации")
        result_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #F0E6D3;")
        result_header.addWidget(result_title)
        result_header.addStretch()

        for name, func in [("📋 Копировать", self.copy_result), ("💾 Сохранить", self.save_result), ("🔄 Новое", self.reset_all)]:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,85,0,0.2);
                    border-radius: 10px;
                    padding: 8px 20px;
                    color: #C8B89A;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(255,85,0,0.1);
                    border-color: #FF5500;
                }
            """)
            btn.clicked.connect(func)
            result_header.addWidget(btn)

        result_layout.addLayout(result_header)

        self.meta_label = QLabel("0 сегментов  •  0 символов")
        self.meta_label.setStyleSheet("color: #4A4A4A; font-size: 15px; margin-bottom: 4px;")
        result_layout.addWidget(self.meta_label)

        panels = QHBoxLayout()
        panels.setSpacing(16)

        for panel_data in [("⏱️ Текст с таймингами", "resultText"), ("✨ Исправленный текст", "correctedText")]:
            panel = QWidget()
            panel.setStyleSheet("""
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,85,0,0.1);
                border-radius: 14px;
                padding: 16px;
            """)
            panel_layout = QVBoxLayout(panel)
            panel_layout.setSpacing(6)

            label = QLabel(panel_data[0])
            label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 15px; font-weight: 600;")
            panel_layout.addWidget(label)

            text = QTextEdit()
            text.setReadOnly(True)
            text.setObjectName(panel_data[1])
            text.setStyleSheet(f"""
                background: transparent;
                border: none;
                color: {'#F0E6D3' if panel_data[1] == 'correctedText' else 'rgba(255,255,255,0.8)'};
                font-size: {17 if panel_data[1] == 'correctedText' else 16}px;
                line-height: 1.8;
                font-family: 'Segoe UI', sans-serif;
            """)
            setattr(self, panel_data[1], text)
            panel_layout.addWidget(text)
            panels.addWidget(panel, 1)

        result_layout.addLayout(panels)
        container_layout.addWidget(self.result_widget)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.worker = None
        self.result_data = None
        self._result_shown = False

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))

    def on_url_changed(self, text):
        self.clear_btn.setVisible(bool(text))
        if text and len(text) > 5:
            self.fetch_video_preview(text)
        else:
            self.preview_widget.setVisible(False)

    def force_load_preview(self):
        url = self.url_input.text().strip()
        if url and len(url) > 5:
            self.fetch_video_preview(url)

    def fetch_video_preview(self, url):
        if not validate_url(url):
            self.preview_widget.setVisible(False)
            return

        self.preview_widget.setVisible(True)
        self.preview_title.setText("⏳ Загрузка...")
        self.preview_channel.setText("")
        self.preview_platform.setText("")
        self.thumbnail.setText("⏳")
        self.thumbnail.setStyleSheet("border-radius: 12px; background: #1A1A1A; font-size: 48px; color: #FF5500;")

        def update_preview(info):
            if info.get('success', False):
                self.preview_title.setText(info['title'])
                self.preview_channel.setText(info['channel'])
                self.preview_platform.setText(info['platform'])
                self.preview_platform.setStyleSheet(f"""
                    font-size: 12px; font-weight: 700; padding: 3px 14px;
                    border-radius: 6px; background: rgba({self._hex_to_rgb('#FF5500')}, 0.12);
                    color: #FF5500;
                """)

                thumbnail_url = info.get('thumbnail', '')
                if thumbnail_url:
                    try:
                        response = requests.get(thumbnail_url, timeout=10)
                        if response.status_code == 200:
                            pixmap = QPixmap()
                            pixmap.loadFromData(response.content)
                            if not pixmap.isNull():
                                self.thumbnail.setPixmap(pixmap.scaled(600, 338, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                                self.thumbnail.setStyleSheet("border-radius: 12px;")
                                return
                    except:
                        pass

                self.thumbnail.setText("🎬")
                self.thumbnail.setStyleSheet("border-radius: 12px; background: #1A1A1A; font-size: 48px; color: #4A4A4A;")
            else:
                platform = detect_platform(url)
                platform_names = {'youtube': 'YouTube', 'rutube': 'Rutube', 'vk': 'VK Video'}
                platform_icons = {'youtube': '▶️', 'rutube': '📺', 'vk': '🎬'}
                name = platform_names.get(platform, 'Видео')
                icon = platform_icons.get(platform, '🎬')
                self.preview_title.setText(f"{icon} Видео готово")
                self.preview_channel.setText(f"Платформа: {name}")
                self.preview_platform.setText(name)
                self.preview_platform.setStyleSheet(f"""
                    font-size: 12px; font-weight: 700; padding: 3px 14px;
                    border-radius: 6px; background: rgba({self._hex_to_rgb('#FF5500')}, 0.12);
                    color: #FF5500;
                """)
                self.thumbnail.setText(icon)
                self.thumbnail.setStyleSheet("border-radius: 12px; background: #1A1A1A; font-size: 48px; color: #FF5500;")

        get_video_info_async(url, update_preview)

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(2000)
        event.accept()

    def start_transcription(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите ссылку на видео")
            return
        if not validate_url(url):
            QMessageBox.warning(self, "Ошибка", "Некорректный URL")
            return

        self.transcribe_btn.setEnabled(False)
        self.transcribe_btn.setText("⏳ Обработка...")
        self.progress_widget.setVisible(True)
        self.result_widget.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Подготовка...")

        self.worker = WorkerThread(url, self.use_gpt_check.isChecked())
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.show_result)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def show_result(self, data):
        self._result_shown = True
        self.result_data = data
        self.meta_label.setText(f"{data['segments_count']} сегментов  •  {data['char_count']} символов")

        timestamps_text = ""
        for seg in data['segments']:
            start_min = int(seg['start'] // 60)
            start_sec = int(seg['start'] % 60)
            end_min = int(seg['end'] // 60)
            end_sec = int(seg['end'] % 60)
            time_str = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"
            timestamps_text += f"{time_str} {seg['text']}\n"

        self.resultText.setText(timestamps_text)
        self.correctedText.setText(data['text'])
        self.result_widget.setVisible(True)
        self.progress_label.setText("✅ Готово!")
        self.transcribe_btn.setEnabled(True)
        self.transcribe_btn.setText("▶ Транскрибировать")

        QTimer.singleShot(100, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        scroll = self.findChild(QScrollArea)
        if scroll:
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())

    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)
        self.transcribe_btn.setEnabled(True)
        self.transcribe_btn.setText("▶ Транскрибировать")
        self.progress_widget.setVisible(False)

    def copy_result(self):
        if self.result_data:
            QApplication.clipboard().setText(self.result_data['text'])
            QMessageBox.information(self, "Готово", "Текст скопирован")

    def save_result(self):
        if self.result_data:
            file_path = OUTPUT_DIRS["transcriptions"] / self.result_data['filename']
            if file_path.exists():
                QMessageBox.information(self, "Готово", f"Файл сохранён:\n{file_path}")

    def reset_all(self):
        self.url_input.clear()
        self.result_widget.setVisible(False)
        self.progress_widget.setVisible(False)
        self.preview_widget.setVisible(False)
        self.result_data = None
        self.url_input.setFocus()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(10, 10, 26))
    dark_palette.setColor(QPalette.WindowText, QColor(240, 230, 211))
    dark_palette.setColor(QPalette.Base, QColor(20, 20, 40))
    dark_palette.setColor(QPalette.Text, QColor(240, 230, 211))
    dark_palette.setColor(QPalette.Button, QColor(30, 30, 50))
    dark_palette.setColor(QPalette.ButtonText, QColor(240, 230, 211))
    dark_palette.setColor(QPalette.Highlight, QColor(255, 85, 0))
    dark_palette.setColor(QPalette.HighlightedText, QColor(10, 10, 26))
    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()