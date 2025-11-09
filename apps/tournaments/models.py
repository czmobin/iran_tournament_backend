from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from apps.accounts.models import User
from decimal import Decimal
from ckeditor.fields import RichTextField


class Tournament(models.Model):
    """Main tournament model"""
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('pending', 'در انتظار'),
        ('registration', 'ثبت‌نام'),
        ('ready', 'آماده شروع'),
        ('ongoing', 'در حال برگزاری'),
        ('finished', 'پایان یافته'),
        ('cancelled', 'لغو شده'),
    ]

    TIME_DURATION_CHOICES = [
        ('30m', '30m'),
        ('1h', '1h'),
        ('2h', '2h'),
        ('3h', '3h'),
        ('4h', '4h'),
    ]

    GAME_MODE_CHOICES = [
        ('normal', 'normal'),
        ('double_elixir_battle', 'double elixir battle'),
        ('triple_elixir_battle', 'triple elixir battle'),
        ('sudden_death_battle', 'sudden death battle'),
        ('double_elixir_draft', 'double elixir draft'),
        ('triple_draft', 'triple draft'),
        ('heist_draft', 'heist draft'),
        ('hog_race', 'hog race'),
        ('lumberjack_rash', 'lumberjack rash'),
        ('wall_breaker_party', 'wall breaker party'),
        ('ghost_parade', 'ghost parade'),
        ('elixir_capture', 'elixir capture'),
        ('dragon_hunt', 'dragon hunt'),
        ('duel', 'duel'),
        ('mega_draft_challenge', 'mega draft challenge'),
    ]
    
    PRICABLE_CHOICES = [
        ('free', 'رایگان'),
        ('premium', 'پرمیوم'),
    ]
    
    title = models.CharField('عنوان', max_length=200)
    slug = models.SlugField('اسلاگ', max_length=250, unique=True)
    description = RichTextField(verbose_name="توضیحات")

    banner = models.ImageField(
        'بنر',
        upload_to='tournament_banners/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Tournament settings
    game_mode = models.CharField(
        'حالت بازی',
        max_length=30,
        choices=GAME_MODE_CHOICES,
        default='normal'
    )
    pricable = models.CharField(
        'رایگان یا پولی',
        max_length=20,
        choices=PRICABLE_CHOICES,
        default='premium'
    )
    max_participants = models.PositiveIntegerField(
        'حداکثر شرکت‌کننده',
        validators=[MinValueValidator(2), MaxValueValidator(1000)]
    )
    
    level_cap = models.DecimalField(
        'لول کارتها',
        max_digits=2,
        decimal_places=0,
        validators=[MinValueValidator(11), MaxValueValidator(14)]
    )
    max_losses = models.DecimalField(
        'حداکثر باخت مجاز',
        max_digits=2,
        decimal_places=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    time_duration = models.CharField(
        'مدت تایم بازی',
        max_length=3,
        choices=TIME_DURATION_CHOICES,
        default='1h'
    )

    # Financial
    entry_fee = models.DecimalField(
        'هزینه ورودی',
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    prize_pool = models.DecimalField(
        'جایزه کل',
        max_digits=12,
        decimal_places=0,
        default=0
    )

    platform_commission = models.DecimalField(
        'کمیسیون پلتفرم (%)',
        max_digits=5,
        decimal_places=2,
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )

    # Dates
    registration_start = models.DateTimeField('شروع ثبت‌نام')
    registration_end = models.DateTimeField('پایان ثبت‌نام')
    start_date = models.DateTimeField('تاریخ شروع')
    end_date = models.DateTimeField('تاریخ پایان', null=True, blank=True)
    
    # Status
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    
    # Rules
    rules = RichTextField(verbose_name="قوانین", blank=True)

    # Game settings
    best_of = models.PositiveIntegerField(
        'نفرات برتر',
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text='Best of 3, 5, 7'
    )
    
    # Featured
    is_featured = models.BooleanField('ویژه', default=False)

    # Clash Royale Integration
    clash_royale_tournament_tag = models.CharField(
        'تگ تورنمنت کلش رویال',
        max_length=20,
        blank=True,
        null=True,
        help_text='مثال: #ABC123XYZ'
    )
    tournament_password = models.CharField(
        'رمز تورنمنت',
        max_length=50,
        blank=True,
        null=True,
        help_text='رمز تورنمنت کلش رویال برای اشتراک با بازیکنان'
    )
    auto_tracking_enabled = models.BooleanField(
        'ردیابی خودکار فعال',
        default=False,
        help_text='فعال‌سازی دریافت خودکار battle logs از کلش رویال'
    )
    last_battle_sync_time = models.DateTimeField(
        'آخرین زمان همگام‌سازی بازی‌ها',
        null=True,
        blank=True
    )
    tracking_started_at = models.DateTimeField(
        'زمان شروع ردیابی',
        null=True,
        blank=True,
        help_text='زمان شروع ردیابی بازی‌ها - معمولاً زمان شروع تورنمنت'
    )

    # Meta
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tournaments',
        verbose_name='ایجاد شده توسط'
    )

    total_participants = models.PositiveIntegerField('تعداد شرکت‌کننده', default=0)
    total_matches = models.PositiveIntegerField('تعداد مسابقات', default=0)
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'tournaments'
        verbose_name = 'تورنومنت'
        verbose_name_plural = 'تورنومنت‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'registration_start']),
            models.Index(fields=['start_date']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def clean(self):
        """Validate tournament data"""
        # Check dates
        if self.registration_start >= self.registration_end:
            raise ValidationError('تاریخ پایان ثبت‌نام باید بعد از شروع باشد')
        
        if self.registration_end >= self.start_date:
            raise ValidationError('تاریخ شروع تورنومنت باید بعد از پایان ثبت‌نام باشد')

    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @property
    def current_participants_count(self):
        return self.participants.filter(status='confirmed').count()

    @property
    def is_full(self):
        return self.current_participants_count >= self.max_participants

    @property
    def can_register(self):
        now = timezone.now()
        return (
            self.status == 'registration' and
            self.registration_start <= now <= self.registration_end and
            not self.is_full
        )
    
    @property
    def prize_after_commission(self):
        """Calculate prize pool after platform commission"""
        commission = (self.prize_pool * self.platform_commission) / 100
        return self.prize_pool - commission
    
    def calculate_prize_pool(self):
        """Calculate total prize pool from entry fees"""
        confirmed_count = self.current_participants_count
        self.prize_pool = confirmed_count * self.entry_fee
        self.save(update_fields=['prize_pool'])
    
    
    @transaction.atomic
    def start_tournament(self):
        """Start the tournament"""
        if self.status != 'ready':
            raise ValidationError('تورنومنت باید در حالت آماده شروع باشد')

        self.status = 'ongoing'
        self.save(update_fields=['status'])
        
        return True

    @transaction.atomic
    def finish_tournament(self):
        """Finish tournament and distribute prizes"""
        if self.status != 'ongoing':
            raise ValidationError('فقط تورنومنت‌های در حال برگزاری قابل پایان هستند')
        
        self.status = 'finished'
        self.end_date = timezone.now()
        self.save(update_fields=['status', 'end_date'])
        
        # Distribute prizes
        # self._distribute_prizes()
        
        return True
    
    @transaction.atomic
    def cancel_tournament(self, reason=''):
        """Cancel tournament and refund entry fees"""
        if self.status in ['finished', 'cancelled']:
            raise ValidationError('نمی‌توان تورنومنت پایان یافته یا لغو شده را دوباره لغو کرد')
        
        self.status = 'cancelled'
        self.save(update_fields=['status'])
        
        # Refund all confirmed participants
        for participant in self.participants.filter(status='confirmed'):
            participant.refund(reason=f'لغو تورنومنت: {reason}')
        
        return True


class TournamentParticipant(models.Model):
    """Tournament participant relation"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('confirmed', 'تایید شده'),
        ('cancelled', 'لغو شده'),
        ('disqualified', 'محروم شده'),
    ]
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='تورنومنت'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_participations',
        verbose_name='کاربر'
    )
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Placement
    placement = models.PositiveIntegerField(
        'رتبه',
        null=True,
        blank=True,
        validators=[MinValueValidator(1)]
    )
    prize_won = models.DecimalField(
        'جایزه برنده شده',
        max_digits=10,
        decimal_places=0,
        default=0
    )
    
    # Payment
    payment = models.OneToOneField(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_participant',
        verbose_name='پرداخت'
    )
    
    # Stats
    matches_played = models.PositiveIntegerField('مسابقات انجام شده', default=0)
    matches_won = models.PositiveIntegerField('مسابقات برده', default=0)
    
    # Disqualification
    disqualification_reason = models.TextField('دلیل محرومیت', blank=True)

    joined_at = models.DateTimeField('تاریخ ثبت‌نام', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'tournament_participants'
        verbose_name = 'شرکت‌کننده تورنومنت'
        verbose_name_plural = 'شرکت‌کنندگان تورنومنت'
        unique_together = ['tournament', 'user']
        ordering = ['placement', '-joined_at']
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['user', '-joined_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} در {self.tournament.title}"
    
    def clean(self):
        """Validate participant"""
    
    @transaction.atomic
    def confirm_registration(self):
        """Confirm participant registration after payment"""
        if self.status != 'pending':
            raise ValidationError('فقط ثبت‌نام‌های در انتظار قابل تایید هستند')
        
        self.status = 'confirmed'
        self.save(update_fields=['status'])
        
        # Update tournament stats
        self.tournament.total_participants = self.tournament.current_participants_count
        self.tournament.calculate_prize_pool()
        
        # Update user stats
        if hasattr(self.user, 'stats'):
            self.user.stats.tournaments_played += 1
            self.user.stats.save(update_fields=['tournaments_played'])
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.create_notification(
            user=self.user,
            notification_type='registration_confirmed',
            title='تایید ثبت‌نام',
            message=f'ثبت‌نام شما در تورنومنت {self.tournament.title} تایید شد',
            priority='high',
            link=f'/tournaments/{self.tournament.slug}/'
        )
        
        return True

    @transaction.atomic
    def disqualify(self, reason):
        """Disqualify participant"""
        if self.status == 'disqualified':
            return False
        
        self.status = 'disqualified'
        self.disqualification_reason = reason
        self.save()
        
        # Send notification
        from apps.notifications.models import Notification
        Notification.create_notification(
            user=self.user,
            notification_type='warning',
            title='محرومیت از تورنومنت',
            message=f'شما از تورنومنت {self.tournament.title} محروم شدید. دلیل: {reason}',
            priority='urgent',
            link=f'/tournaments/{self.tournament.slug}/'
        )
        
        return True
    
    @transaction.atomic
    def refund(self, reason=''):
        """Refund entry fee"""
        if self.status == 'cancelled':
            return False
        
        if self.payment and self.payment.status == 'completed':
            self.payment.refund(reason=reason)
        
        self.status = 'cancelled'
        self.save(update_fields=['status'])
        
        return True


class TournamentInvitation(models.Model):
    """Invitation system for private tournaments"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('accepted', 'پذیرفته شده'),
        ('declined', 'رد شده'),
        ('expired', 'منقضی شده'),
    ]
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='تورنومنت'
    )
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_invitations',
        verbose_name='کاربر دعوت شده'
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_tournament_invitations',
        verbose_name='دعوت شده توسط'
    )
    
    code = models.CharField(
        'کد دعوت',
        max_length=20,
        unique=True,
        db_index=True
    )
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    message = models.TextField('پیام', blank=True)
    expires_at = models.DateTimeField('تاریخ انقضا')
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    responded_at = models.DateTimeField('تاریخ پاسخ', null=True, blank=True)
    
    class Meta:
        db_table = 'tournament_invitations'
        verbose_name = 'دعوت‌نامه تورنومنت'
        verbose_name_plural = 'دعوت‌نامه‌های تورنومنت'
        unique_together = ['tournament', 'invited_user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invitation to {self.invited_user.username} for {self.tournament.title}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            import secrets
            self.code = secrets.token_urlsafe(12)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Accept invitation"""
        if self.status != 'pending':
            raise ValidationError('فقط دعوت‌نامه‌های در انتظار قابل پذیرش هستند')
        
        if self.is_expired:
            raise ValidationError('دعوت‌نامه منقضی شده است')
        
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        return True
    
    def decline(self):
        """Decline invitation"""
        if self.status != 'pending':
            raise ValidationError('فقط دعوت‌نامه‌های در انتظار قابل رد هستند')
        
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()
        
        return True
    
    @classmethod
    def expire_old_invitations(cls):
        """Expire old pending invitations"""
        return cls.objects.filter(
            status='pending',
            expires_at__lt=timezone.now()
        ).update(status='expired')


class PlayerBattleLog(models.Model):
    """Store battle logs from Clash Royale API for tournament tracking"""

    BATTLE_TYPE_CHOICES = [
        ('tournament', 'تورنمنت'),
        ('PvP', 'PvP'),
        ('challenge', 'چلنج'),
        ('friendly', 'دوستانه'),
        ('other', 'سایر'),
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='battle_logs',
        verbose_name='تورنمنت'
    )
    participant = models.ForeignKey(
        TournamentParticipant,
        on_delete=models.CASCADE,
        related_name='battle_logs',
        verbose_name='شرکت‌کننده'
    )

    # Battle identification
    battle_time = models.DateTimeField(
        'زمان بازی',
        db_index=True,
        help_text='زمان بازی از API کلش رویال'
    )
    battle_type = models.CharField(
        'نوع بازی',
        max_length=20,
        choices=BATTLE_TYPE_CHOICES,
        default='tournament'
    )
    game_mode = models.CharField(
        'حالت بازی',
        max_length=50,
        blank=True
    )

    # Player data
    player_tag = models.CharField('تگ بازیکن', max_length=20)
    player_name = models.CharField('نام بازیکن', max_length=100)
    player_crowns = models.PositiveIntegerField('تاج بازیکن', default=0)
    player_king_tower_hp = models.PositiveIntegerField(
        'HP برج پادشاه بازیکن',
        null=True,
        blank=True
    )
    player_princess_towers_hp = models.JSONField(
        'HP برج‌های پرنسس بازیکن',
        default=list,
        blank=True
    )

    # Opponent data
    opponent_tag = models.CharField('تگ حریف', max_length=20)
    opponent_name = models.CharField('نام حریف', max_length=100)
    opponent_crowns = models.PositiveIntegerField('تاج حریف', default=0)
    opponent_king_tower_hp = models.PositiveIntegerField(
        'HP برج پادشاه حریف',
        null=True,
        blank=True
    )
    opponent_princess_towers_hp = models.JSONField(
        'HP برج‌های پرنسس حریف',
        default=list,
        blank=True
    )

    # Result
    is_winner = models.BooleanField('برنده', default=False)
    is_draw = models.BooleanField('مساوی', default=False)

    # Cards used
    player_cards = models.JSONField(
        'کارت‌های بازیکن',
        default=list,
        blank=True,
        help_text='لیست کارت‌های استفاده شده'
    )
    opponent_cards = models.JSONField(
        'کارت‌های حریف',
        default=list,
        blank=True
    )

    # Arena & Trophy
    arena_name = models.CharField('نام آرنا', max_length=100, blank=True)
    arena_id = models.PositiveIntegerField('شناسه آرنا', null=True, blank=True)

    # Additional metadata from API
    raw_battle_data = models.JSONField(
        'داده خام بازی',
        default=dict,
        blank=True,
        help_text='داده کامل از API برای آینده'
    )

    # Tracking
    is_counted = models.BooleanField(
        'محاسبه شده',
        default=True,
        help_text='آیا در رتبه‌بندی محاسبه شود'
    )

    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        db_table = 'player_battle_logs'
        verbose_name = 'لاگ بازی بازیکن'
        verbose_name_plural = 'لاگ‌های بازی بازیکنان'
        ordering = ['-battle_time']
        unique_together = ['tournament', 'player_tag', 'battle_time', 'opponent_tag']
        indexes = [
            models.Index(fields=['tournament', 'participant', '-battle_time']),
            models.Index(fields=['player_tag', '-battle_time']),
            models.Index(fields=['tournament', 'is_counted']),
            models.Index(fields=['battle_time']),
        ]

    def __str__(self):
        result = "برد" if self.is_winner else "مساوی" if self.is_draw else "باخت"
        return f"{self.player_name} vs {self.opponent_name} - {result} ({self.battle_time.strftime('%Y-%m-%d %H:%M')})"

    @property
    def crown_difference(self):
        """Calculate crown difference"""
        return self.player_crowns - self.opponent_crowns


class TournamentRanking(models.Model):
    """Real-time tournament rankings based on battle logs"""

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='rankings',
        verbose_name='تورنمنت'
    )
    participant = models.ForeignKey(
        TournamentParticipant,
        on_delete=models.CASCADE,
        related_name='rankings',
        verbose_name='شرکت‌کننده'
    )

    # Ranking
    rank = models.PositiveIntegerField('رتبه', db_index=True)

    # Stats
    total_battles = models.PositiveIntegerField('تعداد بازی', default=0)
    total_wins = models.PositiveIntegerField('تعداد برد', default=0)
    total_losses = models.PositiveIntegerField('تعداد باخت', default=0)
    total_draws = models.PositiveIntegerField('تعداد مساوی', default=0)

    total_crowns = models.PositiveIntegerField('مجموع تاج‌ها', default=0)
    total_crowns_lost = models.PositiveIntegerField('مجموع تاج‌های از دست رفته', default=0)

    # Win rate
    win_rate = models.DecimalField(
        'درصد برد',
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='درصد برد (0-100)'
    )

    # Score calculation (can be customized)
    score = models.PositiveIntegerField(
        'امتیاز',
        default=0,
        help_text='امتیاز محاسبه شده برای رتبه‌بندی'
    )

    # Last battle
    last_battle_time = models.DateTimeField(
        'آخرین بازی',
        null=True,
        blank=True
    )

    # Timestamps
    calculated_at = models.DateTimeField('زمان محاسبه', auto_now=True)

    class Meta:
        db_table = 'tournament_rankings'
        verbose_name = 'رتبه‌بندی تورنمنت'
        verbose_name_plural = 'رتبه‌بندی‌های تورنمنت'
        unique_together = ['tournament', 'participant']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['tournament', 'rank']),
            models.Index(fields=['tournament', '-score']),
            models.Index(fields=['-score']),
        ]

    def __str__(self):
        return f"#{self.rank} - {self.participant.user.username} در {self.tournament.title}"

    def calculate_score(self):
        """
        Calculate score for ranking
        Formula: (Wins * 3) + (Draws * 1) + (Total Crowns / 10)
        """
        win_points = self.total_wins * 3
        draw_points = self.total_draws * 1
        crown_bonus = self.total_crowns // 10  # Every 10 crowns = 1 bonus point

        self.score = win_points + draw_points + crown_bonus
        return self.score

    def calculate_win_rate(self):
        """Calculate win rate percentage"""
        if self.total_battles == 0:
            self.win_rate = 0
        else:
            self.win_rate = (self.total_wins / self.total_battles) * 100
        return self.win_rate

    def update_stats(self):
        """Update all statistics from battle logs"""
        battles = self.participant.battle_logs.filter(
            tournament=self.tournament,
            is_counted=True
        )

        self.total_battles = battles.count()
        self.total_wins = battles.filter(is_winner=True).count()
        self.total_draws = battles.filter(is_draw=True).count()
        self.total_losses = self.total_battles - self.total_wins - self.total_draws

        # Calculate crowns
        from django.db.models import Sum
        crown_stats = battles.aggregate(
            total_crowns=Sum('player_crowns'),
            total_crowns_lost=Sum('opponent_crowns')
        )
        self.total_crowns = crown_stats['total_crowns'] or 0
        self.total_crowns_lost = crown_stats['total_crowns_lost'] or 0

        # Get last battle time
        last_battle = battles.order_by('-battle_time').first()
        self.last_battle_time = last_battle.battle_time if last_battle else None

        # Calculate derived stats
        self.calculate_win_rate()
        self.calculate_score()

        self.save()
        return True