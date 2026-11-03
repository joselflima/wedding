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


class ProvisionTests(TestCase):
    def provision(self, username="demo", password="Sample-demo-Password-284!"):
        output = StringIO()
        with patch.dict(os.environ, {"DEMO_USERNAME": username, "DEMO_PASSWORD": password}):
            call_command("provision_demo", stdout=output)
        self.assertNotIn(password, output.getvalue())
        return output.getvalue()

    def test_created_once_without_changing_password_or_data(self):
        self.provision()
        user = User.objects.get(username="demo")
        self.assertTrue(user.is_couple)
        self.assertTrue(user.check_password("Sample-demo-Password-284!"))
        self.assertNotEqual(user.password, "Sample-demo-Password-284!")
        self.assertFalse(user.is_staff or user.is_superuser)
        user.first_name = "Nome alterado"
        user.save()
        original_password = user.password
        self.provision(password="Different-password-285!")
        user.refresh_from_db()
        self.assertEqual(user.password, original_password)
        self.assertEqual(user.first_name, "Nome alterado")
        self.assertEqual(User.objects.count(), 1)
        from guests.models import Guest
        self.assertEqual(Guest.objects.count(), 0)

    def test_uses_second_seat(self):
        User.objects.create_user("one", role="couple", seat=1)
        self.provision()
        self.assertEqual(User.objects.get(username="demo").seat, 2)

    def test_full_capacity_and_collisions(self):
        User.objects.create_user("one", role="couple", seat=1)
        User.objects.create_user("two", role="couple", seat=2)
        with self.assertRaisesMessage(CommandError, "duas vagas"):
            self.provision()
        with self.assertRaisesMessage(CommandError, "outra conta"):
            self.provision(username="one")

    def test_missing_invalid_and_weak_credentials(self):
        for username, password in [("", "abc"), ("demo", ""), ("bad name", "Sample-demo-Password-284!"), ("demo", "123")]:
            with self.subTest(username=username, password=password), self.assertRaises(CommandError):
                self.provision(username, password)
        self.assertEqual(User.objects.count(), 0)

    def test_inactive_demo_is_not_silently_reactivated(self):
        self.provision()
        User.objects.filter(username="demo").update(is_active=False)
        with self.assertRaises(CommandError):
            self.provision()


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
