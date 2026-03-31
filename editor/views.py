import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Document
from .services import PistonCodeRunner, AIService

# Инициализируем сервисы один раз при запуске
ai_service = AIService()
runner_service = PistonCodeRunner()

def index(request):
    """Главная страница редактора."""
    doc, _ = Document.objects.get_or_create(id=1)
    return render(request, 'editor/index.html', {'doc': doc})

@csrf_exempt
def sync_code(request):
    """Синхронизация содержимого редактора с базой данных."""
    doc, _ = Document.objects.get_or_create(id=1)
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                doc.content = data.get('content', '')
            else:
                doc.content = request.POST.get('content', '')
            doc.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'content': doc.content})

@csrf_exempt
def run_code(request):
    """Запуск кода через Piston API."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            
            # Используем глобальный экземпляр runner_service
            result = runner_service.run(code)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                "stdout": "",
                "stderr": f"System Error: {str(e)}",
                "error": True
            }, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def ai_review(request):
    """Получение автоматических советов от AI (верхняя плашка)."""
    try:
        # Берем актуальный контент из БД
        doc = Document.objects.get(id=1)
        if not doc.content.strip():
            return JsonResponse({'hints': ["Напишите код, чтобы получить совет"]})
            
        hints = ai_service.analyze_code(doc.content)
        return JsonResponse({'hints': hints})
    except Exception as e:
        # Если здесь летит 401, значит проблема в ключе в .env
        return JsonResponse({'hints': [f"AI Service Error: {str(e)}"]}, status=200)

@csrf_exempt
def resolve_ai_conflict(request):
    """Улучшение строки или разрешение конфликтов (кнопка ИИ)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_a = data.get("variant_a", "")
            variant_b = data.get("variant_b", "")
            
            # Убрали жесткую блокировку 'if not variant_b', 
            # чтобы кнопка "Fix Line" работала с одной строкой
            if not variant_a:
                return JsonResponse({'error': 'No code provided'}, status=400)
            
            # Вызываем ИИ для анализа
            best_option = ai_service.resolve_conflict(variant_a, variant_b)
            return JsonResponse({'resolved_code': best_option})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)