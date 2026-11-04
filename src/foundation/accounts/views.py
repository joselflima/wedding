from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.urls import reverse


def profile_home(user):
    if not user.is_active:
        raise PermissionDenied
    destinations = {"couple": "couple:home", "guest": "guest_home", "godparent": "godparents:home"}
    if user.role not in destinations or (user.role == "couple" and not user.is_couple):
        raise PermissionDenied
    return reverse(destinations[user.role])


class WeddingLoginView(LoginView):
    redirect_authenticated_user = True

    def get_success_url(self):
        return profile_home(self.request.user)
