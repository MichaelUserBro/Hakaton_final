from django.db import models

class Document(models.Model):
    name = models.CharField(max_length=255, default="main.py")
    content = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True) # Исправлено здесь