from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('run/', views.run_code, name='run_code'),
    path('ai-review/', views.ai_review, name='ai_review'),
    path('sync/', views.sync_code, name='sync_code'),
    path('register/', views.register_user, name='register'),
]