from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('run/', views.run_code, name='run_code'),
    path('ai-review/', views.ai_review, name='ai_review'),
    path('sync/', views.sync_code, name='sync_code'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_user, name='logout'),
    path('create-project/', views.create_project, name='create_project'),
    path('ai-review/', views.ai_review, name='ai_review'), 
    # Добавляем маршрут для логики конфликтов из Этапа 2
    path('resolve-conflict/', views.resolve_ai_conflict, name='resolve_ai_conflict'),
    path('analyze/', views.ai_review, name='ai_review'),
]