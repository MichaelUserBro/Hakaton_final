from django.db import models
from django.contrib.auth.models import User
import uuid

class Document(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    name = models.CharField(max_length=255, default="main.py")
    content = models.TextField(blank=True, default="")
    version = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (v{self.version})"
    
from django.contrib.auth.models import User

class UserProfile(models.Model):
    
    # Связываем профиль с системным пользователем Django
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватарка")
    # Твое дополнительное поле
    project_name = models.CharField(max_length=255, verbose_name="Название проекта")

    def __str__(self):
        return f"{self.user.username} - {self.project_name}"
        
class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название комнаты")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(User, related_name='projects', verbose_name="Участники")
    created_at = models.DateTimeField(auto_now_add=True)
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.name