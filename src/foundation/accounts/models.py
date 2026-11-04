from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        COUPLE = "couple", "Noivos"
        GUEST = "guest", "Convidados"
        GODPARENT = "godparent", "Padrinhos"

    role = models.CharField("perfil", max_length=12, choices=Role.choices, default=Role.GUEST)
    seat = models.PositiveSmallIntegerField("vaga de noivo", null=True, blank=True, unique=True)
    is_demo = models.BooleanField(default=False, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(
            # Explicit NOT NULL matters: SQL CHECK accepts UNKNOWN on NULL.
            condition=(Q(role="couple", seat__isnull=False, seat__in=[1, 2])
                       | Q(role__in=["guest", "godparent"], seat__isnull=True)),
            name="valid_role_and_couple_seat",
        )]

    @property
    def is_couple(self):
        return self.is_active and self.role == self.Role.COUPLE and self.seat in (1, 2)
