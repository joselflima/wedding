from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db import IntegrityError, transaction
from django.templatetags.static import static

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


class LoginTests(TestCase):
    def test_password_field_has_an_icon_toggle_with_password_hidden(self):
        response = self.client.get('/login/')
        self.assertContains(response, 'type="password"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, 'class="password-field"')
        self.assertContains(
            response,
            '<button type="button" class="password-toggle" data-password-toggle '
            'aria-controls="id_password" aria-label="Mostrar senha" hidden>'
            '<span class="password-eye" aria-hidden="true"></span></button>',
            html=True,
        )
        self.assertContains(response, f'src="{static("wedding/login.js")}"')


class ActivationTests(TestCase):
    def test_https_activation_with_csrf_and_status_update(self):
        from django.test import Client
        from django.contrib.auth.tokens import default_token_generator
        user = get_user_model().objects.create_user(username='invited', name='Convidado', is_active=False)
        url = f'/activate/{user.pk}/{default_token_generator.make_token(user)}/'
        client = Client(enforce_csrf_checks=True)
        response = client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotContains(response, 'data-password-toggle')
        response = client.post(url, {'new_password1': 'UniqueWedding!9827', 'new_password2': 'UniqueWedding!9827', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value}, secure=True, HTTP_REFERER='https://testserver' + url)
        self.assertRedirects(response, '/login/', fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(client.login(username=user.username, password='UniqueWedding!9827'))
        self.assertEqual(client.get(url).status_code, 404)
        couple = get_user_model().objects.create_user(username='couple', name='Noivo', role='couple', couple_slot=1)
        self.client.force_login(couple)
        response = self.client.get('/people/')
        self.assertContains(response, '>Ativa</span>')
        self.assertNotContains(response, '>Pendente</span>')

    def test_csrf_rejection_preserves_pending_account(self):
        from django.test import Client
        from django.contrib.auth.tokens import default_token_generator
        user = get_user_model().objects.create_user(username='pending', name='Convidado', is_active=False)
        url = f'/activate/{user.pk}/{default_token_generator.make_token(user)}/'
        response = Client(enforce_csrf_checks=True).post(url, {'new_password1': 'UniqueWedding!9827', 'new_password2': 'UniqueWedding!9827'})
        self.assertEqual(response.status_code, 403)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

class HomeTests(TestCase):
    def test_anonymous_home_shows_couple(self):
        response = self.client.get('/')
        self.assertContains(response, 'Maria Eduarda <span>e</span> José Lucas')
        self.assertNotContains(response, 'Bem-vindo(a),')

    def test_every_role_sees_full_name_greeting(self):
        for role, label in get_user_model().Role.choices:
            with self.subTest(role=role):
                user = get_user_model().objects.create_user(username=role, name='Nome Completo Teste', role=role, couple_slot=1 if role == 'couple' else None)
                self.client.force_login(user)
                response = self.client.get('/')
                self.assertContains(response, 'Bem-vindo(a), Nome Completo Teste!')
                self.assertNotContains(response, 'class="hero"')
                message = 'Ainda estamos construindo este sonho juntos, e é muito bom ter você aqui conosco! Estamos preparando novidades com carinho para compartilhar com você.'
                if role == 'couple':
                    self.assertNotContains(response, message)
                else:
                    self.assertContains(response, message)


class InstallationTests(TestCase):
    def test_public_home_offers_installation(self):
        response = self.client.get('/')
        self.assertContains(response, 'Adicionar à tela de início')
        self.assertContains(response, 'Compartilhar')
        self.assertContains(response, 'rel="manifest" href="/manifest.webmanifest"')
        self.assertContains(response, f'rel="apple-touch-icon" href="{static("wedding/icon-180.png")}"')
        self.assertIsNotNone(finders.find('wedding/icon-180.png'))

    def test_authenticated_home_offers_installation_for_each_role(self):
        for role, _ in get_user_model().Role.choices:
            with self.subTest(role=role):
                user = get_user_model().objects.create_user(
                    username=role, name='Teste', role=role,
                    couple_slot=1 if role == 'couple' else None,
                )
                self.client.force_login(user)
                self.assertContains(self.client.get('/'), 'Adicionar à tela de início')

    def test_manifest_describes_installation_from_home(self):
        response = self.client.get('/manifest.webmanifest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        manifest = response.json()
        self.assertEqual(manifest['name'], 'Maria Eduarda e José Lucas')
        self.assertEqual(manifest['short_name'], 'M&J')
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['display'], 'standalone')
        for size in (192, 512):
            filename = f'wedding/icon-{size}.png'
            self.assertIn({
                'src': static(filename), 'sizes': f'{size}x{size}', 'type': 'image/png',
            }, manifest['icons'])
            self.assertIsNotNone(finders.find(filename))
