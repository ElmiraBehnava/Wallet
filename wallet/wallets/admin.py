from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from wallets.models import Transaction, TransactionTask, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("uuid_short", "user_link", "balance_display", "created_at")
    search_fields = ("uuid", "user__username")
    list_filter = ("created_at",)
    readonly_fields = ("uuid", "created_at")

    def uuid_short(self, obj):
        return str(obj.uuid)[:8]

    uuid_short.short_description = "UUID"

    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.pk])
        return format_html("<a href='{}'>{}</a>", url, obj.user.username)

    user_link.short_description = "User"

    def balance_display(self, obj):
        return f"{obj.balance:,}"

    balance_display.short_description = "Balance"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "uuid_short",
        "wallet_link",
        "type",
        "status",
        "amount_formatted",
        "scheduled_for",
        "created_at",
    )
    search_fields = (
        "uuid",
        "wallet__uuid",
        "wallet__user__username",
        "amount",
    )
    list_filter = ("type", "status", "scheduled_for", "created_at")
    readonly_fields = ("uuid", "created_at")

    def uuid_short(self, obj):
        return str(obj.uuid)[:8]

    uuid_short.short_description = "UUID"

    def wallet_link(self, obj):
        url = reverse("admin:wallets_wallet_change", args=[obj.wallet.pk])
        return format_html("<a href='{}'>Wallet {}</a>", url, obj.wallet.uuid)

    wallet_link.short_description = "Wallet"

    def amount_formatted(self, obj):
        return f"{obj.amount:,}"

    amount_formatted.short_description = "Amount"


@admin.register(TransactionTask)
class TransactionTaskAdmin(admin.ModelAdmin):
    list_display = ("get_transaction_uuid", "task_id", "status")
    search_fields = ("transaction__uuid", "task_id")
    list_filter = ("status",)
    readonly_fields = ("task_id",)

    def get_transaction_uuid(self, obj):
        return str(obj.transaction.uuid)[:8]

    get_transaction_uuid.admin_order_field = "transaction"
    get_transaction_uuid.short_description = "Transaction UUID"
