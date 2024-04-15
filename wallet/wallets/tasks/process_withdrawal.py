from celery import shared_task
from django.shortcuts import get_object_or_404
from wallets.models import Transaction, TransactionTask
from wallets.utils import request_third_party_transaction

from wallet.celery import app

__all__ = ("app",)


@shared_task(bind=True)
def process_withdrawal(self, **kwargs):

    transaction_id = kwargs.get("transaction_id")
    transaction = get_object_or_404(Transaction, id=transaction_id)
    wallet = transaction.wallet
    amount = transaction.amount

    try:
        response = request_third_party_transaction(
            wallet, amount, "withdrawal"
        )

        if response.status_code == 200:
            transaction.wallet.balance -= transaction.amount
            transaction.wallet.save()
            transaction.status = Transaction.StatusChoices.SUCCESS
        else:
            transaction.status = TransactionTask.StatusChoices.FAILED

        transaction.save()

        if transaction.status == Transaction.StatusChoices.SUCCESS:
            transaction.task.status = TransactionTask.StatusChoices.SUCCESS
        else:
            transaction.task.status = TransactionTask.StatusChoices.FAILED
        transaction.task.save()

    except Exception as e:
        transaction.task.status = TransactionTask.StatusChoices.FAILED
        transaction.task.save()
        raise e
