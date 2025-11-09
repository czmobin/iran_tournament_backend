from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from apps.accounts.models import User
from apps.tournaments.models import Tournament
import uuid


class Payment(models.Model):
    """Payment transactions"""
    
    TYPE_CHOICES = [
        ('deposit', 'شارژ کیف پول'),
        ('tournament_entry', 'ورودی تورنومنت'),
        ('prize', 'جایزه'),
        ('withdrawal', 'برداشت'),
        ('refund', 'بازگشت وجه'),
        ('penalty', 'جریمه'),
        ('bonus', 'پاداش'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('verifying', 'در حال تایید'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'بازگشت داده شده'),
        ('expired', 'منقضی شده'),
    ]
    
    GATEWAY_CHOICES = [
        ('zarinpal', 'زرین‌پال'),
        ('idpay', 'آیدی‌پی'),
        ('nextpay', 'نکست‌پی'),
        ('zibal', 'زیبال'),
        ('wallet', 'کیف پول'),
        ('admin', 'ادمین'),
    ]
    
    # Unique transaction ID
    transaction_id = models.UUIDField(
        'شناسه تراکنش',
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='کاربر'
    )
    
    payment_type = models.CharField(
        'نوع پرداخت',
        max_length=20,
        choices=TYPE_CHOICES
    )
    
    amount = models.DecimalField(
        'مبلغ',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # Fee/Commission
    fee = models.DecimalField(
        'کارمزد',
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    final_amount = models.DecimalField(
        'مبلغ نهایی',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='مبلغ بعد از کسر کارمزد'
    )
    
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    gateway = models.CharField(
        'درگاه پرداخت',
        max_length=20,
        choices=GATEWAY_CHOICES
    )
    
    # Gateway reference
    gateway_transaction_id = models.CharField(
        'شناسه تراکنش درگاه',
        max_length=200,
        blank=True,
        null=True,
        db_index=True
    )
    gateway_tracking_code = models.CharField(
        'کد پیگیری درگاه',
        max_length=200,
        blank=True,
        null=True
    )
    gateway_response = models.JSONField(
        'پاسخ درگاه',
        blank=True,
        null=True
    )
    gateway_callback_data = models.JSONField(
        'داده‌های callback',
        blank=True,
        null=True
    )
    
    # Related objects
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='تورنومنت'
    )
    
    # Card info (last 4 digits only)
    card_number = models.CharField(
        'شماره کارت (4 رقم آخر)',
        max_length=4,
        blank=True,
        null=True
    )
    card_holder_name = models.CharField(
        'نام صاحب کارت',
        max_length=200,
        blank=True,
        null=True
    )
    
    # Additional info
    description = models.TextField('توضیحات', blank=True)
    admin_note = models.TextField('یادداشت ادمین', blank=True)
    
    # Network info
    ip_address = models.GenericIPAddressField('آدرس IP', null=True, blank=True)
    user_agent = models.CharField('User Agent', max_length=500, blank=True)
    
    # Retry tracking
    retry_count = models.PositiveIntegerField('تعداد تلاش مجدد', default=0)
    
    # Timestamps
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    completed_at = models.DateTimeField('تاریخ تکمیل', null=True, blank=True)
    expires_at = models.DateTimeField('تاریخ انقضا', null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['payment_type', 'status']),
            models.Index(fields=['gateway', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_payment_type_display()} - {self.amount:,} تومان"
    
    def save(self, *args, **kwargs):
        # Calculate final amount
        if not self.final_amount:
            self.final_amount = self.amount - self.fee
        
        # Set expiration for pending payments (15 minutes)
        if not self.expires_at and self.status == 'pending':
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if payment is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at and self.status == 'pending'
    
    @property
    def can_retry(self):
        """Check if payment can be retried"""
        return self.status in ['failed', 'expired'] and self.retry_count < 3
    
    @transaction.atomic
    def mark_as_completed(self, tracking_code='', card_info=None):
        """Mark payment as completed"""
        if self.status == 'completed':
            return False
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        
        if tracking_code:
            self.gateway_tracking_code = tracking_code
        
        if card_info:
            self.card_number = card_info.get('last_4_digits', '')
            self.card_holder_name = card_info.get('holder_name', '')
        
        self.save(update_fields=[
            'status', 'completed_at', 'gateway_tracking_code',
            'card_number', 'card_holder_name'
        ])
        
        # Update user wallet based on type
        if self.payment_type == 'deposit':
            self.user.add_to_wallet(self.final_amount)
            Transaction.record(
                user=self.user,
                transaction_type='credit',
                amount=self.final_amount,
                description=f'شارژ کیف پول - {self.gateway_tracking_code}',
                payment=self
            )
        elif self.payment_type == 'prize':
            self.user.add_to_wallet(self.amount)
            Transaction.record(
                user=self.user,
                transaction_type='credit',
                amount=self.amount,
                description=f'جایزه تورنومنت - {self.tournament.title if self.tournament else ""}',
                payment=self
            )
        elif self.payment_type == 'bonus':
            self.user.add_to_wallet(self.amount)
            Transaction.record(
                user=self.user,
                transaction_type='credit',
                amount=self.amount,
                description='پاداش سیستم',
                payment=self
            )
        
        # Send notification
        self._send_completion_notification()
        
        return True
    
    def mark_as_failed(self, reason=''):
        """Mark payment as failed"""
        if self.status in ['completed', 'refunded']:
            return False
        
        self.status = 'failed'
        self.description = f"{self.description}\nFailed: {reason}".strip()
        self.save(update_fields=['status', 'description'])
        
        # Send notification
        self._send_failure_notification(reason)
        
        return True
    
    @transaction.atomic
    def refund(self, reason='', admin_user=None):
        """Process refund"""
        if self.status != 'completed':
            raise ValidationError('فقط پرداخت‌های تکمیل شده قابل بازگشت هستند')
        
        if self.payment_type == 'refund':
            raise ValidationError('نمی‌توان بازگشت وجه را بازگشت داد')
        
        self.status = 'refunded'
        self.admin_note = f"{self.admin_note}\nRefund: {reason}".strip()
        self.save(update_fields=['status', 'admin_note'])
        
        # Return money to wallet
        if self.payment_type in ['tournament_entry', 'withdrawal']:
            self.user.add_to_wallet(self.amount)
            Transaction.record(
                user=self.user,
                transaction_type='credit',
                amount=self.amount,
                description=f'بازگشت وجه - {reason}',
                payment=self
            )
        
        # Create refund payment record
        Payment.objects.create(
            user=self.user,
            payment_type='refund',
            amount=self.amount,
            status='completed',
            gateway='admin',
            description=f'بازگشت پرداخت {self.transaction_id} - {reason}',
            completed_at=timezone.now()
        )
        
        return True
    
    def retry(self):
        """Retry failed payment"""
        if not self.can_retry:
            return False
        
        self.retry_count += 1
        self.status = 'pending'
        self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        self.save(update_fields=['retry_count', 'status', 'expires_at'])
        
        return True
    
    def cancel(self, reason=''):
        """Cancel payment"""
        if self.status in ['completed', 'refunded']:
            raise ValidationError('نمی‌توان پرداخت تکمیل شده را لغو کرد')
        
        self.status = 'cancelled'
        self.description = f"{self.description}\nCancelled: {reason}".strip()
        self.save(update_fields=['status', 'description'])
        
        return True
    
    def _send_completion_notification(self):
        """Send payment completion notification"""
        from apps.notifications.models import Notification
        
        Notification.create_notification(
            user=self.user,
            notification_type='payment_completed',
            title='پرداخت موفق',
            message=f'پرداخت {self.amount:,} تومان با موفقیت انجام شد',
            priority='high',
            link=f'/payments/{self.transaction_id}/',
            metadata={'payment_id': str(self.transaction_id)}
        )
    
    def _send_failure_notification(self, reason):
        """Send payment failure notification"""
        from apps.notifications.models import Notification
        
        Notification.create_notification(
            user=self.user,
            notification_type='payment_failed',
            title='پرداخت ناموفق',
            message=f'پرداخت {self.amount:,} تومان ناموفق بود. {reason}',
            priority='high',
            link=f'/payments/{self.transaction_id}/',
            metadata={'payment_id': str(self.transaction_id)}
        )
    
    @classmethod
    def expire_old_payments(cls):
        """Expire old pending payments"""
        return cls.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        ).update(status='expired')


class Withdrawal(models.Model):
    """Withdrawal requests from wallet"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('approved', 'تایید شده'),
        ('processing', 'در حال پردازش'),
        ('completed', 'تکمیل شده'),
        ('rejected', 'رد شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='withdrawals',
        verbose_name='کاربر'
    )
    
    amount = models.DecimalField(
        'مبلغ',
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(10000)]
    )
    
    # Fee
    fee = models.DecimalField(
        'کارمزد',
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    final_amount = models.DecimalField(
        'مبلغ نهایی',
        max_digits=12,
        decimal_places=0,
        default=0
    )
    
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Bank details
    bank_name = models.CharField('نام بانک', max_length=100, blank=True)
    bank_account_number = models.CharField(
        'شماره حساب',
        max_length=50
    )
    bank_card_number = models.CharField(
        'شماره کارت',
        max_length=16,
        help_text='16 رقم'
    )
    account_holder_name = models.CharField(
        'نام صاحب حساب',
        max_length=200
    )
    sheba_number = models.CharField(
        'شماره شبا',
        max_length=26,
        blank=True,
        help_text='IR به همراه 24 رقم'
    )
    
    # Tracking
    tracking_code = models.CharField(
        'کد پیگیری',
        max_length=50,
        blank=True
    )
    reference_number = models.CharField(
        'شماره مرجع',
        max_length=50,
        blank=True
    )
    
    # Notes
    user_note = models.TextField('یادداشت کاربر', blank=True)
    admin_note = models.TextField('یادداشت ادمین', blank=True)
    rejection_reason = models.TextField('دلیل رد', blank=True)
    
    # Processing
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_withdrawals',
        verbose_name='پردازش شده توسط'
    )
    
    # Payment record
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawal',
        verbose_name='پرداخت'
    )
    
    created_at = models.DateTimeField('تاریخ درخواست', auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField('تاریخ پردازش', null=True, blank=True)
    completed_at = models.DateTimeField('تاریخ تکمیل', null=True, blank=True)
    
    class Meta:
        db_table = 'withdrawals'
        verbose_name = 'برداشت'
        verbose_name_plural = 'برداشت‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.amount:,} تومان - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Calculate final amount (amount - fee)
        if not self.final_amount:
            self.final_amount = self.amount - self.fee
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate withdrawal"""
        # Check minimum amount
        if self.amount < 10000:
            raise ValidationError('حداقل مبلغ برداشت 10,000 تومان است')
        
        # Check user balance
        if self.status == 'pending' and self.user.wallet_balance < self.amount:
            raise ValidationError('موجودی کافی نیست')
        
        # Validate card number (must be 16 digits)
        if self.bank_card_number and len(self.bank_card_number) != 16:
            raise ValidationError('شماره کارت باید 16 رقم باشد')
        
        # Validate sheba
        if self.sheba_number:
            if not self.sheba_number.startswith('IR'):
                raise ValidationError('شماره شبا باید با IR شروع شود')
            if len(self.sheba_number) != 26:
                raise ValidationError('شماره شبا باید 26 کاراکتر باشد')
    
    @transaction.atomic
    def approve(self, admin_user, tracking_code=''):
        """Approve withdrawal request"""
        if self.status != 'pending':
            raise ValidationError('فقط درخواست‌های در انتظار قابل تایید هستند')
        
        # Check if user has sufficient balance
        if self.user.wallet_balance < self.amount:
            raise ValidationError('موجودی کاربر کافی نیست')
        
        # Deduct from wallet
        if not self.user.deduct_from_wallet(self.amount):
            raise ValidationError('خطا در کسر از کیف پول')
        
        self.status = 'approved'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.tracking_code = tracking_code or f'WD{self.id}{int(timezone.now().timestamp())}'
        self.save()
        
        # Create payment record
        self.payment = Payment.objects.create(
            user=self.user,
            payment_type='withdrawal',
            amount=self.amount,
            fee=self.fee,
            final_amount=self.final_amount,
            status='processing',
            gateway='admin',
            description=f'برداشت از کیف پول - کد پیگیری: {self.tracking_code}',
            gateway_tracking_code=self.tracking_code
        )
        self.save(update_fields=['payment'])
        
        # Record transaction
        Transaction.record(
            user=self.user,
            transaction_type='debit',
            amount=self.amount,
            description=f'برداشت از کیف پول - {self.tracking_code}',
            payment=self.payment
        )
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.create_notification(
            user=self.user,
            notification_type='withdrawal_approved',
            title='تایید درخواست برداشت',
            message=f'درخواست برداشت {self.amount:,} تومان تایید شد',
            priority='high',
            link=f'/withdrawals/{self.id}/',
            metadata={'withdrawal_id': self.id}
        )
        
        return True
    
    @transaction.atomic
    def reject(self, admin_user, reason):
        """Reject withdrawal request"""
        if self.status != 'pending':
            raise ValidationError('فقط درخواست‌های در انتظار قابل رد هستند')
        
        self.status = 'rejected'
        self.rejection_reason = reason
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.create_notification(
            user=self.user,
            notification_type='withdrawal_rejected',
            title='رد درخواست برداشت',
            message=f'درخواست برداشت {self.amount:,} تومان رد شد. دلیل: {reason}',
            priority='high',
            link=f'/withdrawals/{self.id}/',
            metadata={'withdrawal_id': self.id}
        )
        
        return True
    
    @transaction.atomic
    def complete(self, reference_number=''):
        """Mark withdrawal as completed"""
        if self.status not in ['approved', 'processing']:
            raise ValidationError('برداشت باید در حالت تایید شده یا در حال پردازش باشد')
        
        self.status = 'completed'
        self.reference_number = reference_number
        self.completed_at = timezone.now()
        self.save()
        
        # Update payment record
        if self.payment:
            self.payment.mark_as_completed(tracking_code=reference_number)
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.create_notification(
            user=self.user,
            notification_type='withdrawal_completed',
            title='تکمیل برداشت',
            message=f'مبلغ {self.final_amount:,} تومان به حساب شما واریز شد',
            priority='high',
            link=f'/withdrawals/{self.id}/',
            metadata={'withdrawal_id': self.id, 'reference': reference_number}
        )
        
        return True
    
    def cancel(self, by_admin=False, reason=''):
        """Cancel withdrawal"""
        if self.status not in ['pending', 'approved']:
            raise ValidationError('فقط درخواست‌های در انتظار یا تایید شده قابل لغو هستند')
        
        # If already approved, return money to wallet
        if self.status == 'approved':
            self.user.add_to_wallet(self.amount)
            Transaction.record(
                user=self.user,
                transaction_type='credit',
                amount=self.amount,
                description=f'لغو برداشت - {reason}',
                payment=self.payment
            )
        
        self.status = 'cancelled'
        self.admin_note = f"{self.admin_note}\nCancelled: {reason}".strip()
        self.save()
        
        return True


class Transaction(models.Model):
    """Wallet transaction history"""
    
    TYPE_CHOICES = [
        ('credit', 'واریز'),
        ('debit', 'برداشت'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='کاربر'
    )
    
    transaction_type = models.CharField(
        'نوع تراکنش',
        max_length=10,
        choices=TYPE_CHOICES,
        db_index=True
    )
    
    amount = models.DecimalField(
        'مبلغ',
        max_digits=12,
        decimal_places=0
    )
    
    balance_before = models.DecimalField(
        'موجودی قبل',
        max_digits=12,
        decimal_places=0
    )
    
    balance_after = models.DecimalField(
        'موجودی بعد',
        max_digits=12,
        decimal_places=0
    )
    
    description = models.TextField('توضیحات')
    
    # Related payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='پرداخت'
    )
    
    # Related tournament
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='تورنومنت'
    )
    
    created_at = models.DateTimeField('تاریخ', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['transaction_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - {self.amount:,} تومان"
    
    @classmethod
    def record(cls, user, transaction_type, amount, description, payment=None, tournament=None):
        """Record a transaction"""
        balance_before = user.wallet_balance
        
        if transaction_type == 'credit':
            balance_after = balance_before + amount
        else:  # debit
            balance_after = balance_before - amount
        
        return cls.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            payment=payment,
            tournament=tournament
        )


class PaymentGatewayConfig(models.Model):
    """Payment gateway configuration"""
    
    GATEWAY_CHOICES = [
        ('zarinpal', 'زرین‌پال'),
        ('idpay', 'آیدی‌پی'),
        ('nextpay', 'نکست‌پی'),
        ('zibal', 'زیبال'),
    ]
    
    gateway = models.CharField(
        'درگاه',
        max_length=20,
        choices=GATEWAY_CHOICES,
        unique=True
    )
    
    is_active = models.BooleanField('فعال', default=True)
    
    merchant_id = models.CharField('شناسه پذیرنده', max_length=200)
    api_key = models.CharField('کلید API', max_length=200, blank=True)
    
    # Minimum and maximum transaction amounts
    min_amount = models.DecimalField(
        'حداقل مبلغ',
        max_digits=10,
        decimal_places=0,
        default=1000
    )
    max_amount = models.DecimalField(
        'حداکثر مبلغ',
        max_digits=12,
        decimal_places=0,
        default=50000000
    )
    
    # Fee configuration
    fee_percentage = models.DecimalField(
        'درصد کارمزد',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    fixed_fee = models.DecimalField(
        'کارمزد ثابت',
        max_digits=10,
        decimal_places=0,
        default=0
    )
    
    # Gateway URLs
    payment_url = models.URLField('آدرس پرداخت', blank=True)
    verify_url = models.URLField('آدرس تایید', blank=True)
    callback_url = models.URLField('آدرس callback', blank=True)
    
    # Priority
    priority = models.PositiveIntegerField(
        'اولویت',
        default=1,
        help_text='کمترین عدد = بالاترین اولویت'
    )
    
    # Additional settings
    settings = models.JSONField('تنظیمات اضافی', default=dict, blank=True)
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'payment_gateway_configs'
        verbose_name = 'پیکربندی درگاه پرداخت'
        verbose_name_plural = 'پیکربندی‌های درگاه پرداخت'
        ordering = ['priority']
    
    def __str__(self):
        status = 'فعال' if self.is_active else 'غیرفعال'
        return f"{self.get_gateway_display()} - {status}"
    
    def calculate_fee(self, amount):
        """Calculate fee for given amount"""
        percentage_fee = (amount * self.fee_percentage) / 100
        total_fee = percentage_fee + self.fixed_fee
        return int(total_fee)
    
    def is_amount_valid(self, amount):
        """Check if amount is within limits"""
        return self.min_amount <= amount <= self.max_amount
    
    @classmethod
    def get_active_gateway(cls, amount=None):
        """Get the best active gateway for given amount"""
        gateways = cls.objects.filter(is_active=True).order_by('priority')
        
        if amount:
            gateways = [g for g in gateways if g.is_amount_valid(amount)]
        
        return gateways[0] if gateways else None


class PaymentLog(models.Model):
    """Detailed payment log for debugging"""
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='پرداخت'
    )
    
    action = models.CharField(
        'عملیات',
        max_length=50,
        help_text='مثال: request_sent, callback_received, verified'
    )
    
    status = models.CharField('وضعیت', max_length=20, blank=True)
    
    request_data = models.JSONField(
        'داده‌های درخواست',
        null=True,
        blank=True
    )
    
    response_data = models.JSONField(
        'داده‌های پاسخ',
        null=True,
        blank=True
    )
    
    error_message = models.TextField('پیام خطا', blank=True)
    
    ip_address = models.GenericIPAddressField('آدرس IP', null=True, blank=True)
    
    created_at = models.DateTimeField('زمان', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'payment_logs'
        verbose_name = 'لاگ پرداخت'
        verbose_name_plural = 'لاگ‌های پرداخت'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.payment.transaction_id} - {self.action}"
    
    @classmethod
    def log(cls, payment, action, status='', request_data=None, response_data=None, error_message='', ip_address=None):
        """Create a payment log entry"""
        return cls.objects.create(
            payment=payment,
            action=action,
            status=status,
            request_data=request_data,
            response_data=response_data,
            error_message=error_message,
            ip_address=ip_address
        )


class Coupon(models.Model):
    """Discount coupons for tournaments"""
    
    TYPE_CHOICES = [
        ('percentage', 'درصدی'),
        ('fixed', 'مبلغ ثابت'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('expired', 'منقضی شده'),
    ]
    
    code = models.CharField(
        'کد تخفیف',
        max_length=50,
        unique=True,
        db_index=True
    )
    
    discount_type = models.CharField(
        'نوع تخفیف',
        max_length=20,
        choices=TYPE_CHOICES,
        default='percentage'
    )
    
    discount_value = models.DecimalField(
        'مقدار تخفیف',
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    max_discount = models.DecimalField(
        'حداکثر تخفیف',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='برای تخفیف درصدی - 0 = نامحدود'
    )
    
    min_purchase = models.DecimalField(
        'حداقل خرید',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='حداقل مبلغ برای استفاده از کوپن'
    )
    
    # Usage limits
    max_uses = models.PositiveIntegerField(
        'حداکثر استفاده کل',
        default=0,
        help_text='0 = نامحدود'
    )
    max_uses_per_user = models.PositiveIntegerField(
        'حداکثر استفاده هر کاربر',
        default=1
    )
    current_uses = models.PositiveIntegerField('تعداد استفاده', default=0)
    
    # Validity
    valid_from = models.DateTimeField('معتبر از')
    valid_until = models.DateTimeField('معتبر تا')
    
    # Restrictions
    tournaments = models.ManyToManyField(
        'tournaments.Tournament',
        related_name='coupons',
        blank=True,
        verbose_name='تورنومنت‌های مجاز',
        help_text='خالی = همه تورنومنت‌ها'
    )
    
    allowed_users = models.ManyToManyField(
        User,
        related_name='allowed_coupons',
        blank=True,
        verbose_name='کاربران مجاز',
        help_text='خالی = همه کاربران'
    )
    
    first_purchase_only = models.BooleanField(
        'فقط خرید اول',
        default=False
    )
    
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    
    description = models.TextField('توضیحات', blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_coupons',
        verbose_name='ایجاد شده توسط'
    )
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'coupons'
        verbose_name = 'کوپن تخفیف'
        verbose_name_plural = 'کوپن‌های تخفیف'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'status']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else ' تومان'}"
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.valid_from <= now <= self.valid_until and
            (self.max_uses == 0 or self.current_uses < self.max_uses)
        )
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given price"""
        if self.discount_type == 'percentage':
            discount = (amount * self.discount_value) / 100
            if self.max_discount > 0:
                discount = min(discount, self.max_discount)
        else:  # fixed
            discount = min(self.discount_value, amount)
        
        return int(discount)
    
    def can_use(self, user, tournament=None, amount=0):
        """Check if user can use this coupon"""
        if not self.is_valid:
            return False, 'کوپن معتبر نیست'
        
        # Check minimum purchase
        if amount < self.min_purchase:
            return False, f'حداقل خرید {self.min_purchase:,} تومان است'
        
        # Check tournament restriction
        if tournament and self.tournaments.exists():
            if tournament not in self.tournaments.all():
                return False, 'این کوپن برای این تورنومنت معتبر نیست'
        
        # Check user restriction
        if self.allowed_users.exists():
            if user not in self.allowed_users.all():
                return False, 'شما مجاز به استفاده از این کوپن نیستید'
        
        # Check per-user usage limit
        user_uses = CouponUsage.objects.filter(coupon=self, user=user).count()
        if user_uses >= self.max_uses_per_user:
            return False, 'شما قبلاً از این کوپن استفاده کرده‌اید'
        
        # Check first purchase only
        if self.first_purchase_only:
            if Payment.objects.filter(
                user=user,
                payment_type='tournament_entry',
                status='completed'
            ).exists():
                return False, 'این کوپن فقط برای اولین خرید است'
        
        return True, ''
    
    @transaction.atomic
    def use(self, user, payment):
        """Use coupon and record usage"""
        if not self.is_valid:
            raise ValidationError('کوپن معتبر نیست')
        
        # Increment usage
        self.current_uses += 1
        self.save(update_fields=['current_uses'])
        
        # Record usage
        CouponUsage.objects.create(
            coupon=self,
            user=user,
            payment=payment,
            discount_amount=self.calculate_discount(payment.amount)
        )
    
    @classmethod
    def expire_old_coupons(cls):
        """Mark expired coupons"""
        return cls.objects.filter(
            status='active',
            valid_until__lt=timezone.now()
        ).update(status='expired')


class CouponUsage(models.Model):
    """Track coupon usage"""
    
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name='کوپن'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        verbose_name='کاربر'
    )
    
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='coupon_usage',
        verbose_name='پرداخت'
    )
    
    discount_amount = models.DecimalField(
        'مبلغ تخفیف',
        max_digits=10,
        decimal_places=0
    )
    
    used_at = models.DateTimeField('زمان استفاده', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'coupon_usages'
        verbose_name = 'استفاده از کوپن'
        verbose_name_plural = 'استفاده‌های کوپن'
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['coupon', '-used_at']),
            models.Index(fields=['user', '-used_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code} - {self.discount_amount:,} تومان"