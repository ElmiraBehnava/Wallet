import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Wallet(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        db_index=True,
        help_text="User associated with the wallet.",
    )

    balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_balance_cache(self):
        cache_key = f"wallet_balance_{self.uuid}"
        cache.set(cache_key, self.balance, timeout=None)

    def get_balance_cache(self):
        cache_key = f"wallet_balance_{self.uuid}"
        balance = cache.get(cache_key)
        if balance is None:
            self.set_balance_cache()
            balance = self.balance
        return balance

    def clean(self):
        if (
            self.pk
            and Wallet.objects.filter(user=self.user)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("Each user can only have one wallet.")

    def __str__(self):
        return f"Wallet {self.uuid} - User: {self.user}"


class Transaction(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "P", ("PENDING")
        SUCCESS = "S", ("SUCCESS")
        FAILED = "F", ("FAILED")
        CANCELED = "C", ("CANCELED")

    class TypeChoices(models.TextChoices):
        DEPOSIT = "D", ("DEPOSIT")
        WITHDRAWAL = "W", ("WITHDRAWAL")

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    wallet = models.ForeignKey(
        Wallet,
        related_name="transactions",
        on_delete=models.CASCADE,
        null=True,
        db_index=True,
    )
    type = models.CharField(
        max_length=1, choices=TypeChoices.choices, db_index=True
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=1,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
    )
    amount = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class TransactionTask(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "P", ("PENDING")
        SUCCESS = "S", ("SUCCESS")
        FAILED = "F", ("FAILED")

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="task",
        db_index=True,
    )
    task_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=1,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
    )


@receiver(post_save, sender=Wallet)
def update_balance_cache(sender, instance, **kwargs):
    instance.set_balance_cache()
