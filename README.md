# AI Collaborative IDE 🚀

Веб-редактор кода с совместной работой в реальном времени и AI-функциями.

## Стек технологий

- **Backend:** Django 6.0.3 + Daphne + Django Channels (WebSocket)
- **Frontend:** Vanilla JS + Ace Editor + Yjs (CRDT)
- **AI:** Groq API (llama-3.1-8b-instant)
- **Запуск кода:** Judge0 API
- **БД:** SQLite

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/MichaelUserBro/Hakaton_final.git
cd Hakaton_final
git checkout main
```

### 2. Создать виртуальное окружение

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

```bash
cd hackathon_ide
cp .env.example .env
```

Файл `.env` с рабочим API ключом уже готов — ничего менять не нужно.

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Запустить сервер

```bash
python manage.py runserver
```

Открой браузер: **http://localhost:8000**

---

## Функционал

### 👥 Совместная разработка
- Создай комнату через кнопку **+ New Room**
- Скопируй инвайт-ссылку через кнопку **🔗 Invite** в профиле
- Другой пользователь вставляет ссылку в **Join Room**
- Код синхронизируется в реальном времени через Yjs CRDT
- Видны курсоры и ники всех участников

### 🤖 AI-функции
| Кнопка | Описание |
|--------|----------|
| 📝 Подсказки | Добавляет блок советов в начало файла |
| 🏷 Переименование | Переименовывает переменные по PEP8 |
| 📖 Читаемость | Улучшает читаемость кода |
| 🐞 Исправить ошибку | Анализирует traceback и предлагает фикс |

> Выдели часть кода перед нажатием — AI обработает только выделенное

### ▶ Запуск кода
- Нажми **RUN** или `Ctrl+Enter`
- Результат появится в консоли снизу
- Консоль накапливает вывод, очищается кнопкой 🗑

### 🎨 Настройки
- Три темы интерфейса: Dark, Light, Hacker
- Четыре темы редактора: Monokai, GitHub, Terminal, Dracula
- Размер шрифта: 12–18px

---

## Структура проекта

```
hackathon_ide/
├── core/               # Настройки Django
│   ├── settings.py
│   ├── asgi.py
│   └── urls.py
├── editor/             # Основное приложение
│   ├── models.py       # Document, Project, UserProfile
│   ├── views.py        # Все вьюхи
│   ├── services.py     # AIService, PistonCodeRunner
│   ├── consumers.py    # WebSocket consumer
│   ├── templates/
│   └── static/js/
│       ├── editor-sync.js  # Yjs + WebSocket синхронизация
│       ├── y-ace.js        # Биндинг Ace + курсоры
│       ├── main.js         # Кнопки Run и AI
│       └── yjs.js          # Yjs библиотека
├── media/              # Аватарки пользователей
├── requirements.txt
├── .env.example        # Готовый конфиг с API ключом
└── .env                # Создаётся через cp .env.example .env
```

---

## Возможные проблемы

**WebSocket не подключается** — убедись что сервер запущен через `python manage.py runserver`.

**AI не работает** — проверь что `.env` файл находится в папке `hackathon_ide/` рядом с `manage.py`.

**Ошибка при миграциях** — удали `db.sqlite3` и запусти `migrate` заново.