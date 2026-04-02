/**
 * main.js — Логика кнопок Run Code и AI Refactoring
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function printOutput(text, isError = false) {
    const output = document.getElementById('output');
    if (!output) return;
    output.style.color = isError ? '#ff5555' : '#00ff00';
    output.innerText = text;
}

function setLog(text) {
    const log = document.getElementById('log');
    if (log) log.innerText = text;
}

// ▶ Запуск кода
async function runCode() {
    if (typeof editor === 'undefined' || !editor) {
        printOutput('Ошибка: редактор не инициализирован', true);
        return;
    }

    const code = editor.getValue();
    if (!code.trim()) {
        printOutput('Ошибка: редактор пуст', true);
        return;
    }

    printOutput('Выполняется...');
    setLog('Запуск кода...');

    try {
        const response = await fetch('/run/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ code })
        });

        const data = await response.json();

        if (data.stderr) {
            printOutput(data.stderr, true);
        } else if (data.stdout) {
            printOutput(data.stdout);
        } else {
            printOutput('(нет вывода)');
        }

        setLog('Готово.');
        if (typeof addEvent === 'function') addEvent('Run', 'Код выполнен');

    } catch (e) {
        printOutput('Сетевая ошибка: ' + e.message, true);
        setLog('Ошибка запуска.');
    }
}

// ✨ AI действия: hints, rename, readable
async function applyAI(action) {
    if (typeof editor === 'undefined' || !editor) {
        setLog('Редактор не готов');
        return;
    }

    const code = editor.getValue();
    if (!code.trim()) {
        setLog('Код пуст');
        return;
    }

    const errorLog = document.getElementById('output')?.innerText || '';

    // Кнопка fix — отдельная логика с диалогом
    if (action === 'fix') {
        await applyFix(code, errorLog);
        return;
    }

    setLog('AI думает...');

    try {
        const response = await fetch('/ai-action/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ code, action, error_log: errorLog })
        });

        const data = await response.json();

        if (data.error) {
            setLog('Ошибка AI: ' + data.error);
            return;
        }

        // Бэкенд всегда возвращает {"result": "..."}
        if (data.result) {
            editor.setValue(data.result, -1);
            setLog('AI: код обновлён ✓');
            if (typeof addEvent === 'function') addEvent('AI', action + ': код обновлён');
        }

    } catch (e) {
        setLog('Сетевая ошибка AI: ' + e.message);
    }
}

async function applyFix(code, errorLog) {
    setLog('AI анализирует ошибку...');

    try {
        const response = await fetch('/ai-action/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.CSRF_TOKEN || getCookie('csrftoken'),
            },
            body: JSON.stringify({ code, action: 'fix_error', error_log: errorLog })
        });

        const data = await response.json();

        if (data.error) {
            setLog('Ошибка AI: ' + data.error);
            return;
        }

        const explanation = data.explanation || 'Анализ завершён.';
        const fixedCode = typeof data.result === 'string' ? data.result : code;

        showFixModal(explanation, fixedCode, code);
        setLog('AI: анализ готов');

    } catch (e) {
        setLog('Сетевая ошибка AI: ' + e.message);
    }
}

// Модальное окно подтверждения исправления
function showFixModal(explanation, fixedCode, originalCode) {
    const old = document.getElementById('fix-modal');
    if (old) old.remove();

    const modal = document.createElement('div');
    modal.id = 'fix-modal';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.7); z-index: 9999;
        display: flex; align-items: center; justify-content: center;
    `;

    const hasFix = fixedCode && fixedCode !== originalCode;

    modal.innerHTML = `
        <div style="background: #252526; border: 1px solid #454545; border-radius: 8px;
                    padding: 24px; max-width: 560px; width: 90%; color: #e0e0e0;">
            <h3 style="margin: 0 0 12px; color: #ff5555;">🐞 Анализ ошибки</h3>
            <p style="font-size: 13px; line-height: 1.6; margin: 0 0 20px;
                      background: #1e1e1e; padding: 12px; border-radius: 4px; white-space: pre-wrap;">
                ${explanation || 'Ошибок не обнаружено.'}
            </p>
            ${hasFix ? `
            <p style="font-size: 12px; color: #858585; margin: 0 0 16px;">
                AI предлагает исправление. Применить изменения в редакторе?
            </p>
            <div style="display: flex; gap: 10px;">
                <button onclick="acceptFix()" style="flex:1; background: #28a745; color: white;
                        border: none; padding: 8px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                    ✓ Принять исправление
                </button>
                <button onclick="rejectFix()" style="flex:1; background: #3e3e42; color: #ccc;
                        border: none; padding: 8px; border-radius: 4px; cursor: pointer;">
                    ✗ Отклонить
                </button>
            </div>` : `
            <button onclick="rejectFix()" style="background: #3e3e42; color: #ccc;
                    border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer;">
                Закрыть
            </button>`}
        </div>
    `;

    if (hasFix) window._pendingFixCode = fixedCode;
    document.body.appendChild(modal);
}

function acceptFix() {
    if (window._pendingFixCode) {
        editor.setValue(window._pendingFixCode, -1);
        setLog('AI: исправление принято ✓');
        if (typeof addEvent === 'function') addEvent('AI', 'Ошибка исправлена');
        window._pendingFixCode = null;
    }
    const modal = document.getElementById('fix-modal');
    if (modal) modal.remove();
}

function rejectFix() {
    window._pendingFixCode = null;
    const modal = document.getElementById('fix-modal');
    if (modal) modal.remove();
    setLog('AI: исправление отклонено');
}

// Ресайзер терминала
function initResizer() {
    const resizer = document.getElementById('terminal-resizer');
    const container = document.getElementById('terminal-container');
    if (!resizer || !container) return;

    let startY, startHeight;

    resizer.addEventListener('mousedown', (e) => {
        startY = e.clientY;
        startHeight = container.offsetHeight;
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', () => {
            document.removeEventListener('mousemove', onMouseMove);
        }, { once: true });
    });

    function onMouseMove(e) {
        const delta = startY - e.clientY;
        const newHeight = Math.max(40, Math.min(500, startHeight + delta));
        container.style.height = newHeight + 'px';
    }
}

function toggleTerminal() {
    const container = document.getElementById('terminal-container');
    if (!container) return;
    const content = container.querySelector('.terminal-content');
    const resizer = document.getElementById('terminal-resizer');
    if (container.dataset.collapsed === 'true') {
        container.style.height = '200px';
        if (content) content.style.display = '';
        if (resizer) resizer.style.display = '';
        container.dataset.collapsed = 'false';
    } else {
        container.style.height = '40px';
        if (content) content.style.display = 'none';
        if (resizer) resizer.style.display = 'none';
        container.dataset.collapsed = 'true';
    }
}