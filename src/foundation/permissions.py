"""Shared access rules for the wedding domains."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            allowed = user.is_active and user.role == self.required_role
            if self.required_role == "couple":
                allowed = allowed and user.is_couple
            if not allowed:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CoupleRequiredMixin(RoleRequiredMixin):
    required_role = "couple"
