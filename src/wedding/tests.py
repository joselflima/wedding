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
