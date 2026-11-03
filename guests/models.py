from django.core.validators import MaxLengthValidator
from django.db import models


class Guest(models.Model):
    name = models.CharField("Nome", max_length=200)
    phone = models.CharField("Telefone", max_length=30, blank=True)
    notes = models.TextField("Observações", blank=True, max_length=2000, validators=[MaxLengthValidator(2000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "convidado"

    def __str__(self):
        return self.name
