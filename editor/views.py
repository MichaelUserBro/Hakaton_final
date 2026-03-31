import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Document
from .services import PistonCodeRunner, AIService 

# Инициализируем сервисы на уровне модуля для переиспользования
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
        # Поддержка как обычного POST, так и JSON (для разных фронтенд-подходов)
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            doc.content = data.get('content', '')
        else:
            doc.content = request.POST.get('content', '')
            
        doc.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'content': doc.content})

def run_code(request):
    """Запуск кода через песочницу Judge0."""
    try:
        doc = Document.objects.get(id=1)
        output = runner_service.run(doc.content)
        return JsonResponse({'output': output})
    except Exception as e:
        return JsonResponse({'output': f"Ошибка выполнения: {str(e)}"}, status=500)

@csrf_exempt
def ai_review(request):
    """Получение глубокого анализа кода от LLM (DeepSeek)."""
    try:
        doc = Document.objects.get(id=1)
        hints = ai_service.analyze_code(doc.content)
        return JsonResponse({'hints': hints})
    except Exception as e:
        return JsonResponse({'hints': [f"Ошибка AI: {str(e)}"]}, status=500)

@csrf_exempt
def resolve_ai_conflict(request):
    """Новая функция: разрешение конфликтов между двумя вариантами строк."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_a = data.get("variant_a", "")
            variant_b = data.get("variant_b", "")
            
            if not variant_a or not variant_b:
                return JsonResponse({'error': 'Необходимо предоставить оба варианта кода'}, status=400)
                
            best_option = ai_service.resolve_conflict(variant_a, variant_b)
            return JsonResponse({'resolved_code': best_option})
        except Exception as e:
            return JsonResponse({'error': f"Ошибка при разрешении конфликта: {str(e)}"}, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)