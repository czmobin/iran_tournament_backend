from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from .models import (
    Tournament, TournamentParticipant, 
    TournamentInvitation
)


class TournamentParticipantInline(admin.TabularInline):
    """Inline for tournament participants"""
    model = TournamentParticipant
    extra = 0
    
    fields = (
        'user', 'status', 
        'placement', 'prize_won', 'joined_at'
    )
    readonly_fields = ('joined_at', 'prize_won')
    
    autocomplete_fields = ['user']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    """Tournament admin"""
    
    list_display = (
        'title', 'status_badge', 'game_mode',
        'participants_info', 'prize_pool_display',
        'registration_period', 'featured_badge',
        'created_at'
    )
    
    list_filter = (
        'status', 'game_mode', 'pricable',
        'is_featured', 'created_at',
        'start_date', 'level_cap'
    )
    
    search_fields = (
        'title', 'slug', 'description',
        'created_by__username'
    )
    
    readonly_fields = (
        'slug', 'total_participants', 'total_matches',
        'created_at', 'updated_at',
        'banner_preview'
    )
    
    # حذف autocomplete_fields چون created_by رو readonly کردیم
    # autocomplete_fields = ['created_by']
        
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'title', 'slug', 'description',
                'banner', 'banner_preview'
            )
        }),
        ('تنظیمات تورنومنت', {
            'fields': (
                'game_mode', 'pricable',
                'max_participants',
                'best_of',
                'level_cap',
                'max_losses',
                'time_duration'
            )
        }),
        ('تنظیمات مالی', {
            'fields': (
                'entry_fee', 'prize_pool',
                'platform_commission'
            )
        }),
        ('تاریخ‌ها', {
            'fields': (
                'registration_start', 'registration_end',
                'start_date', 'end_date'
            )
        }),
        ('قوانین', {
            'fields': ('rules',),
            'classes': ('collapse',)
        }),
        ('تنظیمات اضافی', {
            'fields': ('is_featured',),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('status',)
        }),
        ('مدیریت', {
            'fields': ('created_by',)
        }),
        ('آمار', {
            'fields': (
                'total_participants', 'total_matches'
            ),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [TournamentParticipantInline]
    
    actions = [
        'activate_registration', 'start_tournaments',
        'finish_tournaments', 'cancel_tournaments',
        'make_featured'
    ]
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by on create"""
        if not change:  # فقط موقع ساخت
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def status_badge(self, obj):
        """Display status with color"""
        colors = {
            'draft': 'gray',
            'pending': 'blue',
            'registration': 'orange',
            'ready': 'purple',
            'ongoing': 'green',
            'finished': 'darkgreen',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'
    
    def participants_info(self, obj):
        """Display participants count"""
        current = obj.current_participants_count
        maximum = obj.max_participants
        percentage = (current / maximum * 100) if maximum > 0 else 0
        
        color = 'green' if percentage >= 50 else 'orange' if percentage >= 25 else 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / {}</span>',
            color, current, maximum
        )
    participants_info.short_description = 'شرکت‌کننده'
    
    def prize_pool_display(self, obj):
        """Display prize pool"""
        # فرمت با جداکننده فارسی
        formatted = f'{int(obj.prize_pool):,}'.replace(',', '،')
        return format_html(
            '<strong style="color: green;">{} تومان</strong>',
            formatted
        )
    prize_pool_display.short_description = 'جایزه کل'
    prize_pool_display.admin_order_field = 'prize_pool'
    
    def registration_period(self, obj):
        """Display registration period"""
        now = timezone.now()
        
        if obj.registration_start > now:
            status = '⏳ شروع نشده'
            color = 'gray'
        elif obj.registration_start <= now <= obj.registration_end:
            status = '✓ باز'
            color = 'green'
        else:
            status = '✗ بسته'
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{}</span><br>'
            '<small>{} تا {}</small>',
            color, status,
            obj.registration_start.strftime('%Y/%m/%d %H:%M'),
            obj.registration_end.strftime('%Y/%m/%d %H:%M')
        )
    registration_period.short_description = 'ثبت‌نام'
    
    def featured_badge(self, obj):
        """Display featured status"""
        if obj.is_featured:
            return format_html(
                '<span style="color: gold; font-size: 16px;">⭐</span>'
            )
        return '—'
    featured_badge.short_description = 'ویژه'
    featured_badge.admin_order_field = 'is_featured'
    
    def banner_preview(self, obj):
        """Show banner preview"""
        if obj.banner:
            return format_html(
                '<img src="{}" width="300" style="border-radius: 5px;" />',
                obj.banner.url
            )
        return '—'
    banner_preview.short_description = 'پیش‌نمایش بنر'
        
    def activate_registration(self, request, queryset):
        """Start registration for selected tournaments"""
        updated = queryset.filter(status='pending').update(status='registration')
        self.message_user(request, f'ثبت‌نام {updated} تورنومنت فعال شد.')
    activate_registration.short_description = 'فعال‌سازی ثبت‌نام'
    
    def start_tournaments(self, request, queryset):
        """Start selected tournaments"""
        success = 0
        errors = []
        
        for tournament in queryset.filter(status='ready'):
            try:
                tournament.start_tournament()
                success += 1
            except Exception as e:
                errors.append(f'{tournament.title}: {str(e)}')
        
        if success:
            self.message_user(request, f'{success} تورنومنت شروع شد.', messages.SUCCESS)
        if errors:
            self.message_user(request, 'خطاها: ' + ', '.join(errors), messages.ERROR)
    start_tournaments.short_description = 'شروع تورنومنت‌ها'
    
    def finish_tournaments(self, request, queryset):
        """Finish selected tournaments"""
        success = 0
        errors = []
        
        for tournament in queryset.filter(status='ongoing'):
            try:
                tournament.finish_tournament()
                success += 1
            except Exception as e:
                errors.append(f'{tournament.title}: {str(e)}')
        
        if success:
            self.message_user(request, f'{success} تورنومنت پایان یافت.', messages.SUCCESS)
        if errors:
            self.message_user(request, 'خطاها: ' + ', '.join(errors), messages.ERROR)
    finish_tournaments.short_description = 'پایان تورنومنت‌ها'
    
    def cancel_tournaments(self, request, queryset):
        """Cancel selected tournaments"""
        from django import forms
        
        class CancelForm(forms.Form):
            reason = forms.CharField(
                label='دلیل لغو',
                widget=forms.Textarea,
                required=True
            )
        
        if 'apply' in request.POST:
            form = CancelForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                success = 0
                
                for tournament in queryset:
                    try:
                        tournament.cancel_tournament(reason)
                        success += 1
                    except:
                        pass
                
                self.message_user(
                    request,
                    f'{success} تورنومنت لغو شد و هزینه ورودی بازگشت داده شد.'
                )
                return redirect('..')
        else:
            form = CancelForm()
        
        return render(
            request,
            'admin/cancel_tournament_form.html',
            {'form': form, 'tournaments': queryset}
        )
    cancel_tournaments.short_description = 'لغو تورنومنت‌ها'
    
    def make_featured(self, request, queryset):
        """Make tournaments featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} تورنومنت ویژه شدند.')
    make_featured.short_description = 'تبدیل به ویژه'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('created_by').prefetch_related('participants')


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    """Tournament participant admin"""
    
    list_display = (
        'tournament_link', 'user_link', 'status_badge',
        'placement_badge',
        'prize_display', 'joined_at'
    )
    
    list_filter = (
        'status', 'placement',
        'joined_at'
    )
    
    search_fields = (
        'tournament__title', 'user__username',
        'user__email'
    )
    
    readonly_fields = (
        'tournament', 'user', 'joined_at',
        'matches_played', 'matches_won'
    )
    
    autocomplete_fields = ['user', 'tournament']
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('tournament', 'user', 'status')
        }),
        ('نتایج', {
            'fields': (
                'placement', 'prize_won',
                'matches_played', 'matches_won'
            )
        }),
        ('محرومیت', {
            'fields': ('disqualification_reason',),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['confirm_participants', 'disqualify_participants']
    
    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنومنت'
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'کاربر'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'green',
            'cancelled': 'red',
            'disqualified': 'darkred'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def placement_badge(self, obj):
        if obj.placement:
            medals = {1: '🥇', 2: '🥈', 3: '🥉'}
            medal = medals.get(obj.placement, '🏅')
            return format_html('{} مقام {}', medal, obj.placement)
        return '—'
    placement_badge.short_description = 'رتبه'
    placement_badge.admin_order_field = 'placement'
    
    def prize_display(self, obj):
        if obj.prize_won > 0:
            formatted = f'{int(obj.prize_won):,}'.replace(',', '،')
            return format_html(
                '<strong style="color: green;">{} تومان</strong>',
                formatted
            )
        return '—'
    prize_display.short_description = 'جایزه'
    prize_display.admin_order_field = 'prize_won'
    
    def confirm_participants(self, request, queryset):
        success = 0
        for participant in queryset.filter(status='pending'):
            try:
                participant.confirm_registration()
                success += 1
            except:
                pass
        self.message_user(request, f'{success} شرکت‌کننده تایید شد.')
    confirm_participants.short_description = 'تایید شرکت‌کنندگان'

    def disqualify_participants(self, request, queryset):
        from django import forms
        
        class DisqualifyForm(forms.Form):
            reason = forms.CharField(
                label='دلیل محرومیت',
                widget=forms.Textarea,
                required=True
            )
        
        if 'apply' in request.POST:
            form = DisqualifyForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                success = 0
                
                for participant in queryset:
                    try:
                        participant.disqualify(reason)
                        success += 1
                    except:
                        pass
                
                self.message_user(request, f'{success} شرکت‌کننده محروم شدند.')
                return redirect('..')
        else:
            form = DisqualifyForm()
        
        return render(
            request,
            'admin/disqualify_form.html',
            {'form': form, 'participants': queryset}
        )
    disqualify_participants.short_description = 'محروم کردن شرکت‌کنندگان'


@admin.register(TournamentInvitation)
class TournamentInvitationAdmin(admin.ModelAdmin):
    """Tournament invitation admin"""
    
    list_display = (
        'tournament_link', 'invited_user_link',
        'invited_by_link', 'status_badge',
        'expires_badge', 'created_at'
    )
    
    list_filter = ('status', 'created_at', 'expires_at')
    
    search_fields = (
        'tournament__title', 'invited_user__username',
        'invited_by__username', 'code'
    )
    
    readonly_fields = ('code', 'created_at', 'responded_at')
    
    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنومنت'
    
    def invited_user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.invited_user.id])
        return format_html('<a href="{}">{}</a>', url, obj.invited_user.username)
    invited_user_link.short_description = 'دعوت شده'
    
    def invited_by_link(self, obj):
        if obj.invited_by:
            url = reverse('admin:accounts_user_change', args=[obj.invited_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.invited_by.username)
        return '—'
    invited_by_link.short_description = 'دعوت کننده'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'declined': 'red',
            'expired': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    
    def expires_badge(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">منقضی شده</span>')
        return format_html('<span style="color: green;">معتبر</span>')
    expires_badge.short_description = 'اعتبار'