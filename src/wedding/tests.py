from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

class AccountsTests(TestCase):
    def test_two_slots(self):
        U = get_user_model()
        for slot in (1, 2):
            U.objects.create_user(username=str(slot), name='Noivo', role='couple', couple_slot=slot)
        with self.assertRaises(IntegrityError), transaction.atomic():
            U.objects.create_user(username='third', name='Outro', role='couple', couple_slot=1)

    def test_guest_denied(self):
        u = get_user_model().objects.create_user(username='guest', name='Guest')
        self.client.force_login(u)
        self.assertEqual(self.client.get('/people/').status_code, 403)

from unittest.mock import patch
from wedding.management.commands.migrate import Command

class LegacyMigrationTests(TestCase):
    def test_adopts_before_django_history_check(self):
        calls = []
        with patch('wedding.management.commands.migrate.MigrationRecorder') as recorder, patch('wedding.management.commands.migrate.call_command', side_effect=lambda *a, **kw: calls.append('adopt')), patch('wedding.management.commands.migrate.DjangoMigrate.handle', side_effect=lambda *a, **kw: calls.append('migrate')), patch('django.db.backends.sqlite3.introspection.DatabaseIntrospection.table_names', return_value=['auth_user']):
            recorder.return_value.applied_migrations.return_value = {('admin', '0001_initial')}
            Command().handle(database='default')
        self.assertEqual(calls, ['adopt', 'migrate'])

    def test_fresh_database_skips_adoption(self):
        with patch('wedding.management.commands.migrate.MigrationRecorder') as recorder, patch('wedding.management.commands.migrate.call_command') as adopt, patch('wedding.management.commands.migrate.DjangoMigrate.handle'):
            recorder.return_value.applied_migrations.return_value = set()
            Command().handle(database='default')
            adopt.assert_not_called()

class LogoutTests(TestCase):
    def test_logout_button_on_authenticated_pages(self):
        for role, slot, path in [('guest', None, '/'), ('couple', 1, '/people/')]:
            user = get_user_model().objects.create_user(username=role, name=role, role=role, couple_slot=slot)
            self.client.force_login(user)
            self.assertContains(self.client.get(path), 'action="/logout/"')

    def test_logout_ends_session_and_redirects_to_login(self):
        user = get_user_model().objects.create_user(username='logout', name='Teste')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.assertRedirects(self.client.post('/logout/'), '/login/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_csrf(self):
        from django.test import Client
        user = get_user_model().objects.create_user(username='csrf', name='Teste')
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.post('/logout/').status_code, 403)
