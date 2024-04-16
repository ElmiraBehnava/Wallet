import requests
from django.utils import timezone
from rest_framework import serializers

from wallets.models import Transaction, Wallet
from wallets.services import deposit


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
        extra_kwargs = {"user": {"write_only": True}}

    def validate(self, data):
        user = data.get("user")
        if user and Wallet.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                {"user": "User already has a wallet."}
            )
        return data

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    def get_deposit_transactions(self, obj):
        return TransactionSerializer(
            obj.transactions.filter(type=Transaction.TypeChoices.DEPOSIT),
            many=True,
        ).data

    def get_withdrawal_transactions(self, obj):
        return TransactionSerializer(
            obj.transactions.filter(type=Transaction.TypeChoices.WITHDRAWAL),
            many=True,
        ).data


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    scheduled_for = serializers.DateTimeField()

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "The scheduled time must be in the future."
            )
        return value


class DepositTransactionSerializer(serializers.Serializer):
    amount = serializers.IntegerField()

    def validate(self, data):
        wallet_uuid = self.context.get("wallet_uuid")
        if not wallet_uuid:
            raise serializers.ValidationError(
                {"wallet_uuid": "This field must be provided."}
            )
        try:
            wallet = Wallet.objects.get(uuid=wallet_uuid)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError(
                {"wallet_uuid": "Wallet not found."}
            )
        data["wallet"] = wallet
        return data

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                {"amount": "Deposit amount must be greater than zero"}
            )
        return value

    def create(self, validated_data):
        wallet = validated_data.get("wallet")
        amount = validated_data.get("amount")
        try:
            result = deposit(wallet.uuid, amount)
            if result["status"] == 200:
                Transaction.objects.create(
                    wallet=wallet,
                    type=Transaction.TypeChoices.DEPOSIT,
                    amount=amount,
                    status=Transaction.StatusChoices.SUCCESS,
                )
            return result
        except requests.exceptions.RequestException as e:
            raise serializers.ValidationError(
                {"network": f"Network error occurred: {str(e)}"}
            )
