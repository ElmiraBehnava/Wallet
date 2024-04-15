import threading
from typing import Dict

from django.db import transaction
from rest_framework import status

from wallets.models import Transaction, Wallet
from wallets.utils import request_third_party_transaction

lock = threading.Lock()


def deposit(wallet_uuid: str, amount: int) -> Dict[str, int]:
    wallet = Wallet.objects.get(uuid=wallet_uuid)

    response = request_third_party_transaction(wallet, amount, "deposit")
    third_party_data = response.json()
    third_party_status = third_party_data.get("status")

    with transaction.atomic():
        if third_party_status == status.HTTP_200_OK:
            wallet.balance += amount
            wallet.save()
            wallet.set_balance_cache()

            Transaction.objects.create(
                wallet=wallet,
                type=Transaction.TypeChoices.DEPOSIT,
                amount=amount,
                status=Transaction.StatusChoices.SUCCESS,
            )
            return {
                "message": "Deposit successful",
                "current_amount": wallet.balance,
                "status": status.HTTP_200_OK,
            }
        else:
            Transaction.objects.create(
                wallet=wallet,
                type=Transaction.TypeChoices.DEPOSIT,
                amount=amount,
                status=Transaction.StatusChoices.FAILED,
            )
            return {
                "message": "Failed to deposit",
                "status": third_party_status,
            }
