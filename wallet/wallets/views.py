from typing import Any

import requests
from celery import current_app
from celery.exceptions import WorkerLostError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from wallets.models import Transaction, TransactionTask, Wallet
from wallets.serializers import WalletSerializer, WithdrawalSerializer
from wallets.services import deposit, schedule_withdrawal


class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer

    def post(self, request: Request, *args, **kwargs):
        user_id = request.data.get("user", None)

        if user_id is not None:
            try:
                existing_wallet = Wallet.objects.get(user_id=user_id)
                serializer = self.get_serializer(existing_wallet)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Wallet.DoesNotExist:
                pass

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"


class CreateDepositView(APIView):
    def post(self, request, *args, **kwargs):
        wallet_uuid = kwargs.get("wallet_uuid")
        amount = int(request.data.get("amount", 0))
        if amount <= 0:
            return Response(
                {"message": "Deposit amount must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Wallet.objects.get(uuid=wallet_uuid)
        except Wallet.DoesNotExist:
            return Response(
                {"message": "Wallet not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = deposit(wallet_uuid, amount)
            return Response(
                {
                    "message": result["message"],
                    "current_amount": result["current_amount"],
                },
                status=result["status"],
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {"message": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class ScheduleWithdrawView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = WithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            wallet_uuid = kwargs.get("wallet_uuid")
            wallet = get_object_or_404(Wallet, uuid=wallet_uuid)
            try:
                schedule_withdrawal(wallet, **serializer.validated_data)
                return Response(
                    {"message": "Withdrawal scheduled successfully"}
                )
            except ValueError as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )


class WithdrawalCancellationView(APIView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        transaction_uuid = request.data.get("transaction_uuid")

        if not transaction_uuid:
            return Response(
                {"error": "Transaction ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            transaction_to_cancel = (
                Transaction.objects.select_for_update()
                .filter(uuid=transaction_uuid)
                .first()
            )

            if not transaction_to_cancel:
                return Response(
                    {"error": "Transaction not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                transaction_to_cancel.status
                != Transaction.StatusChoices.PENDING
            ):
                return Response(
                    {"error": "Only pending transactions can be cancelled"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if transaction_to_cancel.task:
                try:
                    current_app.control.revoke(
                        transaction_to_cancel.task.task_id, terminate=True
                    )
                except WorkerLostError:
                    pass

                transaction_to_cancel.task.status = (
                    TransactionTask.StatusChoices.FAILED
                )
                transaction_to_cancel.task.save()

            transaction_to_cancel.status = Transaction.StatusChoices.CANCELED
            transaction_to_cancel.save()

        return Response({"message": "Withdrawal successfully cancelled"})
