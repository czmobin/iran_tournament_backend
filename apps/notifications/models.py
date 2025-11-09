from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class Notification(models.Model):
    """User notifications"""
    
    TYPE_CHOICES = [
        ('tournament_created', 'تورنومنت جدید'),
        ('tournament_starting', 'شروع تورنومنت'),
        ('tournament_cancelled', 'لغو تورنومنت'),
        ('registration_confirmed', 'تایید ثبت‌نام'),
        ('registration_rejected', 'رد ثبت‌نام'),
        ('match_scheduled', 'زمان‌بندی مسابقه'),
        ('match_starting', 'شروع مسابقه'),
        ('match_reminder', 'یادآوری مسابقه'),
        ('match_result', 'نتیجه مسابقه'),
        ('opponent_submitted_result', 'حریف نتیجه ثبت کرد'),
        ('payment_completed', 'پرداخت موفق'),
        ('payment_failed', 'پرداخت ناموفق'),
        ('prize_awarded', 'دریافت جایزه'),
        ('withdrawal_requested', 'درخواست برداشت'),
        ('withdrawal_approved', 'تایید برداشت'),
        ('withdrawal_rejected', 'رد برداشت'),
        ('withdrawal_completed', 'تکمیل برداشت'),
        ('dispute_opened', 'ثبت اعتراض'),
        ('dispute_response', 'پاسخ به اعتراض'),
        ('dispute_resolved', 'حل اعتراض'),
        ('rank_changed', 'تغییر رتبه'),
        ('achievement_unlocked', 'دستاورد جدید'),
        ('warning', 'هشدار'),
        ('system', 'سیستم'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'زیاد'),
        ('urgent', 'فوری'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='کاربر'
    )
    
    notification_type = models.CharField(
        'نوع اعلان',
        max_length=30,
        choices=TYPE_CHOICES
    )
    
    priority = models.CharField(
        'اولویت',
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    title = models.CharField('عنوان', max_length=200)
    message = models.TextField('پیام')
    
    # Optional link
    link = models.CharField('لینک', max_length=500, blank=True)
    action_text = models.CharField(
        'متن دکمه',
        max_length=50,
        blank=True,
        help_text='مثال: مشاهده، پرداخت، تایید'
    )
    
    # Read status
    is_read = models.BooleanField('خوانده شده', default=False)
    read_at = models.DateTimeField('تاریخ خواندن', null=True, blank=True)
    
    # Delivery status
    is_sent_email = models.BooleanField('ایمیل ارسال شد', default=False)
    is_sent_sms = models.BooleanField('پیامک ارسال شد', default=False)
    is_sent_push = models.BooleanField('پوش ارسال شد', default=False)
    
    # Additional data
    metadata = models.JSONField(
        'داده‌های اضافی',
        default=dict,
        blank=True,
        help_text='اطلاعات اضافی برای پردازش'
    )
    
    # Expiration
    expires_at = models.DateTimeField(
        'تاریخ انقضا',
        null=True,
        blank=True,
        help_text='اعلان بعد از این تاریخ نمایش داده نمی‌شود'
    )
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    @property
    def is_expired(self):
        """Check if notification is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_email_sent(self):
        """Mark email as sent"""
        self.is_sent_email = True
        self.save(update_fields=['is_sent_email'])
    
    def mark_sms_sent(self):
        """Mark SMS as sent"""
        self.is_sent_sms = True
        self.save(update_fields=['is_sent_sms'])
    
    def mark_push_sent(self):
        """Mark push notification as sent"""
        self.is_sent_push = True
        self.save(update_fields=['is_sent_push'])
    
    @classmethod
    def create_notification(cls, user, notification_type, title, message, **kwargs):
        """Helper method to create notification"""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
    
    @classmethod
    def bulk_create_notifications(cls, users, notification_type, title, message, **kwargs):
        """Create notifications for multiple users"""
        notifications = [
            cls(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )
            for user in users
        ]
        return cls.objects.bulk_create(notifications)
    
    @classmethod
    def delete_expired(cls):
        """Delete expired notifications"""
        return cls.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='کاربر'
    )
    
    # Email notifications
    email_enabled = models.BooleanField('ایمیل فعال', default=True)
    email_tournament_created = models.BooleanField('تورنومنت جدید', default=True)
    email_match_scheduled = models.BooleanField('زمان‌بندی مسابقه', default=True)
    email_match_starting = models.BooleanField('شروع مسابقه', default=True)
    email_match_reminder = models.BooleanField('یادآوری مسابقه', default=True)
    email_prize_awarded = models.BooleanField('دریافت جایزه', default=True)
    email_payment = models.BooleanField('پرداخت‌ها', default=True)
    email_withdrawal = models.BooleanField('برداشت‌ها', default=True)
    email_dispute = models.BooleanField('اعتراضات', default=True)
    email_system = models.BooleanField('اعلان‌های سیستم', default=True)
    
    # SMS notifications
    sms_enabled = models.BooleanField('پیامک فعال', default=False)
    sms_match_starting = models.BooleanField('شروع مسابقه (پیامک)', default=False)
    sms_match_reminder = models.BooleanField('یادآوری مسابقه (پیامک)', default=False)
    sms_payment = models.BooleanField('پرداخت‌ها (پیامک)', default=False)
    sms_withdrawal = models.BooleanField('برداشت‌ها (پیامک)', default=False)
    
    # Push notifications
    push_enabled = models.BooleanField('اعلان‌های پوش', default=True)
    push_tournament = models.BooleanField('تورنومنت‌ها', default=True)
    push_match = models.BooleanField('مسابقات', default=True)
    push_payment = models.BooleanField('پرداخت‌ها', default=True)
    push_dispute = models.BooleanField('اعتراضات', default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField('ساعت‌های سکوت', default=False)
    quiet_hours_start = models.TimeField('شروع سکوت', null=True, blank=True)
    quiet_hours_end = models.TimeField('پایان سکوت', null=True, blank=True)
    
    # Frequency
    digest_enabled = models.BooleanField(
        'خلاصه اعلان‌ها',
        default=False,
        help_text='دریافت خلاصه اعلان‌ها به جای تک‌تک'
    )
    digest_frequency = models.CharField(
        'دوره ارسال خلاصه',
        max_length=10,
        choices=[
            ('daily', 'روزانه'),
            ('weekly', 'هفتگی'),
        ],
        default='daily',
        blank=True
    )
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'تنظیمات اعلان'
        verbose_name_plural = 'تنظیمات اعلان‌ها'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def should_send_email(self, notification_type):
        """Check if email should be sent for this notification type"""
        if not self.email_enabled:
            return False
        
        mapping = {
            'tournament_created': self.email_tournament_created,
            'match_scheduled': self.email_match_scheduled,
            'match_starting': self.email_match_starting,
            'match_reminder': self.email_match_reminder,
            'prize_awarded': self.email_prize_awarded,
            'payment_completed': self.email_payment,
            'payment_failed': self.email_payment,
            'withdrawal_approved': self.email_withdrawal,
            'withdrawal_rejected': self.email_withdrawal,
            'dispute_opened': self.email_dispute,
            'dispute_resolved': self.email_dispute,
            'system': self.email_system,
        }
        return mapping.get(notification_type, False)
    
    def should_send_sms(self, notification_type):
        """Check if SMS should be sent for this notification type"""
        if not self.sms_enabled:
            return False
        
        mapping = {
            'match_starting': self.sms_match_starting,
            'match_reminder': self.sms_match_reminder,
            'payment_completed': self.sms_payment,
            'withdrawal_approved': self.sms_withdrawal,
        }
        return mapping.get(notification_type, False)
    
    def should_send_push(self, notification_type):
        """Check if push notification should be sent"""
        if not self.push_enabled:
            return False
        
        # Check quiet hours
        if self.quiet_hours_enabled and self.is_quiet_time():
            return False
        
        type_category = {
            'tournament': ['tournament_created', 'tournament_starting', 'tournament_cancelled'],
            'match': ['match_scheduled', 'match_starting', 'match_reminder', 'match_result'],
            'payment': ['payment_completed', 'payment_failed', 'prize_awarded', 'withdrawal_approved'],
            'dispute': ['dispute_opened', 'dispute_response', 'dispute_resolved'],
        }
        
        for category, types in type_category.items():
            if notification_type in types:
                return getattr(self, f'push_{category}', True)
        
        return True
    
    def is_quiet_time(self):
        """Check if current time is in quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from datetime import datetime
        now = datetime.now().time()
        
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:  # Crosses midnight
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class NotificationTemplate(models.Model):
    """Templates for notifications"""
    
    notification_type = models.CharField(
        'نوع اعلان',
        max_length=30,
        unique=True,
        choices=Notification.TYPE_CHOICES
    )
    
    # Email template
    email_subject = models.CharField('موضوع ایمیل', max_length=200, blank=True)
    email_body = models.TextField(
        'متن ایمیل',
        blank=True,
        help_text='از {{variable}} برای متغیرها استفاده کنید'
    )
    
    # SMS template
    sms_body = models.CharField(
        'متن پیامک',
        max_length=160,
        blank=True,
        help_text='حداکثر 160 کاراکتر'
    )
    
    # Push template
    push_title = models.CharField('عنوان پوش', max_length=100, blank=True)
    push_body = models.CharField('متن پوش', max_length=200, blank=True)
    
    # In-app template
    app_title = models.CharField('عنوان اپ', max_length=200)
    app_body = models.TextField('متن اپ')
    
    is_active = models.BooleanField('فعال', default=True)
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        verbose_name = 'قالب اعلان'
        verbose_name_plural = 'قالب‌های اعلان'
    
    def __str__(self):
        return f"Template: {self.get_notification_type_display()}"
    
    def render(self, context):
        """Render template with context variables"""
        from django.template import Template, Context
        
        return {
            'email_subject': Template(self.email_subject).render(Context(context)),
            'email_body': Template(self.email_body).render(Context(context)),
            'sms_body': Template(self.sms_body).render(Context(context)),
            'push_title': Template(self.push_title).render(Context(context)),
            'push_body': Template(self.push_body).render(Context(context)),
            'app_title': Template(self.app_title).render(Context(context)),
            'app_body': Template(self.app_body).render(Context(context)),
        }