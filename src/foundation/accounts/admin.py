from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class WeddingUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Perfil", {"fields": ("role", "seat")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Perfil", {"fields": ("role", "seat")}),)
    list_display = ("username", "role", "seat", "is_active")

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission
