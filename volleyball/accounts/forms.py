from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'})
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Повторите пароль'})
    )

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'full_name': forms.TextInput(attrs={'placeholder': 'Иванов Иван'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if not password1 or not password2:
            raise ValidationError('Пароль обязателен')

        if password1 != password2:
            raise ValidationError('Пароли не совпадают')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # Keep profile fields but make social fields optional; phone and others are optional in edit
        fields = ['full_name', 'phone', 'vk', 'telegram', 'max', 'birth_date', 'rank', 'height', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'photo': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def clean(self):
        # For profile edit we do not require social/contact fields — keep them optional
        cleaned_data = super().clean()
        return cleaned_data
