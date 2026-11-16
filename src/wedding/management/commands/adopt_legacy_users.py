"""Adopt the existing auth_user table before running normal migrations."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.contrib.auth.models import AbstractUser
from wedding.models import User

class Command(BaseCommand):
    help = 'Preserva auth_user e adapta seu esquema ao User customizado. Faça backup antes.'

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError("Este comando de adoção requer MySQL.")
        recorder = MigrationRecorder(connection)
        if ('wedding', '0001_initial') in recorder.applied_migrations():
            self.stdout.write('Modelo já adotado; execute migrate normalmente.')
            return
        tables = connection.introspection.table_names()
        if 'auth_user' not in tables:
            raise CommandError('Sem auth_user legado. Em banco novo, execute migrate.')
        if 'wedding_user' in tables:
            raise CommandError('Existem duas tabelas de usuários; necessária análise antes de continuar.')
        class LegacyUser(AbstractUser):
            class Meta:
                app_label = 'legacy_adoption'
                db_table = 'auth_user'
                managed = False
        with connection.cursor() as cursor:
            columns = {c.name for c in connection.introspection.get_table_description(cursor, 'auth_user')}
        # Operations are restartable: MySQL DDL is not transactional.
        with connection.schema_editor() as editor:
            for name in ('name', 'phone', 'role', 'couple_slot'):
                if name not in columns:
                    editor.add_field(User, User._meta.get_field(name))
        if 'first_name' in columns and 'last_name' in columns:
            with connection.cursor() as cursor:
                cursor.execute('SELECT id, username, first_name, last_name FROM auth_user')
                rows = cursor.fetchall()
            for pk, username, first, last in rows:
                User.objects.filter(pk=pk, name='').update(name=(' '.join(filter(None, [first, last])) or username))
        with connection.schema_editor() as editor:
            for name in ('email', 'first_name', 'last_name'):
                if name in columns:
                    editor.remove_field(LegacyUser, LegacyUser._meta.get_field(name))
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, 'auth_user')
        with connection.schema_editor() as editor:
            for constraint in User._meta.constraints:
                if constraint.name not in constraints:
                    editor.add_constraint(User, constraint)
        # Existing admin and M2M foreign keys keep referencing auth_user IDs.
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM django_content_type WHERE app_label = 'wedding' AND model = 'user'")
            if not cursor.fetchone():
                cursor.execute("UPDATE django_content_type SET app_label = 'wedding' WHERE app_label = 'auth' AND model = 'user'")
        recorder.record_applied('wedding', '0001_initial')
        self.stdout.write(self.style.SUCCESS('Contas preservadas. Execute migrate para concluir.'))
