from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'name', 'phone', 'role', 'couple_slot')

class ChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

@admin.register(User)
class AccountAdmin(UserAdmin):
    add_form = CreationForm
    form = ChangeForm
    list_display = ('username', 'name', 'role', 'is_active')
    search_fields = ('username', 'name')
    ordering = ('username',)
    fieldsets = ((None, {'fields': ('username','password','name','phone','role','couple_slot')}), ('Permissões', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}))
    add_fieldsets = ((None, {'fields': ('username','name','phone','role','couple_slot','password1','password2')}),)
