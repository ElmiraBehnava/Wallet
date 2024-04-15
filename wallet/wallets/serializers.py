from django.utils import timezone
from rest_framework import serializers
from wallets.models import Transaction, Wallet


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )

    class Meta:
        model = Transaction
        fields = (
            "uuid",
            "type",
            "transaction_type_display",
            "scheduled_for",
            "status",
            "created_at",
            "amount",
        )
        read_only_fields = (
            "uuid",
            "status",
            "created_at",
            "transaction_type_display",
        )


class WalletSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    deposit_transactions = serializers.SerializerMethodField()
    withdrawal_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = (
            "uuid",
            "balance",
            "user",
            "user_name",
            "deposit_transactions",
            "withdrawal_transactions",
        )
        read_only_fields = (
            "uuid",
            "balance",
            "user_name",
            "deposit_transactions",
            "withdrawal_transactions",
        )

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    def get_deposit_transactions(self, obj):
        deposit_transactions = obj.transactions.filter(
            type=Transaction.TypeChoices.DEPOSIT
        )
        serializer = TransactionSerializer(
            deposit_transactions.prefetch_related("wallet"), many=True
        )
        return serializer.data

    def get_withdrawal_transactions(self, obj):
        withdrawal_transactions = obj.transactions.filter(
            type=Transaction.TypeChoices.WITHDRAWAL
        )
        serializer = TransactionSerializer(
            withdrawal_transactions.prefetch_related("wallet"), many=True
        )
        return serializer.data


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    scheduled_for = serializers.DateTimeField()

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "The scheduled time must be in the future."
            )
        return value
