from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Extended user model for Clash Arena"""
    
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="شماره تلفن باید به فرمت 09123456789 باشد"
    )
    
    email = models.EmailField('ایمیل', unique=True)
    phone_number = models.CharField(
        'شماره تماس',
        max_length=11,
        validators=[phone_regex],
        unique=True,
        null=True,
        blank=True
    )
    profile_picture = models.ImageField(
        'تصویر پروفایل',
        upload_to='profile_pictures/',
        null=True,
        blank=True
    )
    wallet_balance = models.DecimalField(
        'موجودی کیف پول',
        max_digits=10,
        decimal_places=0,
        default=0
    )
    clash_royale_tag = models.CharField(
        'تگ کلش رویال',
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='مثال: #ABC123XYZ'
    )
    is_verified = models.BooleanField('تایید شده', default=False)
    created_at = models.DateTimeField('تاریخ ثبت‌نام', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def add_to_wallet(self, amount):
        """Add amount to wallet"""
        self.wallet_balance += amount
        self.save(update_fields=['wallet_balance'])
    
    def deduct_from_wallet(self, amount):
        """Deduct amount from wallet if sufficient balance"""
        if self.wallet_balance >= amount:
            self.wallet_balance -= amount
            self.save(update_fields=['wallet_balance'])
            return True
        return False


class UserStats(models.Model):
    """User tournament statistics"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='stats',
        verbose_name='کاربر'
    )
    tournaments_played = models.PositiveIntegerField('تورنومنت‌های بازی شده', default=0)
    tournaments_won = models.PositiveIntegerField('تورنومنت‌های برنده شده', default=0)
    total_matches = models.PositiveIntegerField('مجموع بازی‌ها', default=0)
    matches_won = models.PositiveIntegerField('بازی‌های برده', default=0)
    total_earnings = models.DecimalField(
        'مجموع درآمد',
        max_digits=12,
        decimal_places=0,
        default=0
    )
    win_rate = models.DecimalField(
        'درصد برد',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    ranking = models.PositiveIntegerField('رتبه', default=0)
    
    class Meta:
        db_table = 'user_stats'
        verbose_name = 'آمار کاربر'
        verbose_name_plural = 'آمار کاربران'
    
    def __str__(self):
        return f"Stats for {self.user.username}"
    
    def update_win_rate(self):
        """Calculate and update win rate"""
        if self.total_matches > 0:
            self.win_rate = (self.matches_won / self.total_matches) * 100
            self.save(update_fields=['win_rate'])