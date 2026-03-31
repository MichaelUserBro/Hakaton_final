from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Document
from .services import PistonCodeRunner, AIService 

def index(request):
    doc, _ = Document.objects.get_or_create(id=1)
    return render(request, 'editor/index.html', {'doc': doc})

@csrf_exempt
def sync_code(request):
    doc, _ = Document.objects.get_or_create(id=1)
    if request.method == 'POST':
        doc.content = request.POST.get('content', '')
        doc.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'content': doc.content})

def run_code(request):
    try:
        doc = Document.objects.get(id=1)
        runner = PistonCodeRunner()
        output = runner.run(doc.content)
        return JsonResponse({'output': output})
    except Exception as e:
        return JsonResponse({'output': f"Ошибка: {str(e)}"})

@csrf_exempt
def ai_review(request):
    try:
        doc = Document.objects.get(id=1)
        reviewer = AIService()
        hints = reviewer.analyze_code(doc.content)
        return JsonResponse({'hints': hints})
    except Exception as e:
        return JsonResponse({'hints': [f"Ошибка AI: {str(e)}"]})