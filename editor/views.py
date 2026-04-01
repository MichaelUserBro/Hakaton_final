import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages

from .models import Document, UserProfile, Project
from .forms import UserRegisterForm
from .services import PistonCodeRunner, AIService

# Инициализируем сервисы один раз при запуске
ai_service = AIService()
runner_service = PistonCodeRunner()

def index(request):
    """Главная страница редактора с выбором проекта."""
    current_project = None
    doc = None

    if request.user.is_authenticated:
        project_id = request.GET.get('project_id')
        
        if project_id:
            current_project = request.user.projects.filter(id=project_id).first()
        
        if not current_project:
            current_project = request.user.projects.last()

        if current_project:
            doc = current_project.documents.first()
            if not doc:
                doc = Document.objects.create(
                    project=current_project, 
                    name="main.py", 
                    content=""
                )
    else:
        # Для неавторизованных берем временный документ
        doc, _ = Document.objects.get_or_create(id=1, defaults={'name': 'temp.py', 'content': ''})

    return render(request, 'editor/index.html', {
        'current_project': current_project,
        'doc': doc,
    })

@csrf_exempt
def sync_code(request):
    """Синхронизация содержимого редактора."""
    if request.method == 'POST':
        try:
            project_id = request.POST.get('project_id')
            client_version = int(request.POST.get('version', 0))
            new_content = request.POST.get('content', '')

            if project_id and project_id != 'None' and project_id != '':
                doc = get_object_or_404(Document, project_id=project_id)
            else:
                doc = get_object_or_404(Document, id=1)

            # Проверка на конфликт версий
            if client_version < doc.version:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Конфликт версий',
                    'current_version': doc.version,
                    'content': doc.content
                }, status=409)

            if new_content != doc.content:
                doc.content = new_content
                doc.version += 1
                doc.save()
            
            return JsonResponse({'status': 'ok', 'new_version': doc.version})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)

@csrf_exempt
def run_code(request):
    """Запуск кода через Piston API."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            result = runner_service.run(code)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({"stderr": f"System Error: {str(e)}", "error": True}, status=500)
    return JsonResponse({"error": "POST required"}, status=405)

@csrf_exempt
def ai_action(request):
    """Универсальный метод для всех AI функций Groq."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            action = data.get('action', '')
            error_log = data.get('error_log', '')

            if not code.strip():
                return JsonResponse({'error': 'Код пуст'}, status=400)

            result = ai_service.process_action(action, code, error_log)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'POST required'}, status=405)

# --- Аккаунты и проекты ---

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Аккаунт {user.username} создан!')
            return redirect('index')
    else:
        form = UserRegisterForm()
    return render(request, 'editor/register.html', {'form': form})

@login_required
def create_project(request):
    if request.method == 'POST':
        name = request.POST.get('project_name')
        if name:
            project = Project.objects.create(name=name, creator=request.user)
            project.members.add(request.user)
            Document.objects.create(project=project, name="main.py", content="")
            return redirect(f'/?project_id={project.id}')
    return render(request, 'editor/create_project.html')

@login_required
def profile(request):
    return render(request, 'editor/profile.html', {
        'user': request.user,
        'created_rooms': request.user.created_projects.all()
    })

def logout_user(request):
    logout(request)
    return redirect('index')

def join_project(request, token):
    project = get_object_or_404(Project, invite_token=token)
    if request.user.is_authenticated:
        project.members.add(request.user)
        return redirect('index')
    return redirect('register')