import os
import json
import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Используем Judge0 для выполнения кода
JUDGE0_URL = "https://ce.judge0.com/submissions?wait=true"

class BaseAIService(ABC):
    @abstractmethod
    def process_action(self, action: str, code: str, error_log: str = None):
        pass

class BaseRunnerService(ABC):
    @abstractmethod
    def run(self, code: str):
        pass

class AIService(BaseAIService):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        # Инициализируем клиент только если есть ключ
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        # Согласно тестам, модель llama-3.1-8b-instant работает стабильно
        self.model_id = "llama-3.1-8b-instant" 

    def _get_ai_response(self, system_prompt: str, user_prompt: str, force_json: bool = False):
        if not self.client:
            return {"error": "GROQ_API_KEY missing в .env файле"}
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                # Если нужен JSON, Groq требует упоминания слова 'json' в системном промте
                response_format={"type": "json_object"} if force_json else None
            )
            text = completion.choices[0].message.content.strip()
            
            if force_json:
                return json.loads(text)
            
            # Очистка от markdown-блоков ```python ... ```, которые часто лепит ИИ
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("python"):
                    text = text[6:]
                text = text.strip()
                
            return text
        except Exception as e:
            return {"error": f"Groq API Error: {str(e)}"}

    def process_action(self, action: str, code: str, error_log: str = None):
        if not code.strip():
            return {"error": "Код пуст. Напишите что-нибудь в редакторе."}

        # 1. Логика исправления ошибок (Action: fix_error)
        if action == 'fix_error':
            system_msg = "You are a Python debugging assistant. You must respond ONLY with a JSON object containing 'explanation' and 'result' keys."
            user_msg = f"Fix this error.\nERROR LOG:\n{error_log}\n\nCODE:\n{code}"
            res = self._get_ai_response(system_msg, user_msg, force_json=True)
            return res # Вернет {'explanation': '...', 'result': '...'}

        # 2. Логика рефакторинга и советов
        prompts = {
            'hints': (
                "You are a senior developer.",
                f"Identify 3 areas of improvement for this code. Return them as brief Python comments at the top of the code:\n{code}"
            ),
            'rename': (
                "You are a code formatter.",
                f"Refactor the following code to use snake_case for all variables and functions. Return ONLY the executable code:\n{code}"
            ),
            'readable': (
                "You are a code style expert.",
                f"Improve the readability of this code (pep8, spacing). Return ONLY the executable code:\n{code}"
            )
        }

        if action in prompts:
            system_msg, user_msg = prompts[action]
            res = self._get_ai_response(system_msg, user_msg)
            
            if isinstance(res, dict) and "error" in res:
                return res
            return {"result": res}

        return {"error": "Неизвестное действие"}

class PistonCodeRunner(BaseRunnerService):
    """Выполнение кода через публичный API Judge0"""
    def run(self, code: str):
        try:
            # language_id 71 — это Python 3.8.1
            payload = {
                "source_code": code,
                "language_id": 71,
                "stdin": ""
            }
            response = requests.post(JUDGE0_URL, json=payload, timeout=10)
            result = response.json()
            
            # Собираем вывод
            stdout = result.get('stdout') or ""
            stderr = result.get('stderr') or ""
            compile_output = result.get('compile_output') or ""
            
            full_error = stderr + compile_output
            
            return {
                "stdout": stdout,
                "stderr": full_error,
                "error": bool(full_error)
            }
        except Exception as e:
            return {"stdout": "", "stderr": f"Runner Error: {str(e)}", "error": True}