from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from .models import (
    Tournament, TournamentParticipant,
    TournamentInvitation, PlayerBattleLog,
    TournamentRanking, TournamentChat
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
        'banner_preview', 'last_battle_sync_time',
        'tracking_started_at', 'auto_tracking_enabled',
        'calculated_prize_pool', 'calculated_prize_after_commission',
        'calculated_prize_distribution'
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
                'platform_commission',
                'calculated_prize_pool',
                'calculated_prize_after_commission',
                'calculated_prize_distribution'
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
        ('اتصال به Clash Royale', {
            'fields': (
                'clash_royale_tournament_tag',
                'tournament_password',
                'auto_tracking_enabled',
                'last_battle_sync_time',
                'tracking_started_at'
            ),
            'classes': ('collapse',),
            'description': 'تنظیمات اتصال به تورنمنت Clash Royale'
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
    
    def calculated_prize_pool(self, obj):
        """Display calculated total prize pool"""
        # محاسبه اولیه اگر مقادیر موجود باشند
        if obj and obj.entry_fee and obj.max_participants:
            total = obj.entry_fee * obj.max_participants
            formatted = f'{int(total):,}'.replace(',', '،')
        else:
            formatted = '—'

        return format_html(
            '<div id="calc_prize_pool" style="background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 2px solid #4caf50;">'
            '<strong style="color: #2e7d32; font-size: 16px;">💰 <span id="prize_pool_value">{}</span> تومان</strong>'
            '<br><small style="color: #666;">جایزه کل محاسبه شده (به‌روزرسانی خودکار)</small>'
            '</div>',
            formatted
        )
    calculated_prize_pool.short_description = 'جایزه کل محاسبه شده'

    def calculated_prize_after_commission(self, obj):
        """Display prize pool after platform commission"""
        # محاسبه اولیه اگر مقادیر موجود باشند
        if obj and obj.entry_fee and obj.max_participants and obj.platform_commission is not None:
            total = obj.entry_fee * obj.max_participants
            commission_amount = (total * obj.platform_commission) / 100
            after_commission = total - commission_amount
            formatted_total = f'{int(after_commission):,}'.replace(',', '،')
            formatted_commission = f'{int(commission_amount):,}'.replace(',', '،')
        else:
            formatted_total = '—'
            formatted_commission = '—'

        return format_html(
            '<div id="calc_after_commission" style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; border: 2px solid #2196f3;">'
            '<strong style="color: #1565c0; font-size: 16px;">💵 <span id="after_commission_value">{}</span> تومان</strong>'
            '<br><small style="color: #666;">پس از کسر کمیسیون (<span id="commission_value">{}</span> تومان)</small>'
            '</div>',
            formatted_total, formatted_commission
        )
    calculated_prize_after_commission.short_description = 'جایزه پس از کمیسیون'

    def calculated_prize_distribution(self, obj):
        """Display prize distribution for top players"""
        # همیشه container را نمایش بده تا JavaScript بتواند update کند
        html = '<div id="calc_distribution" style="background-color: #fff3e0; padding: 10px; border-radius: 5px; border: 2px solid #ff9800;">'
        html += '<strong style="color: #e65100; font-size: 14px;">🏆 توزیع جوایز نفرات برتر:</strong><br><br>'
        html += '<div id="distribution_items">'

        # محاسبه اولیه اگر مقادیر موجود باشند
        if obj and obj.entry_fee and obj.max_participants and obj.platform_commission is not None and obj.best_of:
            total = obj.entry_fee * obj.max_participants
            after_commission = total - (total * obj.platform_commission / 100)

            # Prize distribution percentages based on best_of
            distributions = {
                1: [(1, 100)],
                2: [(1, 60), (2, 40)],
                3: [(1, 50), (2, 30), (3, 20)],
                4: [(1, 40), (2, 30), (3, 20), (4, 10)],
                5: [(1, 40), (2, 25), (3, 15), (4, 12), (5, 8)],
                6: [(1, 35), (2, 25), (3, 15), (4, 12), (5, 8), (6, 5)],
                7: [(1, 35), (2, 22), (3, 15), (4, 11), (5, 8), (6, 5), (7, 4)],
                8: [(1, 35), (2, 20), (3, 13), (4, 10), (5, 8), (6, 6), (7, 4), (8, 4)],
            }

            # Default distribution for more than 8
            if obj.best_of > 8:
                distributions[obj.best_of] = [(i, 100/obj.best_of) for i in range(1, obj.best_of + 1)]

            distribution = distributions.get(obj.best_of, distributions[8])
            medals = {1: '🥇', 2: '🥈', 3: '🥉'}

            for rank, percentage in distribution:
                prize_amount = (after_commission * percentage) / 100
                formatted_prize = f'{int(prize_amount):,}'.replace(',', '،')
                medal = medals.get(rank, '🏅')

                html += format_html(
                    '<div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">'
                    '<strong>{} نفر {}: </strong>'
                    '<span style="color: #2e7d32; font-weight: bold;">{} تومان</span> '
                    '<small style="color: #666;">({}%)</small>'
                    '</div>',
                    medal, rank, formatted_prize, int(percentage)
                )
        else:
            html += '<em style="color: #999;">لطفاً ابتدا فیلدهای ورودی، تعداد شرکت‌کننده، کمیسیون و نفرات برتر را وارد کنید</em>'

        html += '</div></div>'
        return format_html(html)
    calculated_prize_distribution.short_description = 'توزیع جوایز'

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
    
    def get_readonly_fields(self, request, obj=None):
        """
        همیشه فیلدهای محاسبه شده را نمایش بده
        حتی در حالت create
        """
        readonly = list(super().get_readonly_fields(request, obj))
        # اطمینان از اینکه فیلدهای محاسبه شده همیشه موجود هستند
        calc_fields = ['calculated_prize_pool', 'calculated_prize_after_commission', 'calculated_prize_distribution']
        for field in calc_fields:
            if field not in readonly:
                readonly.append(field)
        return readonly

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('created_by').prefetch_related('participants')

    class Media:
        js = ('admin/js/tournament_prize_calculator.js',)
        css = {
            'all': ('admin/css/tournament_admin.css',)
        }


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


@admin.register(PlayerBattleLog)
class PlayerBattleLogAdmin(admin.ModelAdmin):
    """Player battle log admin"""

    list_display = (
        'battle_id', 'player_name', 'opponent_name',
        'result_badge', 'crowns_display', 'tournament_link',
        'battle_time'
    )

    list_filter = (
        'battle_type', 'is_winner', 'is_draw',
        'is_counted', 'battle_time', 'tournament'
    )

    search_fields = (
        'player_name', 'player_tag',
        'opponent_name', 'opponent_tag',
        'tournament__title'
    )

    readonly_fields = (
        'tournament', 'participant', 'battle_time',
        'battle_type', 'game_mode', 'player_tag',
        'player_name', 'player_crowns', 'opponent_tag',
        'opponent_name', 'opponent_crowns', 'is_winner',
        'is_draw', 'arena_name', 'created_at',
        'player_cards', 'opponent_cards', 'raw_battle_data'
    )

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'tournament', 'participant',
                'battle_time', 'battle_type', 'game_mode'
            )
        }),
        ('بازیکن', {
            'fields': (
                'player_tag', 'player_name', 'player_crowns',
                'player_king_tower_hp', 'player_princess_towers_hp',
                'player_cards'
            )
        }),
        ('حریف', {
            'fields': (
                'opponent_tag', 'opponent_name', 'opponent_crowns',
                'opponent_king_tower_hp', 'opponent_princess_towers_hp',
                'opponent_cards'
            )
        }),
        ('نتیجه', {
            'fields': ('is_winner', 'is_draw', 'is_counted')
        }),
        ('آرنا', {
            'fields': ('arena_name', 'arena_id'),
            'classes': ('collapse',)
        }),
        ('داده خام', {
            'fields': ('raw_battle_data',),
            'classes': ('collapse',)
        }),
        ('تاریخچه', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def battle_id(self, obj):
        return f"#{obj.id}"
    battle_id.short_description = 'شناسه'

    def result_badge(self, obj):
        if obj.is_winner:
            return format_html(
                '<span style="background-color: green; color: white; '
                'padding: 2px 8px; border-radius: 3px;">✓ برد</span>'
            )
        elif obj.is_draw:
            return format_html(
                '<span style="background-color: gray; color: white; '
                'padding: 2px 8px; border-radius: 3px;">= مساوی</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; '
                'padding: 2px 8px; border-radius: 3px;">✗ باخت</span>'
            )
    result_badge.short_description = 'نتیجه'
    result_badge.admin_order_field = 'is_winner'

    def crowns_display(self, obj):
        return format_html(
            '<strong>{}</strong> - <strong>{}</strong>',
            obj.player_crowns, obj.opponent_crowns
        )
    crowns_display.short_description = 'تاج‌ها'

    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنمنت'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('tournament', 'participant__user')


@admin.register(TournamentRanking)
class TournamentRankingAdmin(admin.ModelAdmin):
    """Tournament ranking admin"""

    list_display = (
        'rank_badge', 'user_link', 'tournament_link',
        'score_display', 'stats_display', 'win_rate_badge',
        'calculated_at'
    )

    list_filter = (
        'tournament', 'rank', 'calculated_at'
    )

    search_fields = (
        'participant__user__username',
        'tournament__title'
    )

    readonly_fields = (
        'tournament', 'participant', 'rank',
        'total_battles', 'total_wins', 'total_losses',
        'total_draws', 'total_crowns', 'total_crowns_lost',
        'win_rate', 'score', 'last_battle_time',
        'calculated_at'
    )

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('tournament', 'participant', 'rank', 'score')
        }),
        ('آمار بازی', {
            'fields': (
                'total_battles', 'total_wins',
                'total_losses', 'total_draws',
                'win_rate'
            )
        }),
        ('آمار تاج', {
            'fields': ('total_crowns', 'total_crowns_lost')
        }),
        ('تاریخچه', {
            'fields': ('last_battle_time', 'calculated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['recalculate_rankings']

    def rank_badge(self, obj):
        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        medal = medals.get(obj.rank, '🏅')
        return format_html(
            '<strong style="font-size: 16px;">{} #{}</strong>',
            medal, obj.rank
        )
    rank_badge.short_description = 'رتبه'
    rank_badge.admin_order_field = 'rank'

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.participant.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.participant.user.username
        )
    user_link.short_description = 'کاربر'

    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنمنت'

    def score_display(self, obj):
        return format_html(
            '<strong style="color: #0066cc; font-size: 14px;">{} امتیاز</strong>',
            obj.score
        )
    score_display.short_description = 'امتیاز'
    score_display.admin_order_field = 'score'

    def stats_display(self, obj):
        return format_html(
            '<strong style="color: green;">{}</strong>W / '
            '<strong style="color: red;">{}</strong>L / '
            '<strong style="color: gray;">{}</strong>D',
            obj.total_wins, obj.total_losses, obj.total_draws
        )
    stats_display.short_description = 'بازی‌ها'

    def win_rate_badge(self, obj):
        wr = float(obj.win_rate)
        if wr >= 70:
            color = 'green'
        elif wr >= 50:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, round(wr, 1)
        )
    win_rate_badge.short_description = 'درصد برد'
    win_rate_badge.admin_order_field = 'win_rate'

    def recalculate_rankings(self, request, queryset):
        """Recalculate rankings for selected entries"""
        from .tasks import calculate_tournament_rankings

        tournaments = set(queryset.values_list('tournament_id', flat=True))

        for tournament_id in tournaments:
            calculate_tournament_rankings.delay(tournament_id)

        self.message_user(
            request,
            f'محاسبه مجدد رتبه‌بندی برای {len(tournaments)} تورنمنت در صف قرار گرفت.',
            messages.SUCCESS
        )
    recalculate_rankings.short_description = 'محاسبه مجدد رتبه‌بندی'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('tournament', 'participant__user')


@admin.register(TournamentChat)
class TournamentChatAdmin(admin.ModelAdmin):
    """Tournament chat messages admin"""

    list_display = (
        'id', 'tournament_link', 'sender_link', 'message_preview',
        'reply_indicator', 'deleted_indicator', 'created_at'
    )

    list_filter = (
        'tournament', 'is_deleted', 'created_at'
    )

    search_fields = (
        'message', 'sender__username', 'tournament__title'
    )

    readonly_fields = (
        'sender', 'tournament', 'created_at', 'updated_at',
        'deleted_by', 'deleted_at'
    )

    fieldsets = (
        ('اطلاعات پیام', {
            'fields': ('tournament', 'sender', 'message', 'reply_to')
        }),
        ('وضعیت', {
            'fields': ('is_deleted', 'deleted_by', 'deleted_at')
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['soft_delete_messages', 'restore_messages']

    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنمنت'

    def sender_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = 'فرستنده'

    def message_preview(self, obj):
        if obj.is_deleted:
            return format_html(
                '<span style="color: #999; text-decoration: line-through;">{}</span>',
                obj.message[:100]
            )
        return obj.message[:100] + ('...' if len(obj.message) > 100 else '')
    message_preview.short_description = 'پیام'

    def reply_indicator(self, obj):
        if obj.reply_to:
            return format_html(
                '<span style="color: #0066cc;">↩️ پاسخ</span>'
            )
        return '-'
    reply_indicator.short_description = 'نوع'

    def deleted_indicator(self, obj):
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: red; color: white; '
                'padding: 2px 8px; border-radius: 3px;">✗ حذف شده</span>'
            )
        return format_html(
            '<span style="background-color: green; color: white; '
            'padding: 2px 8px; border-radius: 3px;">✓ فعال</span>'
        )
    deleted_indicator.short_description = 'وضعیت'

    def soft_delete_messages(self, request, queryset):
        """Soft delete selected messages"""
        updated = 0
        for message in queryset.filter(is_deleted=False):
            message.delete_message(request.user)
            updated += 1

        self.message_user(
            request,
            f'{updated} پیام حذف شد.',
            messages.SUCCESS
        )
    soft_delete_messages.short_description = 'حذف پیام‌های انتخاب شده'

    def restore_messages(self, request, queryset):
        """Restore deleted messages"""
        updated = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_by=None,
            deleted_at=None
        )

        self.message_user(
            request,
            f'{updated} پیام بازیابی شد.',
            messages.SUCCESS
        )
    restore_messages.short_description = 'بازیابی پیام‌های حذف شده'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('tournament', 'sender', 'reply_to', 'deleted_by')