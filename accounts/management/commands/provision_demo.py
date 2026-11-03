import os
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Cria um noivo de demonstração usando DEMO_USERNAME e DEMO_PASSWORD."

    def handle(self, *args, **options):
        username = os.environ.get("DEMO_USERNAME", "").strip()
        password = os.environ.get("DEMO_PASSWORD", "")
        if not username or not password:
            raise CommandError("Configure DEMO_USERNAME e DEMO_PASSWORD no ambiente.")
        existing = User.objects.filter(username=username).first()
        if existing:
            if existing.is_demo and existing.is_couple and not existing.is_staff and not existing.is_superuser:
                self.stdout.write("Usuário de demonstração já existe; nenhum dado foi alterado.")
                return
            raise CommandError("O login informado já pertence a outra conta ou a uma demonstração inativa.")
        user = User(username=username, first_name="Noivo de demonstração", role=User.Role.COUPLE, is_demo=True)
        try:
            User._meta.get_field("username").clean(username, user)
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        user.set_password(password)
        # Unique constraints arbitrate concurrent provisioning without a count-based race.
        for seat in (1, 2):
            if User.objects.filter(seat=seat).exists():
                continue
            try:
                with transaction.atomic():
                    user.seat = seat
                    user.save(force_insert=True)
                self.stdout.write(self.style.SUCCESS("Noivo de demonstração criado."))
                return
            except IntegrityError:
                if User.objects.filter(username=username).exists():
                    raise CommandError("O login foi ocupado durante o provisionamento; execute novamente.")
        raise CommandError("As duas vagas de noivos já estão ocupadas.")
