from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Document, UserProfile
# Убедись, что эти импорты соответствуют твоему проекту:
# from .services import PistonCodeRunner, AIService 

def index(request):
    doc, _ = Document.objects.get_or_create(id=1)
    return render(request, 'editor/index.html', {'doc': doc})

@csrf_exempt
def sync_code(request):
    doc, _ = Document.objects.get_or_create(id=1)
    if request.method == 'POST':
        try:
            client_version = int(request.POST.get('version', 0))
        except (ValueError, TypeError):
            client_version = 0
        
        new_content = request.POST.get('content', '')

        if client_version < doc.version:
            return JsonResponse({
                'status': 'error',
                'message': 'Конфликт! Кто-то другой уже сохранил код.',
                'current_version': doc.version
            }, status=409)

        doc.content = new_content
        doc.version += 1
        doc.save()
        return JsonResponse({'status': 'ok', 'new_version': doc.version})

    return JsonResponse({'content': doc.content, 'version': doc.version})

@csrf_exempt
def run_code(request):
    if request.method == 'POST':
        code = request.POST.get('content', '')
        # runner = PistonCodeRunner() # Раскомментируй, когда будет импорт
        # result = runner.run(code)
        return JsonResponse({'output': 'Код отправлен на выполнение'}) # Пока заглушка
    return JsonResponse({'error': 'Only POST allowed'}, status=405)

@csrf_exempt
def ai_review(request):
    if request.method == 'POST':
        code = request.POST.get('content', '')
        # ai_service = AIService() # Раскомментируй, когда будет импорт
        # hints = ai_service.analyze_code(code)
        return JsonResponse({'hints': 'ИИ анализирует ваш код...'}) # Пока заглушка
    return JsonResponse({'error': 'Only POST allowed'}, status=405)

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('nickname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        project_name = request.POST.get('project_name')

        if not username or not password:
            return JsonResponse({'error': 'Никнейм и пароль обязательны'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Этот никнейм уже занят'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, project_name=project_name)

        return JsonResponse({'status': 'ok', 'message': 'Регистрация успешна!'})
    
    return render(request, 'editor/register.html')