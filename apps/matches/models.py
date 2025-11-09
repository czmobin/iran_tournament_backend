from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.tournaments.models import Tournament
from apps.accounts.models import User


class Match(models.Model):
    """Individual match between two players"""
    
    STATUS_CHOICES = [
        ('scheduled', 'زمان‌بندی شده'),
        ('ready', 'آماده'),
        ('ongoing', 'در حال بازی'),
        ('waiting_result', 'در انتظار نتیجه'),
        ('completed', 'تمام شده'),
        ('disputed', 'اعتراض شده'),
        ('cancelled', 'لغو شده'),
    ]
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='تورنومنت'
    )

    match_number = models.PositiveIntegerField('شماره مسابقه')
    
    # Players
    player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matches_as_player1',
        verbose_name='بازیکن 1'
    )
    player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='matches_as_player2',
        verbose_name='بازیکن 2'
    )
    
    # Best of X format
    best_of = models.PositiveIntegerField(
        'تعداد بازی',
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text='Best of 3, 5, 7, etc.'
    )
    
    # Scores
    player1_wins = models.PositiveIntegerField('برد بازیکن 1', default=0)
    player2_wins = models.PositiveIntegerField('برد بازیکن 2', default=0)
    
    # Winner
    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_matches',
        verbose_name='برنده'
    )
    
    # Status and timing
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    scheduled_time = models.DateTimeField('زمان برنامه‌ریزی شده', null=True, blank=True)
    started_at = models.DateTimeField('شروع بازی', null=True, blank=True)
    completed_at = models.DateTimeField('پایان بازی', null=True, blank=True)
    
    # Result submission tracking
    player1_submitted_result = models.BooleanField('بازیکن 1 نتیجه ثبت کرد', default=False)
    player2_submitted_result = models.BooleanField('بازیکن 2 نتیجه ثبت کرد', default=False)
    
    # Additional info
    notes = models.TextField('یادداشت‌ها', blank=True)
    admin_verified = models.BooleanField('تایید ادمین', default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_matches',
        verbose_name='تایید شده توسط'
    )
    
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)
    
    class Meta:
        db_table = 'matches'
        verbose_name = 'مسابقه'
        verbose_name_plural = 'مسابقات'
        ordering = ['tournament', 'match_number']
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['player1', 'player2']),
            models.Index(fields=['scheduled_time']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(player1=models.F('player2')),
                name='different_players'
            )
        ]
    
    def __str__(self):
        return f"Match {self.match_number}: {self.player1.username} vs {self.player2.username}"
    
    def clean(self):
        """Validate match data"""
        if self.player1 == self.player2:
            raise ValidationError('بازیکنان نمی‌توانند یکسان باشند')
        
        if self.winner and self.winner not in [self.player1, self.player2]:
            raise ValidationError('برنده باید یکی از بازیکنان باشد')
    
    @property
    def wins_needed(self):
        """Calculate wins needed to win the match"""
        return (self.best_of // 2) + 1
    
    @property
    def is_complete(self):
        """Check if match is complete"""
        return self.status == 'completed' and self.winner is not None
    
    @property
    def loser(self):
        """Get the loser of the match"""
        if not self.winner:
            return None
        return self.player2 if self.winner == self.player1 else self.player1
    
    def can_start(self):
        """Check if match can start"""
        return self.status in ['scheduled', 'ready'] and self.scheduled_time <= timezone.now()
    
    def start_match(self):
        """Start the match"""
        if self.can_start():
            self.status = 'ongoing'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
            return True
        return False
    
    def record_game_result(self, winner_user):
        """Record a single game result within the match"""
        if self.status != 'ongoing':
            raise ValidationError('مسابقه باید در حال انجام باشد')
        
        if winner_user not in [self.player1, self.player2]:
            raise ValidationError('برنده باید یکی از بازیکنان باشد')
        
        if winner_user == self.player1:
            self.player1_wins += 1
        else:
            self.player2_wins += 1
        
        # Check if match is complete
        if self.player1_wins >= self.wins_needed:
            self.complete_match(self.player1)
        elif self.player2_wins >= self.wins_needed:
            self.complete_match(self.player2)
        else:
            self.save(update_fields=['player1_wins', 'player2_wins'])
    
    def complete_match(self, winner_user):
        """Complete the match with a winner"""
        if winner_user not in [self.player1, self.player2]:
            raise ValidationError('برنده باید یکی از بازیکنان باشد')
        
        self.winner = winner_user
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Update user stats
        self._update_user_stats()
    
    def _update_user_stats(self):
        """Update both players' statistics"""
        if not self.winner:
            return
        
        # Update winner stats
        winner_stats, _ = self.winner.stats.get_or_create()
        winner_stats.total_matches += 1
        winner_stats.matches_won += 1
        winner_stats.update_win_rate()
        
        # Update loser stats
        loser = self.loser
        if loser:
            loser_stats, _ = loser.stats.get_or_create()
            loser_stats.total_matches += 1
            loser_stats.update_win_rate()
    
    def cancel(self, reason=''):
        """Cancel the match"""
        if self.status == 'completed':
            raise ValidationError('نمی‌توان مسابقه تمام شده را لغو کرد')
        
        self.status = 'cancelled'
        self.notes = f"{self.notes}\nلغو شده: {reason}"
        self.save()


class Game(models.Model):
    """Individual game within a match"""
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='games',
        verbose_name='مسابقه'
    )
    game_number = models.PositiveIntegerField('شماره بازی')
    
    winner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='won_games',
        verbose_name='برنده'
    )
    
    # Score details
    player1_crowns = models.PositiveIntegerField(
        'کرون بازیکن 1',
        validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    player2_crowns = models.PositiveIntegerField(
        'کرون بازیکن 2',
        validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    
    # Tower destruction details
    player1_towers_destroyed = models.PositiveIntegerField(
        'برج‌های تخریب شده بازیکن 1',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    player2_towers_destroyed = models.PositiveIntegerField(
        'برج‌های تخریب شده بازیکن 2',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(3)]
    )
    
    # Battle mode (if applicable)
    is_overtime = models.BooleanField('اضافه وقت', default=False)
    
    # Screenshots/proof
    screenshot = models.ImageField(
        'اسکرین‌شات',
        upload_to='match_screenshots/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='اسکرین‌شات نتیجه بازی'
    )
    
    # Timing
    duration_seconds = models.PositiveIntegerField(
        'مدت بازی (ثانیه)',
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(600)]
    )
    played_at = models.DateTimeField('زمان بازی', auto_now_add=True)
    
    # Verification
    is_verified = models.BooleanField('تایید شده', default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_games',
        verbose_name='تایید شده توسط'
    )
    verified_at = models.DateTimeField('تاریخ تایید', null=True, blank=True)
    
    # Submission tracking
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submitted_games',
        verbose_name='ثبت شده توسط'
    )
    
    class Meta:
        db_table = 'games'
        verbose_name = 'بازی'
        verbose_name_plural = 'بازی‌ها'
        ordering = ['match', 'game_number']
        unique_together = ['match', 'game_number']
        indexes = [
            models.Index(fields=['match', 'game_number']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"Game {self.game_number} of Match {self.match.match_number}"
    
    def clean(self):
        """Validate game data"""
        # Validate winner is one of the match players
        if self.winner not in [self.match.player1, self.match.player2]:
            raise ValidationError('برنده باید یکی از بازیکنان مسابقه باشد')
        
        # Validate crowns
        if self.winner == self.match.player1 and self.player1_crowns <= self.player2_crowns:
            raise ValidationError('تعداد کرون برنده باید بیشتر باشد')
        if self.winner == self.match.player2 and self.player2_crowns <= self.player1_crowns:
            raise ValidationError('تعداد کرون برنده باید بیشتر باشد')
        
        # At least one player must have scored
        if self.player1_crowns == 0 and self.player2_crowns == 0:
            raise ValidationError('حداقل یک بازیکن باید امتیاز داشته باشد')
    
    def verify(self, admin_user):
        """Verify the game result by admin"""
        if self.is_verified:
            return False
        
        self.is_verified = True
        self.verified_by = admin_user
        self.verified_at = timezone.now()
        self.save(update_fields=['is_verified', 'verified_by', 'verified_at'])
        
        # Update match if all games are verified
        if self.match.games.filter(is_verified=False).count() == 0:
            self.match.admin_verified = True
            self.match.verified_by = admin_user
            self.match.save(update_fields=['admin_verified', 'verified_by'])
        
        return True


class MatchDispute(models.Model):
    """Dispute resolution for matches"""
    
    STATUS_CHOICES = [
        ('open', 'باز'),
        ('under_review', 'در حال بررسی'),
        ('resolved', 'حل شده'),
        ('rejected', 'رد شده'),
    ]
    
    DISPUTE_TYPE_CHOICES = [
        ('cheating', 'تقلب'),
        ('no_show', 'عدم حضور حریف'),
        ('other', 'سایر'),
    ]
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='disputes',
        verbose_name='مسابقه'
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='disputes',
        verbose_name='بازی'
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='filed_disputes',
        verbose_name='گزارش‌دهنده'
    )
    
    dispute_type = models.CharField(
        'نوع اعتراض',
        max_length=20,
        choices=DISPUTE_TYPE_CHOICES,
        default='wrong_result'
    )
    
    reason = models.TextField('دلیل اعتراض')
    evidence = models.ImageField(
        'مدرک',
        upload_to='dispute_evidence/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='تصویر مدرک اعتراض'
    )
    additional_evidence = models.JSONField(
        'مدارک اضافی',
        default=list,
        blank=True,
        help_text='لینک‌ها یا توضیحات اضافی'
    )
    
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )
    
    # Admin response
    admin_response = models.TextField('پاسخ ادمین', blank=True)
    resolution_action = models.CharField(
        'اقدام انجام شده',
        max_length=200,
        blank=True,
        help_text='مثال: نتیجه اصلاح شد، بازیکن محروم شد، و غیره'
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes',
        verbose_name='حل شده توسط'
    )
    
    # Timestamps
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)
    resolved_at = models.DateTimeField('تاریخ حل', null=True, blank=True)
    
    # Priority
    priority = models.PositiveIntegerField(
        'اولویت',
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1=کم، 5=خیلی زیاد'
    )
    
    class Meta:
        db_table = 'match_disputes'
        verbose_name = 'اعتراض مسابقه'
        verbose_name_plural = 'اعتراضات مسابقات'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['match', 'reporter']),
        ]
    
    def __str__(self):
        return f"Dispute by {self.reporter.username} on Match {self.match.match_number}"
    
    def clean(self):
        """Validate dispute data"""
        # Reporter must be one of the match players
        if self.reporter not in [self.match.player1, self.match.player2]:
            raise ValidationError('فقط بازیکنان مسابقه می‌توانند اعتراض کنند')
        
        # If game is specified, it must belong to the match
        if self.game and self.game.match != self.match:
            raise ValidationError('بازی انتخاب شده متعلق به این مسابقه نیست')
    
    def start_review(self, admin_user):
        """Start reviewing the dispute"""
        if self.status != 'open':
            return False
        
        self.status = 'under_review'
        self.resolved_by = admin_user
        self.save(update_fields=['status', 'resolved_by'])
        
        # Update match status
        if self.match.status != 'disputed':
            self.match.status = 'disputed'
            self.match.save(update_fields=['status'])
        
        return True
    
    def resolve(self, admin_user, response, action=''):
        """Resolve the dispute"""
        if self.status not in ['open', 'under_review']:
            return False
        
        self.status = 'resolved'
        self.admin_response = response
        self.resolution_action = action
        self.resolved_by = admin_user
        self.resolved_at = timezone.now()
        self.save()
        
        # Check if there are any other open disputes for this match
        if not self.match.disputes.filter(status__in=['open', 'under_review']).exists():
            # Restore match status if it was completed
            if self.match.winner:
                self.match.status = 'completed'
                self.match.save(update_fields=['status'])
        
        return True
    
    def reject(self, admin_user, response):
        """Reject the dispute"""
        if self.status not in ['open', 'under_review']:
            return False
        
        self.status = 'rejected'
        self.admin_response = response
        self.resolved_by = admin_user
        self.resolved_at = timezone.now()
        self.save()
        
        return True


class MatchChat(models.Model):
    """Chat messages between match players"""
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='مسابقه'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_match_messages',
        verbose_name='فرستنده'
    )
    
    message = models.TextField('پیام', max_length=500)
    
    is_read = models.BooleanField('خوانده شده', default=False)
    read_at = models.DateTimeField('زمان خواندن', null=True, blank=True)
    
    created_at = models.DateTimeField('زمان ارسال', auto_now_add=True)
    
    class Meta:
        db_table = 'match_chats'
        verbose_name = 'چت مسابقه'
        verbose_name_plural = 'چت‌های مسابقه'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['match', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    def clean(self):
        """Validate chat message"""
        if self.sender not in [self.match.player1, self.match.player2]:
            raise ValidationError('فقط بازیکنان مسابقه می‌توانند پیام بفرستند')
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])