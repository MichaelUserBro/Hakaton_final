from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Document
import requests

def index(request):
    doc, _ = Document.objects.get_or_create(id=1)
    return render(request, 'editor/index.html', {'doc': doc})

@csrf_exempt
def sync_code(request):
    doc, _ = Document.objects.get_or_create(id=1)
    if request.method == 'POST':
        doc.content = request.POST.get('content', '')
        doc.save()
        # Тут можно добавить логику проверки конфликтов через AI [cite: 20, 21]
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'content': doc.content})


def run_code(request):
    doc = Document.objects.get(id=1)
    payload = {
        "language": "python",
        "version": "3.10.0",
        "files": [{"content": doc.content}]
    }
    try:
        response = requests.post("https://emkc.org/api/v2/piston/execute", json=payload)
        result = response.json()
        output = result.get('run', {}).get('output', 'Ошибка выполнения')
    except Exception as e:
        output = f"Ошибка связи с песочницей: {str(e)}"
    
    return JsonResponse({'output': output})

@csrf_exempt
def ai_review(request):
    doc = Document.objects.get(id=1)
    code = doc.content
    
    # Здесь должен быть запрос к API (OpenAI/Anthropic/DeepSeek)
    # Для хакатона, если нет ключа, можно сделать "умную заглушку", 
    # которая ищет типичные ошибки Python:
    hints = []
    if "import *" in code:
        hints.append("AI: Избегайте 'import *', это загрязняет пространство имен.")
    if "except:" in code:
        hints.append("AI: Пустой 'except:' — плохая практика. Укажите конкретное исключение.")
    if len(code) > 0 and "def " not in code:
        hints.append("AI: Рекомендуется оборачивать логику в функции.")
    
    return JsonResponse({'hints': hints if hints else ["AI: Код выглядит чистым!"]})