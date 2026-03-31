import os
import json
import requests
from abc import ABC, abstractmethod
from openai import OpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Константа для движка выполнения кода
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
        # Используем OpenRouter как прокси
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        # Выбираем стабильную бесплатную модель Gemini Flash
        self.model = "deepseek/deepseek-chat"
        
        self.system_prompt = (
            "Ты — эксперт по Python. Анализируй код на наличие антипаттернов и уязвимостей. "
            "Отвечай СТРОГО в формате JSON: {'hints': ['совет 1', 'совет 2']}. "
            "Не пиши ничего, кроме этого JSON."
        )

    def analyze_code(self, code: str):
        """Отправляет код нейросети для получения советов в формате JSON."""
        if not os.getenv("OPENROUTER_API_KEY"):
            return ["AI Error: Ключ OPENROUTER_API_KEY не найден в .env"]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Проанализируй этот код:\n{code}"},
                ],
                # Ограничиваем токены, чтобы не вылетать по ошибке 402
                max_tokens=500,
                response_format={'type': 'json_object'}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('hints', ["AI: Ошибок не обнаружено."])
            
        except Exception as e:
            return [f"AI Service Error: {str(e)}"]

    def resolve_conflict(self, code_variant_a: str, code_variant_b: str):
        """Просит AI выбрать лучший вариант из двух предложенных."""
        if not os.getenv("OPENROUTER_API_KEY"):
            return "Ошибка: API ключ не найден."

        prompt = (
            f"У меня есть два варианта одной строки кода:\n"
            f"Вариант А: {code_variant_a}\n"
            f"Вариант Б: {code_variant_b}\n"
            f"Выбери лучший вариант или предложи идеальный объединенный вариант. "
            f"Ответь коротко, только кодом и кратким пояснением в одну строку."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты — помощник по код-ревью."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при разрешении конфликта: {str(e)}"


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
            
            # Приоритет вывода: stdout -> compile_output -> stderr
            output = (
                result.get('stdout') or 
                result.get('compile_output') or 
                result.get('stderr')
            )
            return output if output else "Код выполнен (пустой вывод)"
        except Exception as e:
            return f"Ошибка песочницы: {str(e)}"