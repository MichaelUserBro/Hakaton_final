/**
 * Frontend logic for Collaborative Code Editor
 * Финальная версия: Yjs + Django Channels + Awareness курсоры
 */

let editor;
let ydoc;
let ytext;
let awareness;
let binding;
let socket;

const YLib = window.Y || window.Yjs;

document.addEventListener('DOMContentLoaded', () => {
    if (!YLib) {
        console.error("Yjs не найден! Проверь подключение скриптов в HTML.");
        return;
    }

    console.log("Инициализация Yjs...");

    // --- YJS SETUP ---
    try {
        const DocConstructor = (typeof YLib === 'function') ? YLib : (YLib.Doc || YLib.Y?.Doc);

        if (!DocConstructor) {
            throw new Error("Не удалось найти конструктор Doc в библиотеке Yjs");
        }

        ydoc = new DocConstructor();
        ytext = ydoc.getText('ace');

        const AwarenessConstructor = window.YAwareness?.Awareness || YLib.Awareness || YLib.Y?.Awareness;
        if (AwarenessConstructor) {
            awareness = new AwarenessConstructor(ydoc);
        }

        console.log("Yjs Core инициализирован успешно");
    } catch (e) {
        console.error("Критическая ошибка ядра Yjs:", e);
        return;
    }

    // --- ACE EDITOR INIT ---
    editor = ace.edit("editor");
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/python");
    editor.setShowPrintMargin(false);
    editor.setOptions({ fontSize: "14px" });

    // --- WEBSOCKET SETUP ---
    const socketUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://')
                      + window.location.host
                      + '/ws/editor/';

    socket = new WebSocket(socketUrl);
    socket.binaryType = 'arraybuffer';

    const statusDot = document.getElementById('sync-status');

    socket.onopen = () => {
        if (statusDot) statusDot.classList.add('online');
        addEvent('System', 'Синхронизация активна');

        // Сразу отправляем своё awareness состояние остальным
        if (awareness) {
            _sendAwareness();
        }
    };

    socket.onclose = () => {
        if (statusDot) statusDot.classList.remove('online');
        addEvent('System', 'Соединение потеряно');
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const payload = data.message;

            if (!payload) return;

            // Обновление документа (CRDT)
            if (payload.type === 'update' && payload.update) {
                const update = new Uint8Array(payload.update);
                const apply = YLib.applyUpdate || YLib.Y?.applyUpdate;
                if (apply) {
                    apply(ydoc, update, socket);
                } else {
                    ydoc.applyUpdate(update, socket);
                }
            }

            // Обновление курсора другого пользователя
            if (payload.type === 'awareness' && awareness) {
            const { clientId, state } = payload;
                if (clientId !== awareness.clientID) {
                    const isNew = !awareness.getStates().has(clientId);
                    awareness.getStates().set(clientId, state);
                    awareness.emit('change', [{
                        added: isNew ? [clientId] : [],
                        updated: isNew ? [] : [clientId],
                        removed: []
                    }]);
                }
            }

            // Удаление курсора при отключении пользователя
            if (payload.type === 'awareness_remove' && awareness) {
                const { clientId } = payload;
                awareness.getStates().delete(clientId);
                awareness.emit('change', [{ added: [], updated: [], removed: [clientId] }]);
            }

        } catch (e) {
            console.error("Ошибка входящего обновления:", e);
        }
    };

    // Отправка локальных изменений документа
    ydoc.on('update', (update, origin) => {
        if (origin !== socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                'message': {
                    'type': 'update',
                    'update': Array.from(update)
                }
            }));
        }
    });

    // Отправка awareness через WebSocket
    function _sendAwareness() {
        if (!awareness || socket.readyState !== WebSocket.OPEN) return;
        const localState = awareness.getLocalState();
        if (!localState) return;
        socket.send(JSON.stringify({
            'message': {
                'type': 'awareness',
                'clientId': awareness.clientID,
                'state': localState
            }
        }));
    }

    // Слушаем изменения своего awareness и отправляем другим
    if (awareness) {
        awareness.on('change', ({ added, updated }) => {
            if (added.includes(awareness.clientID) || updated.includes(awareness.clientID)) {
                _sendAwareness();
            }
        });
    }

    // --- BINDING ---
    const AceBinding = window.AceBinding;

    if (AceBinding) {
        try {
            binding = new AceBinding(ytext, editor, awareness);
            console.log("AceBinding подключен");
        } catch (e) {
            console.error("Ошибка биндинга:", e);
        }
    } else {
        console.error("AceBinding не найден в window. Проверь y-ace.js");
    }

    // Начальный контент
    if (typeof INITIAL_CONTENT !== 'undefined' && INITIAL_CONTENT.length > 0) {
        setTimeout(() => {
            if (ytext.toString().length === 0) {
                ydoc.transact(() => {
                    ytext.insert(0, INITIAL_CONTENT);
                });
            }
        }, 500);
    }

    if (typeof initResizer === 'function') initResizer();
});

function addEvent(user, action) {
    const container = document.getElementById('timeline-content');
    if (!container) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const card = document.createElement('div');
    card.className = 'event-card';
    card.innerHTML = `<div style="font-size: 10px; color: #666;">${timeStr}</div><div><b>${user}:</b> ${action}</div>`;
    container.prepend(card);
}