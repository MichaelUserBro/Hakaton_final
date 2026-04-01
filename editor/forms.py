from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UserRegisterForm(UserCreationForm):
    # Добавим поле email, чтобы форма была посолиднее
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email'] # Поля, которые увидит пользователь