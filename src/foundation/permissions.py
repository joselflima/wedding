"""Shared access rules for the wedding domains."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class CoupleRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_couple:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
