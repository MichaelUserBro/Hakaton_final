from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('run/', views.run_code, name='run_code'),
    path('sync/', views.sync_code, name='sync_code'),
    # Это главный маршрут для всех функций ИИ (включая исправление ошибок)
    # Твой универсальный маршрут для всех функций ИИ
    path('ai-action/', views.ai_action, name='ai_action'), 
    
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_user, name='logout'),
    path('create-project/', views.create_project, name='create_project'),
    path('join/<uuid:token>/', views.join_project, name='join_project'),
    path('login/', views.login_view, name='login'),
    path('delete-room/<int:room_id>/', views.delete_room, name='delete_room'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)