import logging

import django.utils.timezone as timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from customfit.patterns.models import IndividualPattern

logger = logging.getLogger(__name__)

###########################################################################
#
# IMPORTANT: see doc/pricing.md before making changes to this model.
#
###########################################################################


class Transaction(models.Model):
    # Need to keep these for historical reasons
    PAYPAL_CHOICES = (
        ("success", "payment_was_successful"),
        ("flagged", "payment_was_flagged"),
    )

    # Mark why free patterns were free. Note that we need to keep these around for historical reasons
    FIRST_BETA_TESTER = (
        "first_beta_tester"  # User is a beta-tester (free patterns for life)
    )
    ALPHA_YARNSTORE = (
        "alpha_yarnstore"  # User alpha-tested the LYS program (free patterns for life)
    )
    STAFF_USER = "staff_user"  # User is staff
    MAKER = "maker"  # User has a maker subscription and have a quota of free patterns each month
    # They don't carry over from month to month, though.
    MAKER_PLUS = "maker_plus"  # User has a maker-plus subscription
    CREDIT = "credit_used"  # User used a credit (either from their bank, a credit code, or a credit-
    # valued coupon code, back when we had them)
    COUPON = "coupon_used"  # User used a dollar-valued coupon that covered the cost of the pattern
    # (back when we had dollar-valued coupon codes)
    LYS_SUBSCRIPTION_FREE_PATTERN = (
        "lys_sub_free"  # User is a LYS account, and they get a quota of free patterns
    )
    # each month. (They don't carry over from montht to month, though)
    UNKNOWN_REASON = "unknown_reason"  # We don't know. The Transaction was probably created before we started
    # tracking these reasons
    LYS_CUSTOMER_COPY = "lys_customer_copy"  # Pattern was copied to an individual account from an LYS account,
    # where it had already been paid for
    FRIENDS_AND_FAMILY = "friend_and_family"

    WHY_FREE_CHOICES = (
        (FIRST_BETA_TESTER, "first-beta-tester pattern"),
        (ALPHA_YARNSTORE, "LYS alpha-tester pattern"),
        (STAFF_USER, "staff-user pattern"),
        (MAKER_PLUS, "maker-plus pattern"),
        (MAKER, "maker pattern"),
        (CREDIT, "credit used"),
        (COUPON, "full-value coupon used"),
        (LYS_SUBSCRIPTION_FREE_PATTERN, "LYS-account free pattern"),
        (UNKNOWN_REASON, "unknown reason"),
        (LYS_CUSTOMER_COPY, "copied from LYS account"),
        (FRIENDS_AND_FAMILY, "friend or family"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    pattern = models.ForeignKey(
        IndividualPattern, related_name="transactions", on_delete=models.CASCADE
    )
    # Amount is set to 9999.99 for transactions created before the transaction
    # model existed (most of which were free; a handful may not have been).
    # The information is unrecoverable, so we make the default clearly bogus.
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    paypal_signal = models.CharField(max_length=7, choices=PAYPAL_CHOICES, blank=True)
    approved = models.BooleanField(default=False)
    paypal_transaction_id = models.CharField(max_length=17, blank=True)
    paypal_payer_email = models.EmailField(blank=True)

    why_free = models.CharField(
        max_length=30, choices=WHY_FREE_CHOICES, blank=True, null=True
    )

    def full_clean(self, exclude=None, validate_unique=True):
        # Yes, this logging is pretty excessive. But users can't get to patterns _they paid for_ if
        # validation fails, so we want to make sure we have the information we need to create Transactions
        # and diagnose the validation failure.
        logger.info(
            "About to full_clean Transaction for user %s (%s), pattern %s, amount %.2f, "
            "paypal signal %s, paypal transaction %s, and why_free of %s",
            self.user.username,
            self.user.id,
            self.pattern.id,
            self.amount,
            self.paypal_signal,
            self.paypal_transaction_id,
            self.why_free,
        )
        return super(Transaction, self).full_clean(exclude, validate_unique)

    def clean(self):
        # Yes, this logging is pretty excessive. But users can't get to patterns _they paid for_ if
        # validation fails, so we want to make sure we have the information we need to create Transactions
        # and diagnose the validation failure.
        logger.info(
            "About to clean Transaction for user %s (%s), pattern %s, amount %.2f, "
            "paypal signal %s, paypal transaction %s, and why_free of %s",
            self.user.username,
            self.user.id,
            self.pattern.id,
            self.amount,
            self.paypal_signal,
            self.paypal_transaction_id,
            self.why_free,
        )
        if self.amount == 0.00:
            if self.why_free is None:
                raise ValidationError("Free patterns must have a reason provided")
        return super(Transaction, self).clean()

    def save(self, *args, **kwargs):
        if (
            self.amount == 0.00
            or self.amount == 9999.99
            or self.paypal_signal == "success"
        ):
            # amount=9999.99 are patterns that were approved in beta
            self.approved = True
        else:
            # make absolutely sure this can't be tampered with
            self.approved = False

        # If there's an associated coupon code, subtract value and
        # mark as used if needed.
        pattern = self.pattern

        super(Transaction, self).save(*args, **kwargs)
