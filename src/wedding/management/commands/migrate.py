"""Bridge existing auth.User databases before Django checks migration history."""
from django.core.management import call_command
from django.core.management.commands.migrate import Command as DjangoMigrate
from django.core.management.base import CommandError
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder


class Command(DjangoMigrate):
    def handle(self, *args, **options):
        connection = connections[options['database']]
        applied = MigrationRecorder(connection).applied_migrations()
        legacy = (
            ('admin', '0001_initial') in applied
            and ('wedding', '0001_initial') not in applied
            and 'auth_user' in connection.introspection.table_names()
        )
        if legacy:
            if options.get('plan') or options.get('check_unapplied'):
                raise CommandError('Banco legado: faça backup e execute migrate para adotar as contas antes de consultar o plano.')
            if options['database'] != 'default' or args or options.get('app_label') or options.get('fake') or options.get('fake_initial'):
                raise CommandError('A adoção requer migrate sem app, alvo ou --fake no banco default, após backup.')
            self.stdout.write('Adotando contas legadas antes de verificar o histórico de migrations.')
            call_command('adopt_legacy_users', stdout=self.stdout, stderr=self.stderr)
        return super().handle(*args, **options)
