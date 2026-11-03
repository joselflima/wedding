from django import forms
from .models import Guest


class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ["name", "phone", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Nome completo"}),
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel", "placeholder": "(11) 99999-9999"}),
            "notes": forms.Textarea(attrs={"rows": 5, "placeholder": "Algo que vocês gostariam de lembrar sobre esta pessoa"}),
        }
        help_texts = {"phone": "Opcional. Inclua o DDD.", "notes": "Opcional. Até 2.000 caracteres."}
