from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'}))
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput(attrs={'placeholder': 'Повторите пароль'}))

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone']

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
        fields = ['full_name', 'phone', 'vk', 'telegram', 'max', 'birth_date', 'rank', 'height', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'photo': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        vk = cleaned_data.get('vk')
        telegram = cleaned_data.get('telegram')
        max_value = cleaned_data.get('max')

        if not (phone or vk or telegram or max_value):
            raise ValidationError('Укажите телефон или хотя бы одну социальную сеть (VK, Telegram, Max)')
        return cleaned_data
