import os
import json
import requests
import google.generativeai as genai
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Константа для движка выполнения кода (Judge0)
JUDGE0_URL = "https://ce.judge0.com/submissions?wait=true"

# --- Абстрактные интерфейсы ---

class BaseAIService(ABC):
    @abstractmethod
    def analyze_code(self, code: str):
        pass

    @abstractmethod
    def resolve_conflict(self, code_variant_a: str, code_variant_b: str):
        pass

class BaseRunnerService(ABC):
    @abstractmethod
    def run(self, code: str):
        pass

# --- Реализация сервисов ---

class AIService(BaseAIService):
    def __init__(self):
        # Инициализация Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        
        # Используем 1.5-flash-8b: у нее выше лимиты запросов на бесплатном тарифе
        self.model = genai.GenerativeModel('models/gemini-flash-latest')
        
        self.system_instructions = (
            "Ты — эксперт по Python. Дай 3 очень коротких совета по коду. "
            "Отвечай СТРОГО в формате JSON: {'hints': ['совет 1', 'совет 2', 'совет 3']}. "
            "Не пиши пояснений вне JSON. Используй русский язык."
        )

    def analyze_code(self, code: str):
        """Отправляет код Gemini для получения советов в формате JSON."""
        if not os.getenv("GOOGLE_API_KEY"):
            return ["AI Error: Ключ GOOGLE_API_KEY не найден"]

        try:
            prompt = f"{self.system_instructions}\n\nКод для анализа:\n{code}"
            response = self.model.generate_content(prompt)
            
            # Очистка текста от markdown-разметки для корректного парсинга JSON
            raw_text = response.text.strip()
            clean_json = raw_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(clean_json)
            return result.get('hints', ["AI: Советы не сформированы."])
            
        except Exception as e:
            # Выводим сокращенную ошибку, чтобы не перегружать интерфейс
            return [f"AI Error: {str(e)[:100]}"]

    def resolve_conflict(self, code_variant_a: str, code_variant_b: str):
        """Просит AI выбрать лучший вариант из двух предложенных."""
        if not os.getenv("GOOGLE_API_KEY"):
            return "Ошибка: API ключ не найден."

        prompt = (
            f"Ты помощник по коду. Есть два варианта:\n"
            f"А: {code_variant_a}\n"
            f"Б: {code_variant_b}\n"
            f"Выбери лучший или объедини. Ответь ТОЛЬКО кодом (без пояснений)."
        )

        try:
            response = self.model.generate_content(prompt)
            # Очищаем результат от оберток кода
            return response.text.strip().replace('```python', '').replace('```', '')
        except Exception as e:
            return f"Ошибка кнопки: {str(e)[:50]}"


class PistonCodeRunner(BaseRunnerService):
    def run(self, code: str):
        """Отправляет код на выполнение в песочницу Judge0."""
        payload = {
            "source_code": code,
            "language_id": 71,  # Python 3
            "stdin": ""
        }
        try:
            response = requests.post(JUDGE0_URL, json=payload, timeout=10)
            result = response.json()
            
            stdout = result.get('stdout') or ""
            stderr = result.get('stderr') or result.get('compile_output') or ""
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "error": bool(stderr)
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Ошибка песочницы: {str(e)}",
                "error": True
            }