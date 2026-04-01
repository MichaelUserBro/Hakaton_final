from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm
import subprocess
import sys
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Document, UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from .models import Project
# Убедись, что эти импорты соответствуют твоему проекту:
# from .services import PistonCodeRunner, AIService 
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
        # Получаем код из редактора
        code = request.POST.get('content', '')
        
        try:
            # Запускаем код через подпроцесс Python
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=5 # Чтобы сервер не завис, если в коде бесконечный цикл
            )
            
            # Если код упал с ошибкой, берем stderr, если выполнился — stdout
            output = result.stdout if result.returncode == 0 else result.stderr
            
            # Если в коде не было print(), выводим подсказку
            if not output:
                output = "Код выполнен, но вывода нет. Добавьте print()."
                
            return JsonResponse({'output': output})
            
        except Exception as e:
            # Если сломался сам сервер при запуске
            return JsonResponse({'output': f"Ошибка запуска: {str(e)}"})
            
    # Если кто-то зашел через GET (как на твоем скрине с ошибкой 405)
    return JsonResponse({'error': 'Метод не поддерживается. Используйте POST'}, status=405)

@csrf_exempt
def ai_review(request):

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

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save() # Сохраняем пользователя в переменную
            login(request, user) # <--- ВОТ ЭТА СТРОКА автоматически "впускает" пользователя
            
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт {username} успешно создан!')
            return redirect('index') 
    else:
        form = UserRegisterForm()
    return render(request, 'editor/register.html', {'form': form})

@login_required
def profile(request):
    # Получаем комнаты, созданные текущим пользователем
    user_created_rooms = request.user.created_projects.all()
    
    # Передаем всё одним словарем
    return render(request, 'editor/profile.html', {
        'user': request.user,
        'created_rooms': user_created_rooms
    })

# editor/views.py
from django.contrib.auth import logout

def logout_user(request):
    logout(request)
    return redirect('index') # После выхода возвращаем на главную

@login_required
def create_project(request):
    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        if project_name:
            new_project = Project.objects.create(name=project_name, creator=request.user)
            new_project.members.add(request.user)
            
            # Сразу создаем первый файл для этой комнаты
            from .models import Document
            Document.objects.create(project=new_project, name="main.py", content="")
            
            # ПРАВИЛЬНО: Редирект в созданную комнату
            return redirect(f'/?project_id={new_project.id}')
            
    return render(request, 'editor/create_project.html')


# @login_required
def index(request):
    current_project = None
    doc = None

    if request.user.is_authenticated:
        # Пытаемся получить конкретный ID из ссылки (?project_id=...)
        project_id = request.GET.get('project_id')
        
        if project_id:
            # Ищем конкретную комнату среди проектов пользователя
            current_project = request.user.projects.filter(id=project_id).first()
        
        # Если ID не передан или проект не найден, берем последний из списка
        if not current_project:
            current_project = request.user.projects.last()

        # Если проект найден (или взят последний), получаем его документ
        if current_project:
            doc = current_project.documents.first()
            
            # ВАЖНО: Если в комнате еще нет файла, создаем его "на лету"
            if not doc:
                from .models import Document
                doc = Document.objects.create(
                    project=current_project, 
                    name="main.py", 
                    content=""
                )

    # Твоя логика сохранения (из image_742a1e.png)
    if request.method == 'POST' and doc:
        try:
            import json
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                doc.content = data.get('content', '')
            else:
                doc.content = request.POST.get('content', '')
            doc.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    # Твой контекст и рендер
    context = {
        'current_project': current_project,
        'doc': doc,
    }
    return render(request, 'editor/index.html', context)

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


from django.shortcuts import get_object_or_404

def join_project(request, token):
    # Ищем проект по его секретному токену
    project = get_object_or_404(Project, invite_token=token)
    
    if request.user.is_authenticated:
        # Добавляем пользователя в список участников
        project.members.add(request.user)
        return redirect('index') 
    else:
        # Если не вошел — отправляем на регистрацию
        return redirect('register')