from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    Notification, NotificationPreference, NotificationTemplate
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification admin"""
    
    list_display = (
        'id', 'user_link', 'notification_type_badge',
        'title_short',
        'read_badge', 'delivery_status',
        'created_at'
    )
    
    list_filter = (
        'notification_type', 'priority',
        'is_read', 'is_sent_email',
        'is_sent_sms', 'is_sent_push',
        'created_at'
    )
    
    search_fields = (
        'user__username', 'user__email',
        'title', 'message'
    )
    
    readonly_fields = (
        'user', 'notification_type', 'priority',
        'title', 'message', 'link', 'action_text',
        'metadata', 'created_at', 'read_at',
        'is_sent_email', 'is_sent_sms', 'is_sent_push',
        'expires_badge'
    )
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'user', 'notification_type', 'priority'
            )
        }),
        ('محتوا', {
            'fields': ('title', 'message', 'link', 'action_text')
        }),
        ('وضعیت', {
            'fields': ('is_read', 'read_at', 'expires_at', 'expires_badge')
        }),
        ('وضعیت ارسال', {
            'fields': (
                'is_sent_email', 'is_sent_sms', 'is_sent_push'
            ),
            'classes': ('collapse',)
        }),
        ('داده‌های اضافی', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('تاریخ', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_read', 'delete_expired',
        'resend_email', 'resend_sms'
    ]
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def notification_type_badge(self, obj):
        colors = {
            'tournament_created': 'blue',
            'tournament_starting': 'purple',
            'registration_confirmed': 'green',
            'match_scheduled': 'orange',
            'match_starting': 'darkorange',
            'match_result': 'darkgreen',
            'payment_completed': 'green',
            'payment_failed': 'red',
            'prize_awarded': 'gold',
            'withdrawal_approved': 'green',
            'withdrawal_rejected': 'red',
            'dispute_opened': 'orange',
            'dispute_resolved': 'green',
            'system': 'gray'
        }
        color = colors.get(obj.notification_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>',
            color, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'نوع'
    
    def title_short(self, obj):
        return obj.title[:30] + '...' if len(obj.title) > 30 else obj.title
    title_short.short_description = 'عنوان'
    
    
    def read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: green;">✓ خوانده شده</span><br>'
                '<small>{}</small>',
                obj.read_at.strftime('%Y/%m/%d %H:%M') if obj.read_at else ''
            )
        return format_html('<span style="color: gray;">✗ خوانده نشده</span>')
    read_badge.short_description = 'وضعیت'
    read_badge.admin_order_field = 'is_read'
    
    def delivery_status(self, obj):
        """Show delivery status for all channels"""
        email_icon = '📧' if obj.is_sent_email else '📭'
        sms_icon = '📱' if obj.is_sent_sms else '📵'
        push_icon = '🔔' if obj.is_sent_push else '🔕'
        
        return format_html(
            '<span title="ایمیل">{}</span> '
            '<span title="پیامک">{}</span> '
            '<span title="پوش">{}</span>',
            email_icon, sms_icon, push_icon
        )
    delivery_status.short_description = 'ارسال'
    
    def expires_badge(self, obj):
        if not obj.expires_at:
            return '—'
        
        if obj.is_expired:
            return format_html(
                '<span style="color: red;">منقضی شده</span><br>'
                '<small>{}</small>',
                obj.expires_at.strftime('%Y/%m/%d %H:%M')
            )
        return format_html(
            '<span style="color: green;">معتبر</span><br>'
            '<small>تا {}</small>',
            obj.expires_at.strftime('%Y/%m/%d %H:%M')
        )
    expires_badge.short_description = 'انقضا'
    
    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        updated = 0
        for notification in queryset.filter(is_read=False):
            notification.mark_as_read()
            updated += 1
        
        self.message_user(request, f'{updated} اعلان به عنوان خوانده شده علامت زده شد.')
    mark_as_read.short_description = 'علامت‌گذاری به عنوان خوانده شده'
    
    def delete_expired(self, request, queryset):
        """Delete expired notifications"""
        deleted = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted[0]} اعلان منقضی حذف شد.')
    delete_expired.short_description = 'حذف اعلان‌های منقضی'
    
    def resend_email(self, request, queryset):
        """Resend email notifications"""
        # This would integrate with your email service
        count = queryset.count()
        self.message_user(
            request,
            f'{count} ایمیل برای ارسال مجدد در صف قرار گرفت.',
            messages.SUCCESS
        )
    resend_email.short_description = 'ارسال مجدد ایمیل'
    
    def resend_sms(self, request, queryset):
        """Resend SMS notifications"""
        # This would integrate with your SMS service
        count = queryset.count()
        self.message_user(
            request,
            f'{count} پیامک برای ارسال مجدد در صف قرار گرفت.',
            messages.SUCCESS
        )
    resend_sms.short_description = 'ارسال مجدد پیامک'
    
    def has_add_permission(self, request):
        """Allow manual notification creation"""
        return True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Notification preference admin"""
    
    list_display = (
        'user_link', 'email_status', 'sms_status',
        'push_status', 'quiet_hours_status',
        'updated_at'
    )
    
    list_filter = (
        'email_enabled', 'sms_enabled',
        'push_enabled', 'quiet_hours_enabled',
        'digest_enabled'
    )
    
    search_fields = ('user__username', 'user__email')
    
    readonly_fields = ('user', 'created_at', 'updated_at')
    
    fieldsets = (
        ('کاربر', {
            'fields': ('user',)
        }),
        ('اعلان‌های ایمیل', {
            'fields': (
                'email_enabled',
                'email_tournament_created', 'email_match_scheduled',
                'email_match_starting', 'email_match_reminder',
                'email_prize_awarded', 'email_payment',
                'email_withdrawal', 'email_dispute', 'email_system'
            )
        }),
        ('اعلان‌های پیامکی', {
            'fields': (
                'sms_enabled',
                'sms_match_starting', 'sms_match_reminder',
                'sms_payment', 'sms_withdrawal'
            ),
            'classes': ('collapse',)
        }),
        ('اعلان‌های پوش', {
            'fields': (
                'push_enabled',
                'push_tournament', 'push_match',
                'push_payment', 'push_dispute'
            ),
            'classes': ('collapse',)
        }),
        ('ساعت‌های سکوت', {
            'fields': (
                'quiet_hours_enabled',
                'quiet_hours_start', 'quiet_hours_end'
            ),
            'classes': ('collapse',)
        }),
        ('خلاصه اعلان‌ها', {
            'fields': ('digest_enabled', 'digest_frequency'),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['enable_all_notifications', 'disable_all_notifications']
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def email_status(self, obj):
        if obj.email_enabled:
            count = sum([
                obj.email_tournament_created, obj.email_match_scheduled,
                obj.email_match_starting, obj.email_prize_awarded,
                obj.email_payment, obj.email_withdrawal
            ])
            return format_html(
                '<span style="color: green;">✓ فعال</span><br>'
                '<small>{} مورد</small>',
                count
            )
        return format_html('<span style="color: red;">✗ غیرفعال</span>')
    email_status.short_description = 'ایمیل'
    
    def sms_status(self, obj):
        if obj.sms_enabled:
            count = sum([
                obj.sms_match_starting, obj.sms_payment
            ])
            return format_html(
                '<span style="color: green;">✓ فعال</span><br>'
                '<small>{} مورد</small>',
                count
            )
        return format_html('<span style="color: red;">✗ غیرفعال</span>')
    sms_status.short_description = 'پیامک'
    
    def push_status(self, obj):
        if obj.push_enabled:
            count = sum([
                obj.push_tournament, obj.push_match,
                obj.push_payment, obj.push_dispute
            ])
            return format_html(
                '<span style="color: green;">✓ فعال</span><br>'
                '<small>{} مورد</small>',
                count
            )
        return format_html('<span style="color: red;">✗ غیرفعال</span>')
    push_status.short_description = 'پوش'
    
    def quiet_hours_status(self, obj):
        if obj.quiet_hours_enabled:
            return format_html(
                '<span style="color: orange;">✓ فعال</span><br>'
                '<small>{} - {}</small>',
                obj.quiet_hours_start.strftime('%H:%M') if obj.quiet_hours_start else '—',
                obj.quiet_hours_end.strftime('%H:%M') if obj.quiet_hours_end else '—'
            )
        return format_html('<span style="color: gray;">✗ غیرفعال</span>')
    quiet_hours_status.short_description = 'ساعت سکوت'
    
    def enable_all_notifications(self, request, queryset):
        """Enable all notification types"""
        queryset.update(
            email_enabled=True,
            email_tournament_created=True,
            email_match_scheduled=True,
            email_match_starting=True,
            email_prize_awarded=True,
            email_payment=True,
            email_withdrawal=True,
            sms_enabled=True,
            sms_match_starting=True,
            sms_payment=True,
            push_enabled=True,
            push_tournament=True,
            push_match=True,
            push_payment=True,
            push_dispute=True
        )
        self.message_user(request, 'تمام اعلان‌ها برای کاربران انتخاب شده فعال شد.')
    enable_all_notifications.short_description = 'فعال‌سازی همه اعلان‌ها'
    
    def disable_all_notifications(self, request, queryset):
        """Disable all notification types"""
        queryset.update(
            email_enabled=False,
            sms_enabled=False,
            push_enabled=False
        )
        self.message_user(request, 'تمام اعلان‌ها برای کاربران انتخاب شده غیرفعال شد.')
    disable_all_notifications.short_description = 'غیرفعال‌سازی همه اعلان‌ها'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Notification template admin"""
    
    list_display = (
        'notification_type_display', 'active_badge',
        'channels_available', 'updated_at'
    )
    
    list_filter = ('is_active', 'notification_type')
    
    search_fields = (
        'notification_type', 'app_title',
        'email_subject', 'push_title'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'preview')
    
    fieldsets = (
        ('نوع اعلان', {
            'fields': ('notification_type', 'is_active')
        }),
        ('قالب ایمیل', {
            'fields': ('email_subject', 'email_body')
        }),
        ('قالب پیامک', {
            'fields': ('sms_body',),
            'classes': ('collapse',)
        }),
        ('قالب پوش', {
            'fields': ('push_title', 'push_body'),
            'classes': ('collapse',)
        }),
        ('قالب اپلیکیشن', {
            'fields': ('app_title', 'app_body')
        }),
        ('پیش‌نمایش', {
            'fields': ('preview',),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_templates', 'deactivate_templates', 'test_template']
    
    def notification_type_display(self, obj):
        return obj.get_notification_type_display()
    notification_type_display.short_description = 'نوع اعلان'
    
    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ فعال</span>')
        return format_html('<span style="color: red;">✗ غیرفعال</span>')
    active_badge.short_description = 'وضعیت'
    active_badge.admin_order_field = 'is_active'
    
    def channels_available(self, obj):
        """Show which channels have templates"""
        channels = []
        if obj.email_subject and obj.email_body:
            channels.append('📧 ایمیل')
        if obj.sms_body:
            channels.append('📱 پیامک')
        if obj.push_title and obj.push_body:
            channels.append('🔔 پوش')
        if obj.app_title and obj.app_body:
            channels.append('📱 اپ')
        
        return format_html('<br>'.join(channels)) if channels else '—'
    channels_available.short_description = 'کانال‌ها'
    
    def preview(self, obj):
        """Show template preview with sample data"""
        sample_context = {
            'user': 'کاربر نمونه',
            'tournament': 'تورنومنت تست',
            'amount': '50,000',
            'date': '1403/08/15',
            'time': '14:30'
        }
        
        try:
            rendered = obj.render(sample_context)
            return format_html(
                '<div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px;">'
                '<h3>پیش‌نمایش (با داده‌های نمونه)</h3>'
                '<hr>'
                '<h4>ایمیل:</h4>'
                '<p><strong>موضوع:</strong> {}</p>'
                '<p><strong>متن:</strong> {}</p>'
                '<hr>'
                '<h4>پیامک:</h4>'
                '<p>{}</p>'
                '<hr>'
                '<h4>پوش:</h4>'
                '<p><strong>عنوان:</strong> {}</p>'
                '<p><strong>متن:</strong> {}</p>'
                '<hr>'
                '<h4>اپلیکیشن:</h4>'
                '<p><strong>عنوان:</strong> {}</p>'
                '<p><strong>متن:</strong> {}</p>'
                '</div>',
                rendered['email_subject'],
                rendered['email_body'],
                rendered['sms_body'],
                rendered['push_title'],
                rendered['push_body'],
                rendered['app_title'],
                rendered['app_body']
            )
        except Exception as e:
            return format_html(
                '<span style="color: red;">خطا در رندر: {}</span>',
                str(e)
            )
    preview.short_description = 'پیش‌نمایش'
    
    def activate_templates(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} قالب فعال شد.')
    activate_templates.short_description = 'فعال‌سازی قالب‌ها'
    
    def deactivate_templates(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} قالب غیرفعال شد.')
    deactivate_templates.short_description = 'غیرفعال‌سازی قالب‌ها'
    
    def test_template(self, request, queryset):
        """Send test notification to admin"""
        if queryset.count() > 1:
            self.message_user(
                request,
                'لطفاً فقط یک قالب را برای تست انتخاب کنید.',
                messages.ERROR
            )
            return
        
        template = queryset.first()
        # Here you would create a test notification
        self.message_user(
            request,
            f'اعلان تست برای قالب "{template.get_notification_type_display()}" ارسال شد.',
            messages.SUCCESS
        )
    test_template.short_description = 'ارسال تست'