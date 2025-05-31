import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from customfit.design_wizard.models import Transaction
from customfit.patterns.models import IndividualPattern
from customfit.test_garment.factories import TestIndividualPatternFactory
from customfit.userauth.factories import StaffFactory

# Get an instance of a logger
logger = logging.getLogger(__name__)


class TransactionTests(TestCase):

    def setUp(self):
        self.pattern = TestIndividualPatternFactory()
        self.user = self.pattern.user

    def test_clean_free_transaction(self):
        t = Transaction()
        t.user = self.user
        t.pattern = self.pattern
        t.amount = 0
        t.approved = True
        t.why_free = Transaction.UNKNOWN_REASON
        t.full_clean()

    def test_clean_free_transaction_no_reason(self):
        t = Transaction()
        t.user = self.user
        t.pattern = self.pattern
        t.amount = 0
        t.approved = True
        t.why_free = None
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_clean_paypal_transaction(self):
        t = Transaction()
        t.user = self.user
        t.pattern = self.pattern
        t.amount = Decimal("19.99")
        t.approved = True
        t.paypal_signal = "success"
        t.paypal_transaction_id = "12345678901234567"
        t.full_clean()


class TransactionAdminSiteTest(TestCase):

    # Tests for the admin site (for the Transaction model)

    def setUp(self):
        super(TransactionAdminSiteTest, self).setUp()

        self.pattern = TestIndividualPatternFactory()
        self.user = self.pattern.user

        self.staff = StaffFactory()

        self.client.force_login(self.staff)
        self.add_url = reverse("admin:design_wizard_transaction_add")
        self.list_url = reverse("admin:design_wizard_transaction_changelist")

    def tearDown(self):
        self.pattern.delete()
        self.staff.delete()
        self.user.delete()

    def test_can_manually_approve_patterns_no_paypal(self):

        # sanity check: pattern is not yet approved? And does not show up in the standard manager?
        self.assertFalse(self.pattern.approved)
        self.assertFalse(
            IndividualPattern.approved_patterns.filter(id=self.pattern.id).exists()
        )

        # Try creating the Transaction through the admin site
        resp = self.client.get(self.add_url)
        self.assertContains(
            resp, "<title>Add transaction | Django site admin</title>", html=True
        )

        post_params = {
            "user": self.user.id,
            "pattern": self.pattern.id,
            "amount": "0.00",
            "approved": True,
            "why_free": "unknown_reason",
            "date_0": "2017-12-26",
            "date_1": "13:54:36",
        }

        resp = self.client.post(self.add_url, post_params)

        # Is the pattern now approved?
        self.assertTrue(self.pattern.approved)
        self.assertTrue(
            IndividualPattern.approved_patterns.filter(id=self.pattern.id).exists()
        )

    def test_can_manually_approve_patterns_paypal(self):

        # Sanity check: pattern is not yet approved? And does not show up in the
        # standard manager?
        self.assertFalse(self.pattern.approved)
        self.assertFalse(
            IndividualPattern.approved_patterns.filter(id=self.pattern.id).exists()
        )

        # Try creating the Transaction through the admin site
        resp = self.client.get(self.add_url)
        self.assertContains(
            resp, "<title>Add transaction | Django site admin</title>", html=True
        )

        post_params = {
            "user": self.user.id,
            "pattern": self.pattern.id,
            "amount": "9.99",
            "approved": True,
            # Note: Transaction does not actually link to PayPalIPN. Therefore we can
            # get away with making up these next values. If we ever change Transaction
            # to actually  link to the models in django_paypal, these tests will fail
            # and need to be updated.
            "paypal_signal": "success",
            "paypal_transaction_id": "12345678901234567",
            "paypal_payer_email": self.user.email,
            "date_0": "2017-12-26",
            "date_1": "13:54:36",
        }
        resp = self.client.post(self.add_url, post_params)
        #        self.assertRedirects(resp, self.list_url)

        # Is the pattern now approved?
        self.assertTrue(self.pattern.approved)
        self.assertTrue(
            IndividualPattern.approved_patterns.filter(id=self.pattern.id).exists()
        )
