import os
import json
import requests
import base64
import time
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

        # Согласно тестам, модель llama-3.1-8b-instant работает стабильно

        self.client = Groq(api_key=self.api_key) if self.api_key else None
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

                # Если нужен JSON, Groq требует упоминания слова 'json' в системном промте

                temperature=0.1,

                response_format={"type": "json_object"} if force_json else None
            )
            text = completion.choices[0].message.content.strip()
            
            if force_json:
                return json.loads(text)
            
            if "```" in text:
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else parts[0]
                if text.lower().startswith("python"):
                    text = text[6:]
                text = text.strip()
                
            return text
        except Exception as e:
            return {"error": f"Ошибка Groq API: {str(e)}"}

    def process_action(self, action: str, code: str, error_log: str = None):
        if not code.strip():
            return {"error": "Редактор пуст. Напишите код перед использованием ИИ."}

        if action == 'fix_error':
            is_actually_error = error_log and ("Error" in error_log or "Traceback" in error_log)
            if not is_actually_error:
                return {
                    "explanation": "Последний запуск прошел успешно. Ошибок в коде не обнаружено!",
                    "result": code
                }

            system_msg = (
                "Ты — эксперт по Python. Твоя задача: ИСПРАВИТЬ ОШИБКУ. "
                "Используй предоставленный Traceback для точного определения места падения. "
                "Отвечай СТРОГО в формате JSON с ключами: 'explanation' (на русском) и 'result' (код)."
            )
            user_msg = f"ЛОГ ВЫПОЛНЕНИЯ:\n{error_log}\n\nКОД:\n{code}"
            return self._get_ai_response(system_msg, user_msg, force_json=True)

        prompts = {
            'hints': (
                "Ты — эксперт по статическому анализу кода (Code Reviewer). "
                "Твоя задача: проанализировать код на антипаттерны и ошибки стиля. "
                "ПРАВИЛА:\n"
                "1. СТРОГО ЗАПРЕЩЕНО менять исполняемый код.\n"
                "2. Добавь краткие советы (#) на русском языке ТОЛЬКО в начало файла.\n"
                "3. Верни оригинальный код без изменений в логике.",
                f"Проведи аудит. Добавь советы в начало как комментарии, НЕ ТРОГАЙ сам код:\n{code}"
            ),
            'rename': (
                "Ты — эксперт по именованию в Python (PEP8). Твоя задача: переименовать переменные и функции. "
                "КРИТЕРИИ:\n1. Используй snake_case.\n2. Имена должны быть короткими.\n"
                "3. Избегай транслита.\n4. СТРОГО ЗАПРЕЩЕНО менять структуру.\n"
                "5. Верни ТОЛЬКО исправленный код.",
                f"Оптимизируй названия переменных и функций в этом коде:\n{code}"
            ),
            'readable': (
                "Ты — мастер чистого кода. Сделай код максимально читаемым, сохраняя оригинальную логику. "
                "Верни ТОЛЬКО код.",
                f"Сделай этот код понятнее и чище, СТРОГО сохраняя оригинальную логику:\n{code}"
            )
        }

        if action in prompts:
            system_msg, user_msg = prompts[action]
            res = self._get_ai_response(system_msg, user_msg)
            if isinstance(res, dict) and "error" in res:
                return res
            return {"result": res}

        return {"error": "Действие не распознано"}

class PistonCodeRunner(BaseRunnerService):
    def run(self, code: str):
        try:
            encoded_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')
            url = f"{JUDGE0_URL}?wait=true&base64_encoded=true"
            payload = {
                "source_code": encoded_code,
                "language_id": 71,
                "stdin": ""
            }
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            
            def safe_decode(data):
                if not data: return ""
                try:
                    return base64.b64decode(data).decode('utf-8')
                except Exception:
                    return str(data)

            stdout = safe_decode(result.get('stdout'))
            stderr = safe_decode(result.get('stderr'))
            compile_output = safe_decode(result.get('compile_output'))
            message = safe_decode(result.get('message'))
            status_id = result.get('status', {}).get('id')

            full_error = stderr + compile_output
            if not stdout and status_id and status_id > 3:
                full_error = full_error or message or f"Ошибка выполнения (ID: {status_id})"

            return {
                "stdout": stdout,
                "stderr": full_error,
                "error": bool(full_error) or (status_id is not None and status_id > 3)
            }
        except Exception as e:
            return {"stdout": "", "stderr": f"Ошибка в Runner: {str(e)}", "error": True}
