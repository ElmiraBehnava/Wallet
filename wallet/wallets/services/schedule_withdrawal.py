from datetime import datetime
from typing import Optional

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from wallets.models import Transaction, TransactionTask, Wallet
from wallets.tasks.process_withdrawal import process_withdrawal


def schedule_withdrawal(
    wallet: Wallet, amount: float, scheduled_for: Optional[datetime]
) -> Transaction:
    with transaction.atomic():
        pending_withdrawals_total = (
            Transaction.objects.filter(
                wallet=wallet,
                type=Transaction.TypeChoices.WITHDRAWAL,
                status=Transaction.StatusChoices.PENDING,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        if wallet.balance - pending_withdrawals_total < amount:
            raise ValueError(
                "Insufficient funds considering pending withdrawals"
            )

        new_transaction = Transaction.objects.create(
            wallet=wallet,
            type=Transaction.TypeChoices.WITHDRAWAL,
            scheduled_for=scheduled_for,
            amount=amount,
            status=Transaction.StatusChoices.PENDING,
        )

        result = process_withdrawal.apply_async(
            kwargs={"transaction_id": new_transaction.id},
            eta=scheduled_for.astimezone(timezone.utc),
        )

        TransactionTask.objects.create(
            transaction=new_transaction, task_id=result.id
        )

        return new_transaction
