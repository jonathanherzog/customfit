from django.contrib import admin

from .models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    search_fields = ("user__username", "paypal_payer_email", "paypal_transaction_id")
    list_display = ("user", "date", "pattern", "amount", "paypal_signal", "approved")
    list_filter = ("approved", "paypal_signal")
    raw_id_fields = ("user", "pattern")


admin.site.register(Transaction, TransactionAdmin)
