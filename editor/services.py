# import requests
# import json
# from abc import ABC, abstractmethod

# # 1. Сначала определяем БАЗОВЫЕ классы (чтобы не было NameError)
# class BaseAIService(ABC):
#     @abstractmethod
#     def analyze_code(self, code: str):
#         pass

# class BaseRunnerService(ABC):
#     @abstractmethod
#     def run(self, code: str):
#         pass

# # 2. Теперь реализация запуска через Judge0
# class PistonCodeRunner(BaseRunnerService):
#     def run(self, code: str):

#         TEST_URL = "https://ce.judge0.com/submissions?wait=true"
#         payload = {
#             "source_code": code,
#             "language_id": 71, # Python
#             "stdin": ""
#         }
#         try:
#             response = requests.post(TEST_URL, json=payload, timeout=10)
#             result = response.json()
#             output = result.get('stdout') or result.get('compile_output') or result.get('stderr')
#             return output if output else "Код выполнен (пустой вывод)"
#         except Exception as e:
#             return f"Ошибка песочницы: {str(e)}"

# # 3. Реализация AI-ревьюера
# class AIService(BaseAIService):
#     def analyze_code(self, code: str):
#         hints = []
#         if "import *" in code:
#             hints.append("AI: Избегайте 'import *'.")
#         if "except:" in code:
#             hints.append("AI: Укажите тип ошибки в 'except:'.")
#         return hints if hints else ["AI: Код выглядит чистым!"]



import requests
from abc import ABC, abstractmethod

# Константа для нового рабочего движка
JUDGE0_URL = "https://ce.judge0.com/submissions?wait=true"

class BaseAIService(ABC):
    @abstractmethod
    def analyze_code(self, code: str):
        pass

class BaseRunnerService(ABC):
    @abstractmethod
    def run(self, code: str):
        pass

class PistonCodeRunner(BaseRunnerService):
    def run(self, code: str):
        payload = {
            "source_code": code,
            "language_id": 71,  # Python 3
            "stdin": ""
        }
        try:
            response = requests.post(JUDGE0_URL, json=payload, timeout=10)
            result = response.json()
            # Берем стандартный вывод или ошибку компиляции
            output = result.get('stdout') or result.get('compile_output') or result.get('stderr')
            return output if output else "Код выполнен (пустой вывод)"
        except Exception as e:
            return f"Ошибка песочницы: {str(e)}"

class AIService(BaseAIService):
    def analyze_code(self, code: str):
        hints = []
        if "import *" in code:
            hints.append("AI: Избегайте 'import *', это засоряет пространство имен.")
        if "except:" in code:
            hints.append("AI: Пустой 'except:' — плохая практика. Укажите тип ошибки.")
        return hints if hints else ["AI: Код выглядит чистым!"]