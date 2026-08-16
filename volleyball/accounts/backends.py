from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate a user by email (case-insensitive) or username.

        Accepts either `email` in kwargs or the `username` argument. Returns
        the user if the password matches and the user is allowed to authenticate.
        """
        email = kwargs.get('email') or username
        if email is None or password is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
