"""
UI компоненты для TranscribeFlow Desktop
Отдельные виджеты с готовыми стилями
"""
import os
import sys  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def load_stylesheet():
    """Загружает стили из style.qss"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        style_path = base_path / 'assets' / 'style.qss'
    else:
        style_path = Path(__file__).parent / 'style.qss'
    
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


class InputGlassCard(QWidget):
    """Glass-карточка для ввода ссылки"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input-glass-card")
        self.init_ui()
        # Применяем стили
        self.setStyleSheet(load_stylesheet())
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)
        
        # Input Row
        input_row = QWidget()
        input_row.setObjectName("input-row")
        input_row_layout = QHBoxLayout(input_row)
        input_row_layout.setSpacing(12)
        input_row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Field Wrapper
        self.field_wrapper = QWidget()
        self.field_wrapper.setObjectName("field-wrapper")
        field_layout = QVBoxLayout(self.field_wrapper)
        field_layout.setContentsMargins(0, 0, 0, 0)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("url-input")
        self.url_input.setPlaceholderText("Вставьте ссылку на видео...")
        field_layout.addWidget(self.url_input)
        input_row_layout.addWidget(self.field_wrapper)
        
        # Action Button
        self.transcribe_btn = QPushButton("Транскрибировать")
        self.transcribe_btn.setObjectName("action-button")
        input_row_layout.addWidget(self.transcribe_btn)
        
        layout.addWidget(input_row)
        
        # Footer
        footer = QWidget()
        footer.setObjectName("input-footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Checkbox
        checkbox_widget = QWidget()
        checkbox_widget.setObjectName("checkbox-group")
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setSpacing(10)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        
        self.use_gpt_check = QCheckBox()
        self.use_gpt_check.setChecked(True)
        checkbox_layout.addWidget(self.use_gpt_check)
        
        checkbox_label = QLabel("Использовать YandexGPT для коррекции")
        checkbox_label.setObjectName("checkbox-label")
        checkbox_layout.addWidget(checkbox_label)
        
        footer_layout.addWidget(checkbox_widget)
        footer_layout.addStretch()
        
        # Platform Indicators
        platform_hint = QLabel("Поддерживаем:")
        platform_hint.setObjectName("platform-hint")
        footer_layout.addWidget(platform_hint)
        
        for name in ["YouTube", "Rutube", "VK"]:
            badge = QLabel(name)
            badge.setObjectName(f"badge-{name.lower()}")
            footer_layout.addWidget(badge)
        
        layout.addWidget(footer)
    
    def get_url(self):
        return self.url_input.text().strip()
    
    def clear_url(self):
        self.url_input.clear()
    
    def set_button_enabled(self, enabled):
        self.transcribe_btn.setEnabled(enabled)
    
    def set_button_text(self, text):
        self.transcribe_btn.setText(text)
    
    def is_gpt_enabled(self):
        return self.use_gpt_check.isChecked()
    
    def url_input_focus(self):
        self.url_input.setFocus()


class StatusIndicator(QWidget):
    """Индикатор статуса"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #4CAF50; font-size: 14px;")
        layout.addWidget(self.dot)
        
        self.text = QLabel("Готов к работе")
        self.text.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 13px;")
        layout.addWidget(self.text)
    
    def set_ready(self, ready=True):
        if ready:
            self.dot.setStyleSheet("color: #4CAF50; font-size: 14px;")
            self.text.setText("Готов к работе ✅")
        else:
            self.dot.setStyleSheet("color: #FF6B6B; font-size: 14px;")
            self.text.setText("FFmpeg не найден ❌")