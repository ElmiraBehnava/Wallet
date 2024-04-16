from typing import Any

from celery import current_app
from celery.exceptions import WorkerLostError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from wallets.models import Transaction, TransactionTask, Wallet
from wallets.serializers import (
    DepositTransactionSerializer,
    WalletSerializer,
    WithdrawalSerializer,
)
from wallets.services import schedule_withdrawal


class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"


class CreateDepositView(CreateAPIView):
    serializer_class = DepositTransactionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["wallet_uuid"] = self.kwargs.get("wallet_uuid")
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            result = serializer.save()
            return Response(result, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response(
                {"errors": e.detail}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"errors": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_create(self, serializer):
        return serializer.save()


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
