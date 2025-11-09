from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from .models import User, UserStats


class UserStatsInline(admin.StackedInline):
    """Inline for user statistics"""
    model = UserStats
    can_delete = False
    verbose_name = 'آمار کاربر'
    verbose_name_plural = 'آمار کاربر'
    
    fields = (
        'tournaments_played', 'tournaments_won', 
        'total_matches', 'matches_won', 
        'win_rate', 'total_earnings', 'ranking'
    )
    readonly_fields = ('win_rate',)
    
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""
    
    list_display = (
        'username', 'email', 'phone_number', 
        'wallet_badge', 'clash_royale_tag',
        'verified_badge', 'tournaments_count',
        'created_at'
    )
    
    list_filter = (
        'is_verified', 'is_staff', 'is_active', 
        'date_joined', 'created_at'
    )
    
    search_fields = (
        'username', 'email', 'phone_number', 
        'first_name', 'last_name', 'clash_royale_tag'
    )
    
    readonly_fields = (
        'date_joined', 'last_login', 'created_at', 
        'updated_at', 'profile_preview', 'tournaments_info'
    )
    
    fieldsets = (
        ('اطلاعات کاربری', {
            'fields': ('username', 'password')
        }),
        ('اطلاعات شخصی', {
            'fields': (
                'first_name', 'last_name', 'email', 
                'phone_number', 'profile_picture', 'profile_preview'
            )
        }),
        ('اطلاعات بازی', {
            'fields': ('clash_royale_tag',)
        }),
        ('اطلاعات مالی', {
            'fields': ('wallet_balance',),
            'classes': ('collapse',)
        }),
        ('دسترسی‌ها', {
            'fields': (
                'is_verified', 'is_active', 
                'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': (
                'date_joined', 'last_login', 
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('آمار', {
            'fields': ('tournaments_info',),
            'classes': ('collapse',)
        })
    )
    
    add_fieldsets = (
        ('اطلاعات ضروری', {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2'
            ),
        }),
    )
    
    inlines = [UserStatsInline]
    
    actions = ['verify_users', 'add_bonus', 'reset_wallet']
    
    
    @admin.display(description="کیف پول", ordering="wallet_balance")
    def wallet_badge(self, obj):
        balance = obj.wallet_balance or 0
        color = "green" if balance > 0 else "red"
        try:
            balance_value = float(balance)
        except (ValueError, TypeError):
            balance_value = 0
        formatted_balance = f"{balance_value:,.0f}"  # عدد به رشته با جداکننده هزارگان
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{formatted_balance} تومان</span>')


    wallet_badge.short_description = 'موجودی کیف پول'
    wallet_badge.admin_order_field = 'wallet_balance'
    
    def verified_badge(self, obj):
        """Display verification status"""
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✓ تایید شده</span>'
            )
        return format_html(
            '<span style="color: red;">✗ تایید نشده</span>'
        )
    verified_badge.short_description = 'وضعیت تایید'
    verified_badge.admin_order_field = 'is_verified'
    
    def profile_preview(self, obj):
        """Show profile picture preview"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return '—'
    profile_preview.short_description = 'پیش‌نمایش عکس'
    
    def tournaments_count(self, obj):
        """Show tournaments count with link"""
        count = obj.tournament_participations.filter(status='confirmed').count()
        url = reverse('admin:tournaments_tournamentparticipant_changelist')
        return format_html(
            '<a href="{}?user__id__exact={}">{} تورنومنت</a>',
            url, obj.id, count
        )
    tournaments_count.short_description = 'تورنومنت‌ها'
    
    def tournaments_info(self, obj):
        """Display detailed tournament info"""
        if not hasattr(obj, 'stats'):
            return '—'
        
        stats = obj.stats
        return format_html(
            '''
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px;"><strong>تورنومنت‌های بازی شده:</strong></td>
                    <td style="padding: 5px;">{}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>تورنومنت‌های برنده شده:</strong></td>
                    <td style="padding: 5px;">{}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>مسابقات:</strong></td>
                    <td style="padding: 5px;">{} / {}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>درصد برد:</strong></td>
                    <td style="padding: 5px;">{:.1f}%</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>کل درآمد:</strong></td>
                    <td style="padding: 5px;">{:,} تومان</td>
                </tr>
            </table>
            ''',
            stats.tournaments_played,
            stats.tournaments_won,
            stats.matches_won,
            stats.total_matches,
            stats.win_rate,
            stats.total_earnings
        )
    tournaments_info.short_description = 'اطلاعات تورنومنت'
    
    def verify_users(self, request, queryset):
        """Bulk verify users"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} کاربر تایید شدند.')
    verify_users.short_description = 'تایید کاربران انتخاب شده'
    
    def add_bonus(self, request, queryset):
        """Add bonus to selected users"""
        from django import forms
        from django.shortcuts import render
        
        class BonusForm(forms.Form):
            amount = forms.DecimalField(label='مبلغ پاداش (تومان)', min_value=1000)
            reason = forms.CharField(label='دلیل', widget=forms.Textarea)
        
        if 'apply' in request.POST:
            form = BonusForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                reason = form.cleaned_data['reason']
                
                from apps.payments.models import Payment
                
                for user in queryset:
                    user.add_to_wallet(amount)
                    Payment.objects.create(
                        user=user,
                        payment_type='bonus',
                        amount=amount,
                        status='completed',
                        gateway='admin',
                        description=reason
                    )
                
                self.message_user(
                    request,
                    f'پاداش {amount:,} تومان به {queryset.count()} کاربر اضافه شد.'
                )
                return
        else:
            form = BonusForm()
        
        return render(
            request,
            'admin/bonus_form.html',
            {'form': form, 'users': queryset}
        )
    add_bonus.short_description = 'اضافه کردن پاداش'
    
    def reset_wallet(self, request, queryset):
        """Reset wallet balance to zero"""
        updated = queryset.update(wallet_balance=0)
        self.message_user(request, f'کیف پول {updated} کاربر صفر شد.')
    reset_wallet.short_description = 'صفر کردن کیف پول'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('stats').prefetch_related('tournament_participations')


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    """User statistics admin"""
    
    list_display = (
        'user_link', 'tournaments_played', 'tournaments_won',
        'win_rate_badge', 'total_earnings_display', 'ranking'
    )
    
    list_filter = ('ranking',)
    
    search_fields = ('user__username', 'user__email')
    
    readonly_fields = (
        'user', 'tournaments_played', 'tournaments_won',
        'total_matches', 'matches_won', 'total_earnings',
        'win_rate'
    )
    
    fieldsets = (
        ('کاربر', {
            'fields': ('user',)
        }),
        ('آمار تورنومنت', {
            'fields': ('tournaments_played', 'tournaments_won')
        }),
        ('آمار مسابقات', {
            'fields': ('total_matches', 'matches_won', 'win_rate')
        }),
        ('مالی', {
            'fields': ('total_earnings',)
        }),
        ('رتبه‌بندی', {
            'fields': ('ranking',)
        })
    )
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def win_rate_badge(self, obj):
        """Display win rate with color"""
        if obj.win_rate >= 70:
            color = 'green'
        elif obj.win_rate >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, obj.win_rate
        )
    win_rate_badge.short_description = 'درصد برد'
    win_rate_badge.admin_order_field = 'win_rate'
    
    def total_earnings_display(self, obj):
        """Display earnings"""
        return format_html('{:,} تومان', obj.total_earnings)
    total_earnings_display.short_description = 'کل درآمد'
    total_earnings_display.admin_order_field = 'total_earnings'
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False