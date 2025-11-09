from celery import shared_task
from django.utils import timezone
from .models import Payment, Coupon


@shared_task(bind=True, max_retries=3)
def expire_old_payments(self):
    """Expire pending payments that have passed expiry time"""
    try:
        expired_count = Payment.expire_old_payments()
        return f'Expired {expired_count} old payments'
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def expire_old_coupons(self):
    """Mark expired coupons as expired"""
    try:
        expired_count = Coupon.expire_old_coupons()
        return f'Expired {expired_count} old coupons'
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=5)
def verify_payment(self, payment_id, gateway_transaction_id):
    """Verify payment with gateway"""
    try:
        from .models import Payment
        payment = Payment.objects.get(id=payment_id)
        
        # Import appropriate gateway
        if payment.gateway == 'zarinpal':
            from .gateways.zarinpal import ZarinPalGateway
            gateway = ZarinPalGateway()
        elif payment.gateway == 'idpay':
            from .gateways.idpay import IDPayGateway
            gateway = IDPayGateway()
        else:
            return f'Unknown gateway: {payment.gateway}'
        
        # Verify payment
        result = gateway.verify(payment, gateway_transaction_id)
        
        if result['success']:
            payment.mark_as_completed(
                tracking_code=result.get('tracking_code', ''),
                card_info=result.get('card_info')
            )
            return f'Payment {payment_id} verified successfully'
        else:
            payment.mark_as_failed(result.get('message', 'Verification failed'))
            return f'Payment {payment_id} verification failed'
            
    except Payment.DoesNotExist:
        return f'Payment {payment_id} not found'
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@shared_task
def process_withdrawal(withdrawal_id):
    """Process withdrawal to user bank account"""
    try:
        from .models import Withdrawal
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        # Here you would integrate with your bank API
        # For now, just mark as completed
        withdrawal.complete(reference_number=f'REF{withdrawal_id}{int(timezone.now().timestamp())}')
        
        return f'Withdrawal {withdrawal_id} processed successfully'
    except Exception as e:
        return f'Error processing withdrawal {withdrawal_id}: {str(e)}'


@shared_task
def send_payment_receipt(payment_id):
    """Send payment receipt via email"""
    try:
        from .models import Payment
        from apps.notifications.tasks import send_email
        
        payment = Payment.objects.get(id=payment_id)
        
        if payment.status == 'completed':
            send_email.delay(
                user_id=payment.user.id,
                subject='رسید پرداخت',
                message=f'پرداخت شما به مبلغ {payment.amount:,} تومان با موفقیت انجام شد.',
                template='payment_receipt'
            )
            return f'Receipt sent for payment {payment_id}'
    except Exception as e:
        return f'Error sending receipt: {str(e)}'