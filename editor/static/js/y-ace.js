/**
 * @module bindings/ace
 * @description Биндинг Ace для Yjs с отображением курсоров других пользователей
 */

const CURSOR_COLORS = [
    '#ff5555', '#50fa7b', '#ffb86c', '#8be9fd',
    '#ff79c6', '#bd93f9', '#f1fa8c', '#6be5fd'
];

function getColor(clientId) {
    return CURSOR_COLORS[clientId % CURSOR_COLORS.length];
}

if (!document.getElementById('cursor-styles')) {
    const style = document.createElement('style');
    style.id = 'cursor-styles';
    style.textContent = `
        .remote-cursor {
            position: absolute;
            width: 2px;
            pointer-events: none;
            z-index: 100;
        }
        .remote-cursor-label {
            position: absolute;
            top: -18px;
            left: 0;
            font-size: 11px;
            padding: 1px 5px;
            border-radius: 3px;
            color: #fff;
            white-space: nowrap;
            pointer-events: none;
            z-index: 101;
        }
        .online-user-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 8px;
            border-radius: 4px;
            margin-bottom: 4px;
            font-size: 11px;
            border: 1px solid #30363D;
            background: #21262D;
        }
        .online-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #3FB950;
            flex-shrink: 0;
        }
    `;
    document.head.appendChild(style);
}

class AceBinding {
    constructor(type, editor, awareness) {
        this.type = type;
        this.editor = editor;
        this.awareness = awareness;
        this.doc = type.doc;
        this._mux = false;
        this._cursors = {};

        this._initContent();
        this._setupObservers();

        if (awareness) {
            this._setupAwareness();
        }
    }

    _initContent() {
        this._mux = true;
        this.editor.setValue(this.type.toString(), -1);
        this._mux = false;
    }

    _setupObservers() {
        const session = this.editor.session;

        this._typeObserver = (event) => {
            if (this._mux) return;
            this._mux = true;

            const doc = session.getDocument();
            let index = 0;

            event.delta.forEach(op => {
                if (op.retain) {
                    index += op.retain;
                } else if (op.insert) {
                    const pos = doc.indexToPosition(index);
                    doc.insert(pos, op.insert);
                    index += op.insert.length;
                } else if (op.delete) {
                    const pos = doc.indexToPosition(index);
                    const endPos = doc.indexToPosition(index + op.delete);
                    const Range = ace.require("ace/range").Range;
                    doc.remove(new Range(pos.row, pos.column, endPos.row, endPos.column));
                }
            });
            this._mux = false;
        };
        this.type.observe(this._typeObserver);

        this._aceObserver = (delta) => {
            if (this._mux) return;
            this._mux = true;

            const doc = session.getDocument();
            const offset = doc.positionToIndex(delta.start);
            const text = delta.lines.join(session.getNewLineMode() === "windows" ? "\r\n" : "\n");

            if (delta.action === "insert") {
                this.type.insert(offset, text);
            } else if (delta.action === "remove") {
                this.type.delete(offset, text.length);
            }
            this._mux = false;
        };
        session.on("change", this._aceObserver);
    }

    _setupAwareness() {
        const awareness = this.awareness;
        const editor = this.editor;

        // Берём username из window.CURRENT_USERNAME (передаётся из Django)
        const username = window.CURRENT_USERNAME || ('User_' + Math.floor(Math.random() * 1000));
        const myColor = getColor(awareness.clientID);

        awareness.setLocalStateField('user', {
            name: username,
            color: myColor
        });

        // Отправляем позицию курсора при движении
        this._cursorObserver = () => {
            const cursor = editor.getCursorPosition();
            const doc = editor.session.getDocument();
            const index = doc.positionToIndex(cursor);
            awareness.setLocalStateField('cursor', {
                index,
                row: cursor.row,
                column: cursor.column
            });
        };
        editor.selection.on('changeCursor', this._cursorObserver);

        // Слушаем изменения awareness — курсоры + список участников
        this._awarenessObserver = ({ added, updated, removed }) => {
            [...added, ...updated].forEach(clientId => {
                if (clientId === awareness.clientID) return;
                const state = awareness.getStates().get(clientId);
                if (state && state.cursor) {
                    this._renderCursor(clientId, state);
                }
            });
            removed.forEach(clientId => {
                this._removeCursor(clientId);
            });

            // Обновляем список онлайн-участников в сайдбаре
            this._updateUserList();
        };
        awareness.on('change', this._awarenessObserver);
    }

    _updateUserList() {
        const awareness = this.awareness;
        const userList = document.getElementById('user-list');
        if (!userList) return;

        const myUsername = window.CURRENT_USERNAME || 'You';

        // Собираем всех участников кроме себя
        const others = [];
        awareness.getStates().forEach((state, clientId) => {
            if (clientId === awareness.clientID) return;
            if (state && state.user) {
                others.push({ clientId, user: state.user });
            }
        });

        // Перерисовываем список — себя оставляем первым
        userList.innerHTML = `
            <div class="online-user-badge">
                <span class="online-dot"></span>
                <div style="width:20px;height:20px;border-radius:50%;background:${getColor(awareness.clientID)};display:flex;justify-content:center;align-items:center;flex-shrink:0;">
                    <span style="font-size:9px;color:white;font-weight:bold;">${myUsername.slice(0,1).toUpperCase()}</span>
                </div>
                <span>${myUsername} (you)</span>
            </div>
        `;

        others.forEach(({ clientId, user }) => {
            const badge = document.createElement('div');
            badge.className = 'online-user-badge';
            badge.innerHTML = `
                <span class="online-dot" style="background:${user.color};"></span>
                <div style="width:20px;height:20px;border-radius:50%;background:${user.color};display:flex;justify-content:center;align-items:center;flex-shrink:0;">
                    <span style="font-size:9px;color:white;font-weight:bold;">${user.name.slice(0,1).toUpperCase()}</span>
                </div>
                <span>${user.name}</span>
            `;
            userList.appendChild(badge);
        });
    }

    _renderCursor(clientId, state) {
        const { cursor, user } = state;
        if (!cursor) return;

        const editor = this.editor;
        const color = user?.color || getColor(clientId);
        const name = user?.name || ('User ' + clientId);

        this._removeCursor(clientId);

        const renderer = editor.renderer;
        const screenPos = renderer.textToScreenCoordinates(cursor.row, cursor.column);
        const editorEl = editor.container;
        const editorRect = editorEl.getBoundingClientRect();

        const x = screenPos.pageX - editorRect.left;
        const y = screenPos.pageY - editorRect.top;
        const lineHeight = renderer.lineHeight;

        const cursorEl = document.createElement('div');
        cursorEl.className = 'remote-cursor';
        cursorEl.style.cssText = `left:${x}px;top:${y}px;height:${lineHeight}px;background:${color};`;

        const label = document.createElement('div');
        label.className = 'remote-cursor-label';
        label.style.background = color;
        label.textContent = name;
        cursorEl.appendChild(label);

        editorEl.style.position = 'relative';
        editorEl.appendChild(cursorEl);

        this._cursors[clientId] = cursorEl;
    }

    _removeCursor(clientId) {
        if (this._cursors[clientId]) {
            this._cursors[clientId].remove();
            delete this._cursors[clientId];
        }
    }

    destroy() {
        this.type.unobserve(this._typeObserver);
        this.editor.session.off("change", this._aceObserver);
        if (this.awareness) {
            this.awareness.off('change', this._awarenessObserver);
            this.editor.selection.off('changeCursor', this._cursorObserver);
        }
        Object.keys(this._cursors).forEach(id => this._removeCursor(id));
        this.type = null;
        this.editor = null;
    }
}

window.AceBinding = AceBinding;