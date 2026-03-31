from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('sync/', views.sync_code, name='sync_code'),
    path('run/', views.run_code, name='run_code'),
    path('ai-review/', views.ai_review, name='ai_review'),
]