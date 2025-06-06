from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import PaymentDetail

class Command(BaseCommand):
    help = 'Migrate payment details from settings.PAYMENT_DETAILS to PaymentDetail model'

    def handle(self, *args, **kwargs):
        if not PaymentDetail.objects.exists():
            payment_details = getattr(settings, 'PAYMENT_DETAILS', {})
            PaymentDetail.objects.create(
                bank_name=payment_details.get('bank', {}).get('name', ''),
                bank_account_number=payment_details.get('bank', {}).get('account_number', ''),
                bank_account_name=payment_details.get('bank', {}).get('account_name', ''),
                momo_name=payment_details.get('momo', {}).get('name', ''),
                momo_number=payment_details.get('momo', {}).get('number', ''),
                momo_provider=payment_details.get('momo', {}).get('provider', '')
            )
            self.stdout.write(self.style.SUCCESS('Payment details migrated to PaymentDetail model successfully.'))
        else:
            self.stdout.write(self.style.WARNING('PaymentDetail already exists. No migration performed.'))