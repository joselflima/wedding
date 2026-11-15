import os
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase

User = get_user_model()


class SeatTests(TestCase):
    def test_two_seats_and_other_profiles(self):
        for seat in (1, 2):
            User.objects.create_user(f"couple{seat}", role="couple", seat=seat)
        User.objects.create_user("guest", role="guest")
        User.objects.create_user("godparent", role="godparent")
        self.assertEqual(User.objects.filter(role="couple").count(), 2)

    def test_database_rejects_invalid_combinations(self):
        cases = [("couple", None), ("couple", 0), ("couple", 3), ("guest", 1),
                 ("godparent", 2), ("invalid", None), ("invalid", 1)]
        for role, seat in cases:
            with self.subTest(role=role, seat=seat), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create(username="invalid", role=role, seat=seat)

    def test_duplicate_and_third_couple_rejected_even_if_inactive(self):
        User.objects.create_user("one", role="couple", seat=1, is_active=False)
        User.objects.create_user("two", role="couple", seat=2)
        for seat in (1, 2, 3, None):
            with self.subTest(seat=seat), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create_user("third", role="couple", seat=seat)

    def test_update_cannot_bypass_constraint(self):
        guest = User.objects.create_user("guest")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=guest.pk).update(role="couple")


class ConcurrentSeatTests(TransactionTestCase):
    def test_last_seat_has_exactly_one_winner(self):
        if connection.vendor != "mysql":
            self.skipTest("Acceptance test requires MySQL")
        User.objects.create_user("first", role="couple", seat=1)
        barrier = Barrier(2)

        def claim(username):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    User.objects.create_user(username, role="couple", seat=2)
                return "created"
            except IntegrityError:
                return "rejected"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, ("second-a", "second-b")))
        self.assertCountEqual(results, ["created", "rejected"])
        self.assertEqual(User.objects.filter(role="couple").count(), 2)


class ProfileEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User.objects.create_user("couple", password="Valid-password-89!", role="couple", seat=1),
            User.objects.create_user("guest", password="Valid-password-89!", role="guest"),
            User.objects.create_user("godparent", password="Valid-password-89!", role="godparent"),
        ]
        cls.homes = ["/couple/", "/guests/", "/godparents/"]

    def test_public_entry_is_shared_and_neutral(self):
        for url in ("/", "/login/"):
            response = self.client.get(url)
            self.assertContains(response, "Acesse seu espaço")
            self.assertContains(response, "Uma história para celebrar juntos.")
            self.assertContains(response, "Maria Eduarda &amp; José Lucas")
            self.assertNotContains(response, "Vamos planejar?")
            self.assertNotContains(response, "Um espaço privado para os noivos")

    def test_login_and_authenticated_entry_always_use_profile(self):
        for user, home in zip(self.users, self.homes):
            for next_url in ("", "/couple/guests/", "/godparents/", "https://example.com/"):
                for entry in ("/", "/login/"):
                    with self.subTest(user=user.username, next=next_url, entry=entry):
                        self.client.logout()
                        response = self.client.post(entry, {"username": user.username,
                            "password": "Valid-password-89!", "next": next_url})
                        self.assertRedirects(response, home)
                        self.assertRedirects(self.client.get(entry, {"next": next_url}), home)

    def test_homes_require_matching_profile_including_superusers(self):
        for home in self.homes:
            self.assertRedirects(self.client.get(home), "/login/?next=" + home)
        for user, own_home in zip(self.users, self.homes):
            user.is_staff = user.is_superuser = True
            user.save()
            self.client.force_login(user)
            for home in self.homes:
                response = self.client.get(home)
                if home == own_home:
                    self.assertEqual(response.status_code, 200)
                    if user.is_couple:
                        self.assertContains(response, 'href="/couple/guests/"')
                    else:
                        self.assertNotContains(response, 'href="/couple/guests/"')
                else:
                    self.assertEqual(response.status_code, 403)
                    self.assertContains(response, "Voltar ao meu espaço", status_code=403)
            self.client.logout()

    def test_inactive_accounts_invalid_credentials_and_logout(self):
        for user in self.users:
            user.is_active = False
            user.save()
            response = self.client.post("/login/", {"username": user.username, "password": "Valid-password-89!"})
            self.assertContains(response, "Não foi possível entrar")
            self.assertNotIn("_auth_user_id", self.client.session)
            self.client.force_login(user)
            self.assertEqual(self.client.get("/").status_code, 200)
            self.client.logout()
        user = self.users[0]
        user.is_active = True
        user.save()
        self.client.force_login(user)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)


class AdminTests(TestCase):
    def test_superuser_can_manage_accounts(self):
        user = User.objects.create_superuser("administrator", password="Valid-password-89!")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 200)

    def test_login_session_persists_and_logout_clears_it(self):
        user = User.objects.create_user("visitor", password="Valid-password-89!")
        self.client.post("/login/", {"username": "visitor", "password": "Valid-password-89!"})
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertEqual(self.client.get("/guests/").wsgi_request.user.pk, user.pk)
        self.client.post("/logout/")
        self.assertNotIn("_auth_user_id", self.client.session)
