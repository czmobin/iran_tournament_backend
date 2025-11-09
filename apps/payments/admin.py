from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from .models import (
    Payment, Withdrawal, Transaction,
    PaymentGatewayConfig, PaymentLog,
    Coupon, CouponUsage
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment admin"""
    
    list_display = (
        'transaction_id_short', 'user_link',
        'payment_type_badge', 'amount_display',
        'status_badge', 'gateway',
        'created_at'
    )
    
    list_filter = (
        'status', 'payment_type', 'gateway',
        'created_at'
    )
    
    search_fields = (
        'transaction_id', 'gateway_transaction_id',
        'user__username', 'user__email',
        'description'
    )
    
    readonly_fields = (
        'transaction_id', 'user', 'payment_type',
        'final_amount', 'gateway_transaction_id',
        'gateway_tracking_code', 'gateway_response',
        'gateway_callback_data', 'created_at',
        'updated_at', 'completed_at', 'card_info_display',
        'retry_count'
    )
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'transaction_id', 'user', 'payment_type', 'status'
            )
        }),
        ('مبلغ', {
            'fields': ('amount', 'fee', 'final_amount')
        }),
        ('درگاه پرداخت', {
            'fields': (
                'gateway', 'gateway_transaction_id',
                'gateway_tracking_code', 'card_info_display'
            )
        }),
        ('اطلاعات تورنومنت', {
            'fields': ('tournament',),
            'classes': ('collapse',)
        }),
        ('اطلاعات فنی', {
            'fields': (
                'gateway_response', 'gateway_callback_data',
                'ip_address', 'user_agent', 'retry_count'
            ),
            'classes': ('collapse',)
        }),
        ('توضیحات', {
            'fields': ('description', 'admin_note')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_completed', 'mark_as_failed', 'refund_payments']
    
    def transaction_id_short(self, obj):
        """Show short transaction ID"""
        return format_html(
            '<code>{}</code>',
            str(obj.transaction_id)[:8]
        )
    transaction_id_short.short_description = 'شناسه تراکنش'
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def payment_type_badge(self, obj):
        colors = {
            'deposit': 'blue',
            'tournament_entry': 'purple',
            'prize': 'green',
            'withdrawal': 'orange',
            'refund': 'gray',
            'penalty': 'red',
            'bonus': 'gold'
        }
        color = colors.get(obj.payment_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_payment_type_display()
        )
    payment_type_badge.short_description = 'نوع'
    
    def amount_display(self, obj):
        """Display amount with fee"""
        if obj.fee > 0:
            return format_html(
                '<strong>{:,}</strong> تومان<br>'
                '<small style="color: red;">کارمزد: -{:,}</small><br>'
                '<small style="color: green;">خالص: {:,}</small>',
                obj.amount, obj.fee, obj.final_amount
            )
        return format_html('<strong>{:,}</strong> تومان', obj.amount)
    amount_display.short_description = 'مبلغ'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'verifying': 'purple',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'darkred',
            'expired': 'lightgray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def card_info_display(self, obj):
        """Display card info"""
        if obj.card_number:
            return format_html(
                'کارت: ****{}<br>صاحب کارت: {}',
                obj.card_number, obj.card_holder_name or '—'
            )
        return '—'
    card_info_display.short_description = 'اطلاعات کارت'
    
    def mark_as_completed(self, request, queryset):
        """Mark payments as completed"""
        success = 0
        for payment in queryset.filter(status__in=['pending', 'processing', 'verifying']):
            try:
                payment.mark_as_completed()
                success += 1
            except Exception as e:
                messages.error(request, f'خطا در تکمیل {payment.transaction_id}: {str(e)}')
        
        if success:
            self.message_user(request, f'{success} پرداخت تکمیل شد.', messages.SUCCESS)
    mark_as_completed.short_description = 'تکمیل پرداخت‌ها'
    
    def mark_as_failed(self, request, queryset):
        """Mark payments as failed"""
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'{updated} پرداخت ناموفق علامت زده شد.')
    mark_as_failed.short_description = 'علامت‌گذاری به عنوان ناموفق'
    
    def refund_payments(self, request, queryset):
        """Refund selected payments"""
        from django import forms
        from django.shortcuts import render, redirect
        
        class RefundForm(forms.Form):
            reason = forms.CharField(
                label='دلیل بازگشت',
                widget=forms.Textarea,
                required=True
            )
        
        if 'apply' in request.POST:
            form = RefundForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                success = 0
                
                for payment in queryset.filter(status='completed'):
                    try:
                        payment.refund(reason=reason, admin_user=request.user)
                        success += 1
                    except Exception as e:
                        messages.error(request, f'خطا: {str(e)}')
                
                if success:
                    self.message_user(request, f'{success} پرداخت بازگشت داده شد.')
                return redirect('..')
        else:
            form = RefundForm()
        
        return render(
            request,
            'admin/refund_form.html',
            {'form': form, 'payments': queryset}
        )
    refund_payments.short_description = 'بازگشت وجه'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of completed payments"""
        if obj and obj.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    """Withdrawal admin"""
    
    list_display = (
        'id', 'user_link', 'amount_display',
        'status_badge', 'bank_info_short',
        'tracking_code', 'created_at'
    )
    
    list_filter = ('status', 'created_at', 'processed_at')
    
    search_fields = (
        'user__username', 'user__email',
        'tracking_code', 'bank_card_number',
        'account_holder_name'
    )
    
    readonly_fields = (
        'user', 'created_at', 'processed_at',
        'completed_at', 'final_amount',
        'payment'
    )
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'status')
        }),
        ('مبلغ', {
            'fields': ('amount', 'fee', 'final_amount')
        }),
        ('اطلاعات بانکی', {
            'fields': (
                'bank_name', 'bank_account_number',
                'bank_card_number', 'account_holder_name',
                'sheba_number'
            )
        }),
        ('پیگیری', {
            'fields': ('tracking_code', 'reference_number')
        }),
        ('یادداشت‌ها', {
            'fields': ('user_note', 'admin_note', 'rejection_reason')
        }),
        ('پردازش', {
            'fields': ('processed_by', 'payment'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'processed_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_withdrawals', 'reject_withdrawals', 'complete_withdrawals']
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{:,} تومان</small>',
            url, obj.user.username, obj.user.wallet_balance
        )
    user_link.short_description = 'کاربر'
    
    def amount_display(self, obj):
        if obj.fee > 0:
            return format_html(
                '<strong>{:,}</strong> تومان<br>'
                '<small style="color: red;">کارمزد: -{:,}</small><br>'
                '<small style="color: green;">خالص: {:,}</small>',
                obj.amount, obj.fee, obj.final_amount
            )
        return format_html('<strong>{:,}</strong> تومان', obj.amount)
    amount_display.short_description = 'مبلغ'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'processing': 'purple',
            'completed': 'green',
            'rejected': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def bank_info_short(self, obj):
        return format_html(
            'کارت: ****{}<br>{}',
            obj.bank_card_number[-4:] if obj.bank_card_number else '—',
            obj.account_holder_name
        )
    bank_info_short.short_description = 'اطلاعات بانکی'
    
    def approve_withdrawals(self, request, queryset):
        """Approve withdrawal requests"""
        success = 0
        errors = []
        
        for withdrawal in queryset.filter(status='pending'):
            try:
                withdrawal.approve(request.user)
                success += 1
            except Exception as e:
                errors.append(f'#{withdrawal.id}: {str(e)}')
        
        if success:
            self.message_user(request, f'{success} درخواست تایید شد.', messages.SUCCESS)
        if errors:
            self.message_user(request, 'خطاها: ' + ', '.join(errors), messages.ERROR)
    approve_withdrawals.short_description = 'تایید درخواست‌ها'
    
    def reject_withdrawals(self, request, queryset):
        """Reject withdrawal requests"""
        from django import forms
        from django.shortcuts import render, redirect
        
        class RejectForm(forms.Form):
            reason = forms.CharField(
                label='دلیل رد',
                widget=forms.Textarea,
                required=True
            )
        
        if 'apply' in request.POST:
            form = RejectForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                success = 0
                
                for withdrawal in queryset.filter(status='pending'):
                    try:
                        withdrawal.reject(request.user, reason)
                        success += 1
                    except:
                        pass
                
                self.message_user(request, f'{success} درخواست رد شد.')
                return redirect('..')
        else:
            form = RejectForm()
        
        return render(
            request,
            'admin/reject_withdrawal_form.html',
            {'form': form, 'withdrawals': queryset}
        )
    reject_withdrawals.short_description = 'رد درخواست‌ها'
    
    def complete_withdrawals(self, request, queryset):
        """Mark withdrawals as completed"""
        from django import forms
        from django.shortcuts import render, redirect
        
        class CompleteForm(forms.Form):
            reference_number = forms.CharField(
                label='شماره مرجع',
                required=False
            )
        
        if 'apply' in request.POST:
            form = CompleteForm(request.POST)
            if form.is_valid():
                reference = form.cleaned_data['reference_number']
                success = 0
                
                for withdrawal in queryset.filter(status__in=['approved', 'processing']):
                    try:
                        withdrawal.complete(reference)
                        success += 1
                    except:
                        pass
                
                self.message_user(request, f'{success} برداشت تکمیل شد.')
                return redirect('..')
        else:
            form = CompleteForm()
        
        return render(
            request,
            'admin/complete_withdrawal_form.html',
            {'form': form, 'withdrawals': queryset}
        )
    complete_withdrawals.short_description = 'تکمیل برداشت‌ها'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Transaction admin"""
    
    list_display = (
        'id', 'user_link', 'transaction_type_badge',
        'amount_display', 'balance_change',
        'payment_link', 'created_at'
    )
    
    list_filter = ('transaction_type', 'created_at')
    
    search_fields = (
        'user__username', 'user__email',
        'description'
    )
    
    readonly_fields = (
        'user', 'transaction_type', 'amount',
        'balance_before', 'balance_after',
        'description', 'payment', 'tournament',
        'created_at'
    )
    
    fieldsets = (
        ('اطلاعات', {
            'fields': (
                'user', 'transaction_type', 'amount'
            )
        }),
        ('موجودی', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('جزئیات', {
            'fields': ('description', 'payment', 'tournament')
        }),
        ('تاریخ', {
            'fields': ('created_at',)
        })
    )
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def transaction_type_badge(self, obj):
        color = 'green' if obj.transaction_type == 'credit' else 'red'
        icon = '↑' if obj.transaction_type == 'credit' else '↓'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = 'نوع'
    
    def amount_display(self, obj):
        color = 'green' if obj.transaction_type == 'credit' else 'red'
        sign = '+' if obj.transaction_type == 'credit' else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{:,} تومان</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'مبلغ'
    
    def balance_change(self, obj):
        return format_html(
            '{:,} → {:,}',
            obj.balance_before, obj.balance_after
        )
    balance_change.short_description = 'تغییر موجودی'
    
    def payment_link(self, obj):
        if obj.payment:
            url = reverse('admin:payments_payment_change', args=[obj.payment.id])
            return format_html('<a href="{}">مشاهده</a>', url)
        return '—'
    payment_link.short_description = 'پرداخت'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    """Payment gateway configuration admin"""
    
    list_display = (
        'gateway_display', 'active_badge',
        'amount_limits', 'fee_display',
        'priority'
    )
    
    list_filter = ('is_active', 'gateway')
    
    list_editable = ('priority',)
    
    fieldsets = (
        ('اطلاعات درگاه', {
            'fields': ('gateway', 'is_active', 'priority')
        }),
        ('احراز هویت', {
            'fields': ('merchant_id', 'api_key')
        }),
        ('محدودیت‌های مبلغ', {
            'fields': ('min_amount', 'max_amount')
        }),
        ('کارمزد', {
            'fields': ('fee_percentage', 'fixed_fee')
        }),
        ('URLها', {
            'fields': ('payment_url', 'verify_url', 'callback_url'),
            'classes': ('collapse',)
        }),
        ('تنظیمات اضافی', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def gateway_display(self, obj):
        return obj.get_gateway_display()
    gateway_display.short_description = 'درگاه'
    
    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ فعال</span>')
        return format_html('<span style="color: red;">✗ غیرفعال</span>')
    active_badge.short_description = 'وضعیت'
    
    def amount_limits(self, obj):
        return format_html(
            '{:,} - {:,} تومان',
            obj.min_amount, obj.max_amount
        )
    amount_limits.short_description = 'محدوده مبلغ'
    
    def fee_display(self, obj):
        parts = []
        if obj.fee_percentage > 0:
            parts.append(f'{obj.fee_percentage}%')
        if obj.fixed_fee > 0:
            parts.append(f'{obj.fixed_fee:,} تومان')
        return ' + '.join(parts) if parts else '—'
    fee_display.short_description = 'کارمزد'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Coupon admin"""
    
    list_display = (
        'code', 'discount_display', 'status_badge',
        'usage_info', 'validity_period',
        'created_at'
    )
    
    list_filter = ('status', 'discount_type', 'valid_from', 'valid_until')
    
    search_fields = ('code', 'description')
    
    filter_horizontal = ('tournaments', 'allowed_users')
    
    readonly_fields = ('current_uses', 'created_at', 'updated_at')
    
    fieldsets = (
        ('کد تخفیف', {
            'fields': ('code', 'status', 'description')
        }),
        ('تخفیف', {
            'fields': (
                'discount_type', 'discount_value',
                'max_discount', 'min_purchase'
            )
        }),
        ('محدودیت استفاده', {
            'fields': (
                'max_uses', 'max_uses_per_user',
                'current_uses'
            )
        }),
        ('اعتبار', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('محدودیت‌ها', {
            'fields': (
                'tournaments', 'allowed_users',
                'first_purchase_only'
            ),
            'classes': ('collapse',)
        }),
        ('مدیریت', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_coupons', 'deactivate_coupons']
    
    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return format_html('<strong>{}%</strong>', obj.discount_value)
        return format_html('<strong>{:,}</strong> تومان', obj.discount_value)
    discount_display.short_description = 'تخفیف'
    
    def status_badge(self, obj):
        colors = {'active': 'green', 'inactive': 'gray', 'expired': 'red'}
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def usage_info(self, obj):
        if obj.max_uses > 0:
            percentage = (obj.current_uses / obj.max_uses * 100)
            return format_html(
                '{} / {} ({:.0f}%)',
                obj.current_uses, obj.max_uses, percentage
            )
        return f'{obj.current_uses} / ∞'
    usage_info.short_description = 'استفاده'
    
    def validity_period(self, obj):
        now = timezone.now()
        if now < obj.valid_from:
            status = '⏳ شروع نشده'
            color = 'gray'
        elif obj.valid_from <= now <= obj.valid_until:
            status = '✓ معتبر'
            color = 'green'
        else:
            status = '✗ منقضی'
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, status
        )
    validity_period.short_description = 'اعتبار'
    
    def activate_coupons(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} کوپن فعال شد.')
    activate_coupons.short_description = 'فعال‌سازی'
    
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} کوپن غیرفعال شد.')
    deactivate_coupons.short_description = 'غیرفعال‌سازی'


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    """Coupon usage admin"""
    
    list_display = (
        'coupon', 'user_link', 'payment_link',
        'discount_display', 'used_at'
    )
    
    list_filter = ('used_at',)
    
    search_fields = (
        'coupon__code', 'user__username',
        'payment__transaction_id'
    )
    
    readonly_fields = (
        'coupon', 'user', 'payment',
        'discount_amount', 'used_at'
    )
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def payment_link(self, obj):
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">مشاهده</a>', url)
    payment_link.short_description = 'پرداخت'
    
    def discount_display(self, obj):
        return format_html(
            '<strong style="color: green;">{:,}</strong> تومان',
            obj.discount_amount
        )
    discount_display.short_description = 'تخفیف'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    """Payment log admin"""
    
    list_display = (
        'id', 'payment_link', 'action',
        'status', 'created_at'
    )
    
    list_filter = ('action', 'status', 'created_at')
    
    search_fields = (
        'payment__transaction_id', 'action',
        'error_message'
    )
    
    readonly_fields = (
        'payment', 'action', 'status',
        'request_data', 'response_data',
        'error_message', 'ip_address', 'created_at'
    )
    
    def payment_link(self, obj):
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">مشاهده</a>', url)
    payment_link.short_description = 'پرداخت'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False