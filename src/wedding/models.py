from django.contrib.auth.models import AbstractUser
from django.db import models

from django.contrib.auth.models import UserManager as BaseUserManager

class UserManager(BaseUserManager):
    def _create_user_object(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError('Informe o usuário.')
        user = self.model(username=self.model.normalize_username(username), **extra_fields)
        user.set_password(password)
        return user

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    objects = UserManager()
    class Role(models.TextChoices):
        COUPLE = 'couple', 'Noivo(a)'
        GUEST = 'guest', 'Convidado(a)'
        SPONSOR = 'sponsor', 'Padrinho/Madrinha'
        MOTHER = 'mother', 'Mãe'
        FATHER = 'father', 'Pai'
        PAGE = 'page', 'Pajem'
        MAID = 'maid', 'Dama de Honra'
    email = None
    first_name = None
    last_name = None
    name = models.CharField('nome completo', max_length=200)
    phone = models.CharField('telefone', max_length=32, blank=True)
    role = models.CharField('tipo', max_length=16, choices=Role.choices, default=Role.GUEST)
    couple_slot = models.PositiveSmallIntegerField('vaga de noivo', null=True, blank=True, unique=True)
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = "auth_user"
        constraints = [models.CheckConstraint(condition=(models.Q(role='couple', couple_slot__in=[1, 2], couple_slot__isnull=False) | (~models.Q(role='couple') & models.Q(couple_slot__isnull=True))), name='valid_couple_slot'), models.CheckConstraint(condition=models.Q(role__in=['couple','guest','sponsor','mother','father','page','maid']), name='valid_role')]

    def get_full_name(self):
        return self.name
