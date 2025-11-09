from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Match, Game, MatchChat


class GameInline(admin.TabularInline):
    """Inline for games within a match"""
    model = Game
    extra = 0
    
    fields = (
        'game_number', 'winner', 'player1_crowns',
        'player2_crowns', 'is_verified'
    )
    readonly_fields = ('game_number', 'winner', 'played_at')
    
    autocomplete_fields = ['winner']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Match admin"""
    
    list_display = (
        'match_info', 'tournament_link',
        'players_display', 'score_display',
        'status_badge', 'scheduled_time',
        'verified_badge'
    )
    
    list_filter = (
        'status', 'admin_verified',
        'tournament',
        'scheduled_time', 'created_at'
    )
    
    search_fields = (
        'tournament__title', 'player1__username',
        'player2__username', 'match_number'
    )
    
    readonly_fields = (
        'tournament', 'match_number',
        'player1', 'player2', 'winner',
        'player1_wins', 'player2_wins',
        'started_at', 'completed_at',
        'created_at', 'updated_at',
        'match_duration', 'games_summary'
    )
    
    autocomplete_fields = ['verified_by']
    
    fieldsets = (
        ('اطلاعات مسابقه', {
            'fields': (
                'tournament', 'match_number', 'best_of'
            )
        }),
        ('بازیکنان', {
            'fields': ('player1', 'player2')
        }),
        ('نتایج', {
            'fields': (
                'player1_wins', 'player2_wins', 'winner',
                'games_summary'
            )
        }),
        ('وضعیت', {
            'fields': ('status', 'scheduled_time')
        }),
        ('ثبت نتیجه', {
            'fields': (
                'player1_submitted_result',
                'player2_submitted_result'
            ),
            'classes': ('collapse',)
        }),
        ('تایید', {
            'fields': ('admin_verified', 'verified_by')
        }),
        ('یادداشت', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': (
                'started_at', 'completed_at',
                'match_duration', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [GameInline]
    
    actions = [
        'start_matches', 'complete_matches',
        'cancel_matches', 'verify_matches'
    ]
    
    def match_info(self, obj):
        """Display match number and best of"""
        return format_html(
            '<strong>مسابقه #{}</strong><br>'
            '<small>Best of {}</small>',
            obj.match_number, obj.best_of
        )
    match_info.short_description = 'مسابقه'
    
    def tournament_link(self, obj):
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
    tournament_link.short_description = 'تورنومنت'
    
    def players_display(self, obj):
        """Display both players with links"""
        p1_url = reverse('admin:accounts_user_change', args=[obj.player1.id])
        p2_url = reverse('admin:accounts_user_change', args=[obj.player2.id])
        
        return format_html(
            '<a href="{}">{}</a><br>vs<br><a href="{}">{}</a>',
            p1_url, obj.player1.username,
            p2_url, obj.player2.username
        )
    players_display.short_description = 'بازیکنان'
    
    def score_display(self, obj):
        """Display score with winner highlight"""
        if obj.winner:
            if obj.winner == obj.player1:
                return format_html(
                    '<span style="color: green; font-weight: bold;">{}</span> - {}',
                    obj.player1_wins, obj.player2_wins
                )
            else:
                return format_html(
                    '{} - <span style="color: green; font-weight: bold;">{}</span>',
                    obj.player1_wins, obj.player2_wins
                )
        return format_html('{} - {}', obj.player1_wins, obj.player2_wins)
    score_display.short_description = 'نتیجه'
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'blue',
            'ready': 'purple',
            'ongoing': 'orange',
            'waiting_result': 'yellow',
            'completed': 'green',
            'disputed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'
    
    def verified_badge(self, obj):
        if obj.admin_verified:
            return format_html(
                '<span style="color: green; font-size: 16px;">✓</span>'
            )
        return format_html(
            '<span style="color: orange; font-size: 16px;">⏳</span>'
        )
    verified_badge.short_description = 'تایید'
    verified_badge.admin_order_field = 'admin_verified'
    
    def match_duration(self, obj):
        """Calculate match duration"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            minutes = int(duration.total_seconds() / 60)
            return f'{minutes} دقیقه'
        return '—'
    match_duration.short_description = 'مدت مسابقه'
    
    def games_summary(self, obj):
        """Display games summary"""
        games = obj.games.all()
        if not games:
            return '—'
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th>بازی</th><th>برنده</th><th>نتیجه</th><th>تایید</th></tr>'
        
        for game in games:
            verified = '✓' if game.is_verified else '✗'
            verified_color = 'green' if game.is_verified else 'red'
            
            html += f'''
            <tr>
                <td>بازی {game.game_number}</td>
                <td>{game.winner.username}</td>
                <td>{game.player1_crowns} - {game.player2_crowns}</td>
                <td style="color: {verified_color};">{verified}</td>
            </tr>
            '''
        
        html += '</table>'
        return format_html(html)
    games_summary.short_description = 'خلاصه بازی‌ها'
    
    def start_matches(self, request, queryset):
        """Start selected matches"""
        success = 0
        for match in queryset.filter(status__in=['scheduled', 'ready']):
            try:
                match.start_match()
                success += 1
            except:
                pass
        
        self.message_user(request, f'{success} مسابقه شروع شد.')
    start_matches.short_description = 'شروع مسابقات'
    
    def complete_matches(self, request, queryset):
        """Mark matches as completed (for admin override)"""
        from django import forms
        from django.shortcuts import render, redirect
        
        class CompleteForm(forms.Form):
            winner = forms.ModelChoiceField(
                label='برنده',
                queryset=None,
                required=True
            )
            
            def __init__(self, match, *args, **kwargs):
                super().__init__(*args, **kwargs)
                from apps.accounts.models import User
                self.fields['winner'].queryset = User.objects.filter(
                    id__in=[match.player1.id, match.player2.id]
                )
        
        # This would need a custom view implementation
        updated = 0
        for match in queryset.filter(status='ongoing'):
            if match.winner:
                match.status = 'completed'
                match.completed_at = timezone.now()
                match.save()
                updated += 1
        
        self.message_user(request, f'{updated} مسابقه تکمیل شد.')
    complete_matches.short_description = 'تکمیل مسابقات'
    
    def cancel_matches(self, request, queryset):
        """Cancel selected matches"""
        from django import forms
        from django.shortcuts import render, redirect
        
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
                
                for match in queryset:
                    try:
                        match.cancel(reason)
                        success += 1
                    except:
                        pass
                
                self.message_user(request, f'{success} مسابقه لغو شد.')
                return redirect('..')
        else:
            form = CancelForm()
        
        return render(
            request,
            'admin/cancel_match_form.html',
            {'form': form, 'matches': queryset}
        )
    cancel_matches.short_description = 'لغو مسابقات'
    
    def verify_matches(self, request, queryset):
        """Verify selected matches"""
        updated = queryset.filter(status='completed').update(
            admin_verified=True,
            verified_by=request.user
        )
        self.message_user(request, f'{updated} مسابقه تایید شد.')
    verify_matches.short_description = 'تایید مسابقات'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'tournament', 'player1', 'player2', 'winner', 'verified_by'
        ).prefetch_related('games')


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Game admin"""
    
    list_display = (
        'game_info', 'match_link', 'winner_link',
        'score_display', 'verified_badge', 'played_at'
    )
    
    list_filter = (
        'is_verified', 'is_overtime',
        'played_at'
    )
    
    search_fields = (
        'match__match_number', 'match__tournament__title',
        'winner__username'
    )
    
    readonly_fields = (
        'match', 'game_number', 'winner',
        'player1_crowns', 'player2_crowns',
        'player1_towers_destroyed', 'player2_towers_destroyed',
        'duration_seconds', 'played_at',
        'submitted_by', 'verified_at'
    )
    
    autocomplete_fields = ['verified_by']
    
    fieldsets = (
        ('اطلاعات بازی', {
            'fields': ('match', 'game_number', 'is_overtime')
        }),
        ('نتیجه', {
            'fields': (
                'winner', 'player1_crowns', 'player2_crowns',
                'player1_towers_destroyed', 'player2_towers_destroyed'
            )
        }),
        ('زمان', {
            'fields': ('duration_seconds', 'played_at')
        }),
        ('تایید', {
            'fields': (
                'is_verified', 'verified_by', 'verified_at',
                'submitted_by'
            )
        })
    )
    
    actions = ['verify_games', 'reject_games']
    
    def game_info(self, obj):
        return format_html(
            'بازی {} از {}<br><small>Best of {}</small>',
            obj.game_number, obj.match.match_number,
            obj.match.best_of
        )
    game_info.short_description = 'بازی'
    
    def match_link(self, obj):
        url = reverse('admin:matches_match_change', args=[obj.match.id])
        return format_html(
            '<a href="{}">مسابقه #{}</a><br>'
            '<small>{}</small>',
            url, obj.match.match_number,
            obj.match.tournament.title
        )
    match_link.short_description = 'مسابقه'
    
    def winner_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.winner.id])
        return format_html('<a href="{}">{}</a>', url, obj.winner.username)
    winner_link.short_description = 'برنده'
    
    def score_display(self, obj):
        p1_name = obj.match.player1.username
        p2_name = obj.match.player2.username
        
        if obj.winner == obj.match.player1:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span> '
                '<strong>{}</strong> - {} {}',
                p1_name, obj.player1_crowns,
                obj.player2_crowns, p2_name
            )
        else:
            return format_html(
                '{} {} - <strong>{}</strong> '
                '<span style="color: green; font-weight: bold;">{}</span>',
                p1_name, obj.player1_crowns,
                obj.player2_crowns, p2_name
            )
    score_display.short_description = 'نتیجه'
    
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✓ تایید شده</span><br>'
                '<small>توسط {}</small>',
                obj.verified_by.username if obj.verified_by else '—'
            )
        return format_html('<span style="color: red;">✗ تایید نشده</span>')
    verified_badge.short_description = 'تایید'
    verified_badge.admin_order_field = 'is_verified'

    def verify_games(self, request, queryset):
        """Verify selected games"""
        updated = 0
        for game in queryset.filter(is_verified=False):
            try:
                game.verify(request.user)
                updated += 1
            except:
                pass
        
        self.message_user(request, f'{updated} بازی تایید شد.')
    verify_games.short_description = 'تایید بازی‌ها'
    
    def reject_games(self, request, queryset):
        """Reject/unverify games"""
        updated = queryset.update(
            is_verified=False,
            verified_by=None,
            verified_at=None
        )
        self.message_user(request, f'{updated} بازی رد شد.')
    reject_games.short_description = 'رد بازی‌ها'
    
    def has_add_permission(self, request):
        """Prevent manual game creation"""
        return False

@admin.register(MatchChat)
class MatchChatAdmin(admin.ModelAdmin):
    """Match chat admin"""
    
    list_display = (
        'id', 'match_link', 'sender_link',
        'message_preview', 'read_badge',
        'created_at'
    )
    
    list_filter = ('is_read', 'created_at')
    
    search_fields = (
        'match__match_number', 'sender__username',
        'message'
    )
    
    readonly_fields = (
        'match', 'sender', 'message',
        'created_at', 'read_at'
    )
    
    fieldsets = (
        ('اطلاعات', {
            'fields': ('match', 'sender', 'message')
        }),
        ('وضعیت', {
            'fields': ('is_read', 'read_at')
        }),
        ('تاریخ', {
            'fields': ('created_at',)
        })
    )
    
    def match_link(self, obj):
        url = reverse('admin:matches_match_change', args=[obj.match.id])
        return format_html('<a href="{}">مسابقه #{}</a>', url, obj.match.match_number)
    match_link.short_description = 'مسابقه'
    
    def sender_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = 'فرستنده'
    
    def message_preview(self, obj):
        preview = obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
        return preview
    message_preview.short_description = 'پیام'
    
    def read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')
    read_badge.short_description = 'خوانده شده'
    read_badge.admin_order_field = 'is_read'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    