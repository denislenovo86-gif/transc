/**
 * TranscribeFlow — Main JavaScript
 * Управление интерфейсом, предпросмотром видео и транскрибацией
 */

// ============================================
// State
// ============================================

const state = {
    taskId: null,
    pollingInterval: null,
    resultData: null,
    videoInfo: null,
    isProcessing: false
};

// ============================================
// DOM References
// ============================================

const $ = (id) => document.getElementById(id);

const elements = {
    urlInput: $('videoUrl'),
    loadBtn: $('loadBtn'),
    transcribeBtn: $('transcribeBtn'),
    useGpt: $('useGpt'),

    videoPreview: $('videoPreview'),
    videoThumbnail: $('videoThumbnail'),
    videoTitle: $('videoTitle'),
    videoChannel: $('videoChannel'),
    videoPlatform: $('videoPlatform'),
    videoDuration: $('videoDuration'),
    videoLength: $('videoLength'),

    statusSection: $('statusSection'),
    progressBar: $('progressBar'),
    progressText: $('progressText'),
    statusMessage: $('statusMessage'),
    statusSpinner: $('statusSpinner'),

    resultSection: $('resultSection'),
    resultSegments: $('resultSegments'),
    resultChars: $('resultChars'),
    timestampsText: $('timestampsText'),
    correctedText: $('correctedText'),
    segmentsBadge: $('segmentsBadge'),

    errorMessage: $('errorMessage'),
    errorText: document.querySelector('.error-text'),

    headerStatus: $('headerStatus'),
    statusDot: document.querySelector('.status-dot'),
    statusText: document.querySelector('.status-text'),

    copyBtn: $('copyBtn'),
    downloadBtn: $('downloadBtn'),
    newBtn: $('newBtn')
};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    checkEnvironment();
    setupEventListeners();
});

// ============================================
// Event Listeners
// ============================================

function setupEventListeners() {
    elements.transcribeBtn.addEventListener('click', startTranscription);
    elements.loadBtn.addEventListener('click', loadVideoInfo);
    elements.urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (e.shiftKey) {
                loadVideoInfo();
            } else {
                startTranscription();
            }
        }
    });
    elements.copyBtn.addEventListener('click', copyResult);
    elements.downloadBtn.addEventListener('click', downloadResult);
    elements.newBtn.addEventListener('click', resetAll);
}

// ============================================
// Environment Check
// ============================================

async function checkEnvironment() {
    try {
        const response = await fetch('/api/check');
        const data = await response.json();

        const dot = elements.statusDot;
        const text = elements.statusText;

        if (data.ready) {
            dot.className = 'status-dot';
            text.textContent = 'Готов к работе ✅';
        } else if (!data.ffmpeg) {
            dot.className = 'status-dot error';
            text.textContent = 'FFmpeg не найден';
        } else if (!data.vosk) {
            dot.className = 'status-dot error';
            text.textContent = 'Модель Vosk не найдена';
        } else {
            dot.className = 'status-dot warning';
            text.textContent = 'Частичная готовность';
        }
    } catch (error) {
        elements.statusText.textContent = 'Ошибка подключения';
    }
}

// ============================================
// Video Info Loading
// ============================================

async function loadVideoInfo() {
    const url = elements.urlInput.value.trim();
    if (!url) {
        showError('Введите ссылку на видео');
        return;
    }

    try {
        elements.loadBtn.disabled = true;
        elements.loadBtn.textContent = '⏳';

        const response = await fetch('/api/video-info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        state.videoInfo = data;
        showVideoPreview(data);
        hideError();

    } catch (error) {
        showError('Ошибка загрузки информации о видео');
    } finally {
        elements.loadBtn.disabled = false;
        elements.loadBtn.textContent = '🔍';
    }
}

function showVideoPreview(info) {
    elements.videoThumbnail.src = info.thumbnail || 'https://via.placeholder.com/320x180/1a1a2e/6C63FF?text=No+Preview';
    elements.videoTitle.textContent = info.title || 'Без названия';
    elements.videoChannel.textContent = info.channel || 'Неизвестный канал';

    const platform = info.platform || 'youtube';
    elements.videoPlatform.textContent = platform.toUpperCase();
    elements.videoPlatform.className = `video-platform-tag ${platform}`;

    const duration = info.duration || 0;
    const mins = Math.floor(duration / 60);
    const secs = Math.floor(duration % 60);
    elements.videoDuration.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    elements.videoLength.textContent = `⏱️ ${mins}:${String(secs).padStart(2, '0')}`;

    elements.videoPreview.style.display = 'block';
}

// ============================================
// Transcription
// ============================================

async function startTranscription() {
    const url = elements.urlInput.value.trim();
    if (!url) {
        showError('Введите ссылку на видео');
        return;
    }

    if (state.isProcessing) return;
    state.isProcessing = true;

    // UI State
    hideError();
    elements.transcribeBtn.disabled = true;
    elements.transcribeBtn.innerHTML = '<span class="btn-icon">⏳</span> Обработка...';
    elements.resultSection.style.display = 'none';
    elements.statusSection.style.display = 'block';
    elements.progressBar.style.width = '0%';
    elements.progressText.textContent = '0%';
    elements.statusMessage.textContent = 'Подготовка...';
    elements.statusSpinner.textContent = '⏳';

    try {
        const useGpt = elements.useGpt.checked;
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, use_gpt: useGpt })
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            state.isProcessing = false;
            elements.transcribeBtn.disabled = false;
            elements.transcribeBtn.innerHTML = '<span class="btn-icon">▶</span> Транскрибировать';
            return;
        }

        state.taskId = data.task_id;
        startPolling();

    } catch (error) {
        showError('Ошибка запуска транскрибации');
        state.isProcessing = false;
        elements.transcribeBtn.disabled = false;
        elements.transcribeBtn.innerHTML = '<span class="btn-icon">▶</span> Транскрибировать';
    }
}

// ============================================
// Polling
// ============================================

function startPolling() {
    if (state.pollingInterval) clearInterval(state.pollingInterval);

    state.pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${state.taskId}`);
            const data = await response.json();
            updateStatus(data);

            if (data.status === 'completed') {
                clearInterval(state.pollingInterval);
                state.pollingInterval = null;
                showResult(data);
                state.isProcessing = false;
                elements.transcribeBtn.disabled = false;
                elements.transcribeBtn.innerHTML = '<span class="btn-icon">▶</span> Транскрибировать';
            } else if (data.status === 'error') {
                clearInterval(state.pollingInterval);
                state.pollingInterval = null;
                showError(data.error_message || data.message);
                state.isProcessing = false;
                elements.transcribeBtn.disabled = false;
                elements.transcribeBtn.innerHTML = '<span class="btn-icon">▶</span> Транскрибировать';
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);
}

function updateStatus(data) {
    const progress = data.progress || 0;
    elements.progressBar.style.width = `${progress}%`;
    elements.progressText.textContent = `${progress}%`;
    elements.statusMessage.textContent = data.message || 'Обработка...';

    if (data.status === 'pending' || data.status === 'processing') {
        elements.statusSpinner.textContent = '⏳';
    } else {
        elements.statusSpinner.textContent = '✅';
    }
}

// ============================================
// Show Result
// ============================================

function showResult(data) {
    const result = data.result || {};
    state.resultData = result;

    elements.resultSection.style.display = 'block';
    elements.statusMessage.textContent = '✅ Готово!';
    elements.statusSpinner.textContent = '✅';

    // Stats
    elements.resultSegments.textContent = `${result.segments_count || 0} сегментов`;
    elements.resultChars.textContent = `${result.char_count || 0} символов`;
    elements.segmentsBadge.textContent = result.segments_count || 0;

    // Timestamps
    if (result.segments && result.segments.length > 0) {
        let html = '';
        result.segments.forEach(seg => {
            const startMin = Math.floor(seg.start / 60);
            const startSec = Math.floor(seg.start % 60);
            const endMin = Math.floor(seg.end / 60);
            const endSec = Math.floor(seg.end % 60);
            const timeStr = `[${String(startMin).padStart(2, '0')}:${String(startSec).padStart(2, '0')} - ${String(endMin).padStart(2, '0')}:${String(endSec).padStart(2, '0')}]`;
            html += `<div class="timestamp-line"><span class="timestamp">${timeStr}</span> ${seg.text}</div>`;
        });
        elements.timestampsText.innerHTML = html;
    } else {
        elements.timestampsText.textContent = 'Нет данных с таймингами';
    }

    // Corrected text
    elements.correctedText.textContent = result.text || 'Нет текста';

    // Scroll to result
    elements.resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================
// Copy & Download
// ============================================

function copyResult() {
    if (!state.resultData || !state.resultData.text) {
        showError('Нет текста для копирования');
        return;
    }

    navigator.clipboard.writeText(state.resultData.text)
        .then(() => {
            elements.copyBtn.textContent = '✅ Скопировано!';
            setTimeout(() => {
                elements.copyBtn.textContent = '📋 Копировать';
            }, 2000);
        })
        .catch(() => {
            // Fallback
            const text = state.resultData.text;
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            elements.copyBtn.textContent = '✅ Скопировано!';
            setTimeout(() => {
                elements.copyBtn.textContent = '📋 Копировать';
            }, 2000);
        });
}

function downloadResult() {
    if (!state.resultData || !state.resultData.filename) {
        showError('Нет файла для скачивания');
        return;
    }

    window.location.href = `/api/download/${state.resultData.filename}`;
}

// ============================================
// Reset
// ============================================

function resetAll() {
    elements.urlInput.value = '';
    elements.videoPreview.style.display = 'none';
    elements.statusSection.style.display = 'none';
    elements.resultSection.style.display = 'none';
    elements.errorMessage.style.display = 'none';
    elements.progressBar.style.width = '0%';
    elements.progressText.textContent = '0%';

    if (state.pollingInterval) {
        clearInterval(state.pollingInterval);
        state.pollingInterval = null;
    }

    state.taskId = null;
    state.resultData = null;
    state.videoInfo = null;
    state.isProcessing = false;

    elements.transcribeBtn.disabled = false;
    elements.transcribeBtn.innerHTML = '<span class="btn-icon">▶</span> Транскрибировать';

    elements.urlInput.focus();
}

// ============================================
// Error Handling
// ============================================

function showError(message) {
    elements.errorMessage.style.display = 'flex';
    elements.errorText.textContent = message;
}

function hideError() {
    elements.errorMessage.style.display = 'none';
}

// ============================================
// Keyboard Shortcuts
// ============================================

document.addEventListener('keydown', (e) => {
    // Ctrl+Enter - начать транскрибацию
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        startTranscription();
    }
    // Escape - сбросить
    if (e.key === 'Escape') {
        resetAll();
    }
});