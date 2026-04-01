Вот три шага, которые сделают импорт удобным:

### 1. Создай файл `requirements.txt`
Этот файл скажет компьютерам коллег, какие библиотеки нужно установить (Django, requests и т.д.).
В терминале с активированным `(venv)` выполни:
```powershell
pip freeze > requirements.txt
```
*Теперь в корне проекта появился список всех нужных пакетов.*

---

### 2. Создай `README.md`
[cite_start]Это «лицо» твоего проекта на GitHub[cite: 46]. Создай файл `README.md` в корне и вставь туда этот текст:

```markdown
# AI-Collaborative IDE 2.0 🚀

Прототип веб-IDE с поддержкой совместного редактирования и AI-ревьюером.

## Как запустить проект локально:

1. **Клонируйте репозиторий:**
   ```bash
   git clone [https://github.com/ТВОЙ_ЛОГИН/ai-collaborative-ide.git](https://github.com/ТВОЙ_ЛОГИН/ai-collaborative-ide.git)
   cd ai-collaborative-ide
   ```

2. **Создайте и активируйте виртуальное окружение:**
   ```bash
   python -m venv venv
   # Для Windows:
   venv\Scripts\activate
   # Для Mac/Linux:
   source venv/bin/activate
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Примените миграции базы данных:**
   ```bash
   python manage.py migrate
   ```

5. **Запустите сервер:**
   ```bash
   python manage.py runserver
   ```
   Откройте в браузере: `http://127.0.0.1:8000/`
```

---

