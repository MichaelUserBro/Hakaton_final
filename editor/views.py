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

@login_required # Эта строка не пустит на страницу анонимов
def profile(request):
    return render(request, 'editor/profile.html', {'user': request.user})

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
            # Создаем проект
            new_project = Project.objects.create(name=project_name, creator=request.user)
            # Добавляем создателя в список участников
            new_project.members.add(request.user)
            return redirect('index')
    return render(request, 'editor/create_project.html')


@login_required
def index(request):
    # Берем последнюю комнату, в которой состоит пользователь
    current_project = request.user.projects.last() 
    
    context = {
        'current_project': current_project,
        # ... твои другие данные для редактора (например, doc) ...
    }
    return render(request, 'editor/index.html', context)