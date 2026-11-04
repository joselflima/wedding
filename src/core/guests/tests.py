from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import Guest

User = get_user_model()


class GuestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.one = User.objects.create_user("one", password="Valid-password-89!", role="couple", seat=1)
        cls.two = User.objects.create_user("two", password="Valid-password-89!", role="couple", seat=2)
        cls.guest_user = User.objects.create_user("guest")
        cls.godparent = User.objects.create_user("godparent", role="godparent")
        cls.admin = User.objects.create_superuser("admin", password="Valid-password-89!")
        cls.guest = Guest.objects.create(name="Ana", phone="(11) 99999-0000", notes="Família")

    def routes(self):
        return [reverse("guests:list"), reverse("guests:create"),
                reverse("guests:update", args=[self.guest.pk]), reverse("guests:delete", args=[self.guest.pk])]

    def test_visitors_and_other_profiles_cannot_read_or_write(self):
        for user in (None, self.guest_user, self.godparent, self.admin):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for url in self.routes():
                for method in ("get", "post"):
                    with self.subTest(user=user, url=url, method=method):
                        response = getattr(self.client, method)(url, {"name": "Inválido"})
                        self.assertEqual(response.status_code, 403 if user else 302)
                        if user:
                            self.assertNotContains(response, 'href="/noivos/convidados/adicionar/"', status_code=403)
                        else:
                            self.assertTrue(response.url.startswith("/entrar/?next="))
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.name, "Ana")
        self.assertEqual(Guest.objects.count(), 1)

    def test_both_couple_accounts_share_all_operations(self):
        for user in (self.one, self.two):
            self.client.force_login(user)
            for url in self.routes():
                self.assertEqual(self.client.get(url).status_code, 200)
            self.assertContains(self.client.get(reverse("guests:list")), "Ana")
            self.client.post(reverse("guests:create"), {"name": "Novo"})
            added = Guest.objects.get(name="Novo")
            self.client.post(reverse("guests:update", args=[added.pk]), {"name": "Editado"})
            added.refresh_from_db()
            self.assertEqual(added.name, "Editado")
            self.client.post(reverse("guests:delete", args=[added.pk]))
            self.assertFalse(Guest.objects.filter(pk=added.pk).exists())

    def test_login_logout_inactive_account(self):
        response = self.client.post(reverse("login"), {"username": "one", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("login"), {"username": "one", "password": "Valid-password-89!"})
        self.assertRedirects(response, reverse("couple:home"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        User.objects.filter(pk=self.one.pk).update(is_active=False)
        self.assertFalse(self.client.login(username="one", password="Valid-password-89!"))

    def test_create_trim_duplicate_and_no_account_creation(self):
        self.client.force_login(self.one)
        response = self.client.post(reverse("guests:create"), {"name": "  Ana  ", "phone": "+55 (11) 99999-0000", "notes": "Teste"}, follow=True)
        self.assertContains(response, "Convidado salvo com sucesso.")
        self.assertEqual(Guest.objects.filter(name="Ana").count(), 2)
        self.assertEqual(User.objects.count(), 5)

    def test_invalid_fields_and_boundaries(self):
        self.client.force_login(self.one)
        for data in ({"name": "   "}, {"name": "a" * 201}, {"name": "Ok", "phone": "1" * 31}, {"name": "Ok", "notes": "a" * 2001}):
            response = self.client.post(reverse("guests:create"), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(Guest.objects.count(), 1)
        self.client.post(reverse("guests:create"), {"name": "a" * 200, "phone": "1" * 30, "notes": "a" * 2000})
        self.assertEqual(Guest.objects.count(), 2)

    def test_search_pagination_counts_and_order(self):
        Guest.objects.bulk_create([Guest(name=f"Pessoa {i:02d}") for i in range(30)])
        self.client.force_login(self.two)
        response = self.client.get(reverse("guests:list"))
        self.assertEqual(response.context["total"], 31)
        self.assertEqual(len(response.context["guests"]), 25)
        self.assertEqual(response.context["guests"][0].name, "Ana")
        self.assertEqual(len(self.client.get(reverse("guests:list"), {"page": 2}).context["guests"]), 6)
        for query in ("ana", "99999", "  Ana  "):
            response = self.client.get(reverse("guests:list"), {"q": query})
            self.assertEqual(response.context["paginator"].count, 1)
            self.assertEqual(response.context["total"], 31)
        response = self.client.get(reverse("guests:list"), {"q": "Pessoa"})
        self.assertContains(response, "q=Pessoa&amp;page=2")
        self.assertEqual(self.client.get(reverse("guests:list"), {"page": 999}).status_code, 404)

    def test_empty_and_no_results(self):
        self.client.force_login(self.one)
        response = self.client.get(reverse("guests:list"), {"q": "Ausente"})
        self.assertContains(response, "Nenhum convidado encontrado")
        Guest.objects.all().delete()
        self.assertContains(self.client.get(reverse("guests:list")), "Adicionar primeiro convidado")

    def test_delete_requires_post_and_unsupported_methods_rejected(self):
        self.client.force_login(self.one)
        url = reverse("guests:delete", args=[self.guest.pk])
        self.assertContains(self.client.get(url), "Excluir convidado?")
        self.assertTrue(Guest.objects.filter(pk=self.guest.pk).exists())
        self.assertEqual(self.client.delete(url).status_code, 405)
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Convidado excluído da lista.")
        self.assertFalse(Guest.objects.filter(pk=self.guest.pk).exists())
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_csrf_protects_every_write(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.one)
        for url in self.routes()[1:] + [reverse("logout")]:
            self.assertEqual(client.post(url, {"name": "Bypass"}).status_code, 403)
        client.logout()
        self.assertEqual(client.post(reverse("login"), {"username": "one", "password": "Valid-password-89!"}).status_code, 403)

    def test_html_is_escaped(self):
        self.client.force_login(self.one)
        Guest.objects.create(name='<script>alert("x")</script>')
        response = self.client.get(reverse("guests:list"))
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
