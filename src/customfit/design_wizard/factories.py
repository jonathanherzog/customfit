import django.utils.timezone
import factory

from customfit.patterns.factories import IndividualPatternFactory

from .models import Transaction


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction
        django_get_or_create = ("pattern",)

    pattern = factory.SubFactory(IndividualPatternFactory)
    user = factory.SelfAttribute("pattern.user")
    amount = 0
    why_free = Transaction.UNKNOWN_REASON
    paypal_signal = "success"
    approved = True
    date = django.utils.timezone.now()
