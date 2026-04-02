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
    if (!YLib) return;

    // --- YJS SETUP ---
    try {
        const DocConstructor = (typeof YLib === 'function') ? YLib : (YLib.Doc || YLib.Y?.Doc);
        if (!DocConstructor) throw new Error("Не удалось найти конструктор Doc");

        ydoc = new DocConstructor();
        ytext = ydoc.getText('ace');

        const AwarenessConstructor = window.YAwareness?.Awareness || YLib.Awareness || YLib.Y?.Awareness;
        if (AwarenessConstructor) {
            awareness = new AwarenessConstructor(ydoc);
        }
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
    const projectId = window.PROJECT_ID || 'global';
    const socketUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://')
                  + window.location.host
                  + '/ws/editor/?project_id=' + projectId;
    socket = new WebSocket(socketUrl);
    socket.binaryType = 'arraybuffer';

    const statusDot = document.getElementById('sync-status');

    // Флаг — получили ли мы doc от других участников
    let receivedDocFromPeer = false;

    socket.onopen = () => {
        if (statusDot) statusDot.classList.add('online');
        addEvent('System', 'Синхронизация активна');

        if (awareness) {
            const username = window.CURRENT_USERNAME || 'Guest';
            const color = getAwarenessColor(awareness.clientID);
            awareness.setLocalState({
                user: { name: username, color: color },
                cursor: null
            });
            _sendAwareness();
        }

        // Запрашиваем документ и awareness от других участников
        socket.send(JSON.stringify({ message: { type: 'doc_request' } }));

        // Если через 1.5 сек никто не прислал doc — берём из БД
        setTimeout(() => {
            if (!receivedDocFromPeer && ytext.toString().length === 0) {
                if (typeof INITIAL_CONTENT !== 'undefined' && INITIAL_CONTENT.length > 0) {
                    ydoc.transact(() => { ytext.insert(0, INITIAL_CONTENT); });
                }
            }
        }, 1500);
    };

    socket.onclose = () => {
        if (statusDot) statusDot.classList.remove('online');
        addEvent('System', 'Соединение потеряно');
        if (awareness) {
            awareness.getStates().forEach((_, clientId) => {
                if (clientId !== awareness.clientID) {
                    awareness.getStates().delete(clientId);
                }
            });
            awareness.emit('change', [{ added: [], updated: [], removed: [] }]);
        }
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const payload = data.message;
            if (!payload) return;

            // Запрос документа — отвечаем полным состоянием Yjs
            if (payload.type === 'doc_request') {
                const encodeStateAsUpdate = YLib.encodeStateAsUpdate || YLib.Y?.encodeStateAsUpdate;
                if (encodeStateAsUpdate && ytext.toString().length > 0) {
                    const update = encodeStateAsUpdate(ydoc);
                    socket.send(JSON.stringify({
                        message: { type: 'update', update: Array.from(update) }
                    }));
                }
                // Также отвечаем своим awareness
                _sendAwareness();
            }

            // Обновление документа (CRDT)
            if (payload.type === 'update' && payload.update) {
                const update = new Uint8Array(payload.update);
                const apply = YLib.applyUpdate || YLib.Y?.applyUpdate;
                if (apply) apply(ydoc, update, socket);
                else ydoc.applyUpdate(update, socket);
                // Помечаем что получили doc от другого участника
                if (ytext.toString().length > 0) {
                    receivedDocFromPeer = true;
                }
            }

            // Обновление awareness от другого пользователя
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
                    if (isNew) {
                        addEvent(state?.user?.name || 'User', 'присоединился к комнате');
                    }
                }
            }

            // Удаление участника при отключении
            if (payload.type === 'awareness_remove' && awareness) {
                const { clientId } = payload;
                const state = awareness.getStates().get(clientId);
                const name = state?.user?.name || 'User';
                awareness.getStates().delete(clientId);
                awareness.emit('change', [{ added: [], updated: [], removed: [clientId] }]);
                addEvent(name, 'покинул комнату');
            }

        } catch (e) {
            console.error("Ошибка входящего обновления:", e);
        }
    };

    // Отправка локальных изменений документа
    ydoc.on('update', (update, origin) => {
        if (origin !== socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                message: { type: 'update', update: Array.from(update) }
            }));
        }
    });

    // Автосохранение в БД через 3 секунды после изменения
    let saveTimer = null;
    ydoc.on('update', () => {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            const content = ytext.toString();
            const pid = window.PROJECT_ID;
            if (!pid) return;
            fetch('/sync/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `project_id=${pid}&content=${encodeURIComponent(content)}&version=9999`
            });
        }, 3000);
    });

    // Отправка awareness через WebSocket
    function _sendAwareness() {
        if (!awareness || socket.readyState !== WebSocket.OPEN) return;
        const localState = awareness.getLocalState();
        if (!localState) return;
        socket.send(JSON.stringify({
            message: {
                type: 'awareness',
                clientId: awareness.clientID,
                state: localState
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
        } catch (e) {
            console.error("Ошибка биндинга:", e);
        }
    }

    // Отправляем awareness_remove при закрытии вкладки
    window.addEventListener('beforeunload', () => {
        if (socket && socket.readyState === WebSocket.OPEN && awareness) {
            socket.send(JSON.stringify({
                message: { type: 'awareness_remove', clientId: awareness.clientID }
            }));
        }
    });

    if (typeof initResizer === 'function') initResizer();
});

function getAwarenessColor(clientId) {
    const colors = ['#ff5555','#50fa7b','#ffb86c','#8be9fd','#ff79c6','#bd93f9','#f1fa8c','#6be5fd'];
    return colors[clientId % colors.length];
}

function addEvent(user, action) {
    const container = document.getElementById('timeline-content');
    if (!container) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const card = document.createElement('div');
    card.className = 'event-card';
    card.innerHTML = `<div style="font-size:10px;color:#666;">${timeStr}</div><div><b>${user}:</b> ${action}</div>`;
    container.prepend(card);
}