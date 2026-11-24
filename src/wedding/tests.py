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

    def test_login_page_hides_duplicate_header_login_button(self):
        response = self.client.get('/login/')
        self.assertNotContains(response, '>Entrar</a>')


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
        data = {'new_password1': 'UniqueWedding!9827', 'new_password2': 'UniqueWedding!9827', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value}
        response = client.post(url, data, secure=True, HTTP_REFERER='https://testserver' + url, follow=True)
        self.assertEqual(response.redirect_chain, [('/login/', 302)])
        self.assertContains(response, 'Bem-vindo ao nosso casamento')
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        response = client.get(url, secure=True)
        self.assertContains(response, 'Este link não está mais disponível', status_code=400)
        self.assertContains(response, '<a href="/login/">Voltar para o login</a>', status_code=400, html=True)
        self.assertNotContains(response, 'name="new_password1"', status_code=400)
        retry = {**data, 'new_password1': 'OtherWedding!54321', 'new_password2': 'OtherWedding!54321'}
        response = client.post(url, retry, secure=True, HTTP_REFERER='https://testserver' + url)
        self.assertContains(response, 'Este link não está mais disponível', status_code=400)
        self.assertTrue(client.login(username=user.username, password='UniqueWedding!9827'))
        couple = get_user_model().objects.create_user(username='couple', name='Noivo', role='couple', couple_slot=1)
        self.client.force_login(couple)
        response = self.client.get('/people/')
        self.assertContains(response, '>Ativa</span>')
        self.assertNotContains(response, '>Pendente</span>')

    def test_invalid_or_expired_invitation_offers_login_without_activation(self):
        from datetime import datetime, timedelta
        from django.contrib.auth.tokens import default_token_generator
        user = get_user_model().objects.create_user(username='expired', name='Convidado', is_active=False)
        with patch.object(default_token_generator, '_now', return_value=datetime.now() - timedelta(days=4)):
            token = default_token_generator.make_token(user)
        for url in (f'/activate/{user.pk}/{token}/', f'/activate/{user.pk}/invalid/', f'/activate/{user.pk + 1}/{token}/'):
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                self.assertContains(response, 'Este link não está mais disponível', status_code=400)
                self.assertContains(response, '<a href="/login/">Voltar para o login</a>', status_code=400, html=True)
                self.assertNotContains(response, 'name="new_password1"', status_code=400)
                self.assertEqual(response['Cache-Control'], 'no-store')
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_csrf_rejection_preserves_pending_account(self):
        from django.test import Client
        from django.contrib.auth.tokens import default_token_generator
        user = get_user_model().objects.create_user(username='pending', name='Convidado', is_active=False)
        url = f'/activate/{user.pk}/{default_token_generator.make_token(user)}/'
        response = Client(enforce_csrf_checks=True).post(url, {'new_password1': 'UniqueWedding!9827', 'new_password2': 'UniqueWedding!9827'})
        self.assertEqual(response.status_code, 403)
        user.refresh_from_db()
        self.assertFalse(user.is_active)


class PasswordResetTests(TestCase):
    request_url = '/password-reset/'
    panel_url = '/people/password-resets/'
    old_password = 'OriginalWedding!5471'
    new_password = 'UniqueWedding!9827'

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        User = get_user_model()
        self.guest = User.objects.create_user(username='guest', name='Convidado Teste', password=self.old_password)
        self.couple = User.objects.create_user(username='couple', name='Noivo', role='couple', couple_slot=1)
        self.issue_url = f'{self.panel_url}{self.guest.pk}/issue/'

    def submit_request(self, username='guest'):
        return self.client.post(self.request_url, {'username': username}, follow=True)

    def issue_link(self):
        self.client.force_login(self.couple)
        response = self.client.post(self.issue_url)
        self.assertContains(response, 'Copie e compartilhe')
        self.assertIn('no-store', response['Cache-Control'])
        self.client.logout()
        return response.context['reset_link']

    def confirm(self, url):
        return self.client.post(url, {'new_password1': self.new_password, 'new_password2': self.new_password})

    def test_login_links_to_recovery(self):
        self.assertContains(self.client.get('/login/'), f'href="{self.request_url}"')

    def test_missing_inactive_and_privileged_accounts_have_same_message(self):
        User = get_user_model()
        User.objects.create_user(username='pending', name='Pendente', is_active=False)
        User.objects.create_superuser(username='admin', password=self.old_password, name='Admin')
        for username in ('missing', 'pending', 'couple', 'admin'):
            with self.subTest(username=username):
                self.assertContains(self.submit_request(username), 'Usuário não encontrado ou ainda não ativado.')
        self.client.force_login(self.couple)
        self.assertContains(self.client.get(self.panel_url), 'Nenhum pedido')

    def test_requests_are_deduplicated_and_do_not_change_the_password(self):
        for _ in range(2):
            self.assertContains(self.submit_request(), 'Seu pedido foi enviado aos noivos.')
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.is_active)
        self.assertTrue(self.guest.check_password(self.old_password))
        self.client.force_login(self.couple)
        self.assertContains(self.client.get(self.panel_url), 'Convidado Teste', count=1)

    def test_repeated_attempts_are_limited(self):
        for _ in range(5):
            self.assertEqual(self.submit_request('missing').status_code, 200)
        self.assertContains(self.submit_request(), 'Muitas tentativas', status_code=429)

    def test_only_couple_may_issue_for_an_existing_request_via_post(self):
        self.assertEqual(self.client.get(self.panel_url).status_code, 302)
        self.assertEqual(self.client.post(self.issue_url).status_code, 302)
        self.client.force_login(self.couple)
        self.assertEqual(self.client.post(self.issue_url).status_code, 404)
        self.client.logout()
        self.submit_request()
        self.client.force_login(self.guest)
        self.assertEqual(self.client.get(self.panel_url).status_code, 403)
        self.assertEqual(self.client.post(self.issue_url).status_code, 403)
        self.client.force_login(self.couple)
        self.assertEqual(self.client.get(self.issue_url).status_code, 405)
        self.assertEqual(self.client.post(f'{self.panel_url}{self.couple.pk}/issue/').status_code, 404)
        self.guest.is_active = False
        self.guest.save(update_fields=['is_active'])
        self.assertEqual(self.client.post(self.issue_url).status_code, 404)

    def test_link_requires_session_and_is_consumed_after_password_change(self):
        from django.test import Client
        self.submit_request()
        link = self.issue_link()
        self.assertTrue(self.client.login(username='guest', password=self.old_password))
        self.client.logout()
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        self.assertIn('no-store', response['Cache-Control'])
        confirm_url = response.url
        self.assertEqual(Client().get(confirm_url).status_code, 400)
        self.assertContains(self.client.get(confirm_url), 'Redefinir senha')
        self.assertContains(self.client.post(confirm_url, {'new_password1': '123', 'new_password2': '123'}), 'Redefinir senha')
        self.assertRedirects(self.confirm(confirm_url), '/login/')
        self.assertEqual(self.client.get(link).status_code, 400)
        self.assertEqual(self.confirm(confirm_url).status_code, 400)
        self.assertFalse(self.client.login(username='guest', password=self.old_password))
        self.assertTrue(self.client.login(username='guest', password=self.new_password))
        self.client.force_login(self.couple)
        self.assertContains(self.client.get(self.panel_url), 'Nenhum pedido')

    def test_new_link_invalidates_previous_link_and_expires(self):
        from datetime import timedelta
        from django.utils import timezone
        self.submit_request()
        old_link = self.issue_link()
        new_link = self.issue_link()
        self.assertNotEqual(old_link, new_link)
        self.assertEqual(self.client.get(old_link).status_code, 400)
        response = self.client.get(new_link)
        self.assertEqual(response.status_code, 302)
        future = timezone.now() + timedelta(hours=25)
        with patch('wedding.password_reset.timezone.now', return_value=future):
            self.assertEqual(self.client.get(new_link).status_code, 400)
            self.assertEqual(self.confirm(response.url).status_code, 400)

    def test_account_must_still_be_active_when_submitting_new_password(self):
        self.submit_request()
        link = self.issue_link()
        confirm_url = self.client.get(link).url
        self.guest.is_active = False
        self.guest.save(update_fields=['is_active'])
        self.assertEqual(self.confirm(confirm_url).status_code, 400)
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.check_password(self.old_password))

    def test_https_password_reset_requires_csrf(self):
        from django.test import Client
        self.submit_request()
        link = self.issue_link()
        client = Client(enforce_csrf_checks=True)
        confirm_url = client.get(link, secure=True).url
        response = client.get(confirm_url, secure=True)
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        data = {'new_password1': self.new_password, 'new_password2': self.new_password}
        referer = f'https://testserver{confirm_url}'
        self.assertEqual(client.post(confirm_url, data, secure=True, HTTP_REFERER=referer).status_code, 403)
        data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        response = client.post(confirm_url, data, secure=True, HTTP_REFERER=referer)
        self.assertRedirects(response, '/login/', fetch_redirect_response=False)

    def test_issued_reset_link_includes_copy_control(self):
        self.submit_request()
        self.client.force_login(self.couple)
        response = self.client.post(self.issue_url)
        self.assertContains(response, 'id="reset-link"')
        self.assertContains(response, 'data-copy-target="#reset-link"')
        self.assertContains(response, f'src="{static("wedding/copy.js")}"')


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

    def test_couple_home_shows_dashboard_metrics_and_shortcuts(self):
        from wedding.models import PasswordResetRequest
        User = get_user_model()
        couple = User.objects.create_user(username='couple', name='Noivo Teste', role='couple', couple_slot=1)
        guest_active = User.objects.create_user(username='guest1', name='Convidado Um', role='guest', is_active=True)
        User.objects.create_user(username='guest2', name='Convidado Dois', role='guest', is_active=True)
        User.objects.create_user(username='sponsor1', name='Padrinho Pendente', role='sponsor', is_active=False)
        User.objects.create_user(username='staff', name='Equipe', role='guest', is_staff=True, is_active=True)
        PasswordResetRequest.objects.create(user=guest_active)

        self.client.force_login(couple)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['dashboard'],
            {
                'total_participants': 3,
                'active_participants': 2,
                'pending_participants': 1,
                'pending_password_resets': 1,
            },
        )
        self.assertContains(response, 'data-couple-dashboard')
        self.assertContains(response, 'href="/people/"')
        self.assertContains(response, 'href="/people/password-resets/"')

    def test_non_couple_and_anonymous_do_not_see_dashboard(self):
        guest = get_user_model().objects.create_user(username='guest', name='Convidado', role='guest')
        for client_user in (None, guest):
            with self.subTest(user=client_user):
                if client_user:
                    self.client.force_login(client_user)
                else:
                    self.client.logout()
                response = self.client.get('/')
                self.assertNotIn('dashboard', response.context)
                self.assertNotContains(response, 'data-couple-dashboard')

    def test_anonymous_home_hides_duplicate_header_login_and_skip_link(self):
        response = self.client.get('/')
        self.assertNotContains(response, '>Entrar</a>')
        self.assertNotContains(response, 'Pular para o conteúdo')
        self.assertContains(response, 'Entrar no espaço')
        self.assertContains(response, '<meta name="theme-color" content="#f3e7d3">')
        self.assertContains(response, 'viewport-fit=cover')


class PeopleManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.couple = User.objects.create_user(username='couple', name='Noivo', role='couple', couple_slot=1)
        self.active_guest = User.objects.create_user(
            username='ana', name='Ana Ativa', role='guest', is_active=True,
        )
        self.pending_sponsor = User.objects.create_user(
            username='bruno', name='Bruno Pendente', role='sponsor', is_active=False,
        )
        self.client.force_login(self.couple)

    def test_status_filter_and_combined_filters(self):
        active_response = self.client.get('/people/', {'status': 'active'})
        self.assertContains(active_response, 'Ana Ativa')
        self.assertNotContains(active_response, 'Bruno Pendente')

        pending_response = self.client.get('/people/', {'status': 'pending'})
        self.assertContains(pending_response, 'Bruno Pendente')
        self.assertNotContains(pending_response, 'Ana Ativa')

        invalid_response = self.client.get('/people/', {'status': 'invalid'})
        self.assertContains(invalid_response, 'Ana Ativa')
        self.assertContains(invalid_response, 'Bruno Pendente')

        combined_response = self.client.get('/people/', {'q': 'ana', 'status': 'active', 'role': 'guest'})
        self.assertContains(combined_response, 'Ana Ativa')
        self.assertNotContains(combined_response, 'Bruno Pendente')

        empty_response = self.client.get('/people/', {'q': 'ana', 'status': 'pending'})
        self.assertContains(empty_response, 'Nenhum participante encontrado.')
        self.assertNotContains(empty_response, 'Ana Ativa')

    def test_activation_link_includes_copy_control(self):
        response = self.client.post(f'/people/{self.pending_sponsor.pk}/', {'action': 'link'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="activation-link"')
        self.assertContains(response, 'data-copy-target="#activation-link"')
        self.assertContains(response, f'src="{static("wedding/copy.js")}"')

    def test_couple_navigation_marks_current_page_and_links_resets(self):
        response = self.client.get('/people/')
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, 'href="/people/password-resets/"')

    def test_people_list_paginates_ten_per_page_and_preserves_filters(self):
        User = get_user_model()
        for i in range(1, 12):
            User.objects.create_user(
                username=f'convidado{i:02d}',
                name=f'Convidado {i:02d}',
                role='guest',
                is_active=True,
            )

        page1 = self.client.get('/people/')
        self.assertEqual(len(page1.context['rows']), 10)
        self.assertEqual(page1.context['page_obj'].number, 1)
        self.assertEqual(page1.context['page_obj'].paginator.num_pages, 2)
        self.assertContains(page1, 'Página 1 de 2')
        self.assertContains(page1, 'page=2')

        page2 = self.client.get('/people/', {'page': 2})
        self.assertEqual(len(page2.context['rows']), 3)
        self.assertEqual(page2.context['page_obj'].number, 2)
        self.assertContains(page2, 'Página 2 de 2')
        self.assertContains(page2, 'page=1')

        filtered = self.client.get('/people/', {'status': 'active', 'page': 1})
        self.assertEqual(len(filtered.context['rows']), 10)
        self.assertContains(filtered, 'status=active&amp;page=2')


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
                response = self.client.get('/')
                if role == 'couple':
                    self.assertNotContains(response, 'Adicionar à tela de início')
                else:
                    self.assertContains(response, 'Adicionar à tela de início')

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
