# Generated manually for Clash Royale integration

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0002_alter_tournament_best_of_alter_tournament_pricable'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add Clash Royale fields to Tournament
        migrations.AddField(
            model_name='tournament',
            name='clash_royale_tournament_tag',
            field=models.CharField(blank=True, help_text='مثال: #ABC123XYZ', max_length=20, null=True, verbose_name='تگ تورنمنت کلش رویال'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='tournament_password',
            field=models.CharField(blank=True, help_text='رمز تورنمنت کلش رویال برای اشتراک با بازیکنان', max_length=50, null=True, verbose_name='رمز تورنمنت'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='auto_tracking_enabled',
            field=models.BooleanField(default=False, help_text='فعال\u200cسازی دریافت خودکار battle logs از کلش رویال', verbose_name='ردیابی خودکار فعال'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='last_battle_sync_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='آخرین زمان همگام\u200cسازی بازی\u200cها'),
        ),
        migrations.AddField(
            model_name='tournament',
            name='tracking_started_at',
            field=models.DateTimeField(blank=True, help_text='زمان شروع ردیابی بازی\u200cها - معمولاً زمان شروع تورنمنت', null=True, verbose_name='زمان شروع ردیابی'),
        ),
        # Create PlayerBattleLog model
        migrations.CreateModel(
            name='PlayerBattleLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('battle_time', models.DateTimeField(db_index=True, help_text='زمان بازی از API کلش رویال', verbose_name='زمان بازی')),
                ('battle_type', models.CharField(choices=[('tournament', 'تورنمنت'), ('PvP', 'PvP'), ('challenge', 'چلنج'), ('friendly', 'دوستانه'), ('other', 'سایر')], default='tournament', max_length=20, verbose_name='نوع بازی')),
                ('game_mode', models.CharField(blank=True, max_length=50, verbose_name='حالت بازی')),
                ('player_tag', models.CharField(max_length=20, verbose_name='تگ بازیکن')),
                ('player_name', models.CharField(max_length=100, verbose_name='نام بازیکن')),
                ('player_crowns', models.PositiveIntegerField(default=0, verbose_name='تاج بازیکن')),
                ('player_king_tower_hp', models.PositiveIntegerField(blank=True, null=True, verbose_name='HP برج پادشاه بازیکن')),
                ('player_princess_towers_hp', models.JSONField(blank=True, default=list, verbose_name='HP برج\u200cهای پرنسس بازیکن')),
                ('opponent_tag', models.CharField(max_length=20, verbose_name='تگ حریف')),
                ('opponent_name', models.CharField(max_length=100, verbose_name='نام حریف')),
                ('opponent_crowns', models.PositiveIntegerField(default=0, verbose_name='تاج حریف')),
                ('opponent_king_tower_hp', models.PositiveIntegerField(blank=True, null=True, verbose_name='HP برج پادشاه حریف')),
                ('opponent_princess_towers_hp', models.JSONField(blank=True, default=list, verbose_name='HP برج\u200cهای پرنسس حریف')),
                ('is_winner', models.BooleanField(default=False, verbose_name='برنده')),
                ('is_draw', models.BooleanField(default=False, verbose_name='مساوی')),
                ('player_cards', models.JSONField(blank=True, default=list, help_text='لیست کارت\u200cهای استفاده شده', verbose_name='کارت\u200cهای بازیکن')),
                ('opponent_cards', models.JSONField(blank=True, default=list, verbose_name='کارت\u200cهای حریف')),
                ('arena_name', models.CharField(blank=True, max_length=100, verbose_name='نام آرنا')),
                ('arena_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='شناسه آرنا')),
                ('raw_battle_data', models.JSONField(blank=True, default=dict, help_text='داده کامل از API برای آینده', verbose_name='داده خام بازی')),
                ('is_counted', models.BooleanField(default=True, help_text='آیا در رتبه\u200cبندی محاسبه شود', verbose_name='محاسبه شده')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='battle_logs', to='tournaments.tournamentparticipant', verbose_name='شرکت\u200cکننده')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='battle_logs', to='tournaments.tournament', verbose_name='تورنمنت')),
            ],
            options={
                'verbose_name': 'لاگ بازی بازیکن',
                'verbose_name_plural': 'لاگ\u200cهای بازی بازیکنان',
                'db_table': 'player_battle_logs',
                'ordering': ['-battle_time'],
            },
        ),
        # Create TournamentRanking model
        migrations.CreateModel(
            name='TournamentRanking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.PositiveIntegerField(db_index=True, verbose_name='رتبه')),
                ('total_battles', models.PositiveIntegerField(default=0, verbose_name='تعداد بازی')),
                ('total_wins', models.PositiveIntegerField(default=0, verbose_name='تعداد برد')),
                ('total_losses', models.PositiveIntegerField(default=0, verbose_name='تعداد باخت')),
                ('total_draws', models.PositiveIntegerField(default=0, verbose_name='تعداد مساوی')),
                ('total_crowns', models.PositiveIntegerField(default=0, verbose_name='مجموع تاج\u200cها')),
                ('total_crowns_lost', models.PositiveIntegerField(default=0, verbose_name='مجموع تاج\u200cهای از دست رفته')),
                ('win_rate', models.DecimalField(decimal_places=2, default=0, help_text='درصد برد (0-100)', max_digits=5, verbose_name='درصد برد')),
                ('score', models.PositiveIntegerField(default=0, help_text='امتیاز محاسبه شده برای رتبه\u200cبندی', verbose_name='امتیاز')),
                ('last_battle_time', models.DateTimeField(blank=True, null=True, verbose_name='آخرین بازی')),
                ('calculated_at', models.DateTimeField(auto_now=True, verbose_name='زمان محاسبه')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rankings', to='tournaments.tournamentparticipant', verbose_name='شرکت\u200cکننده')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rankings', to='tournaments.tournament', verbose_name='تورنمنت')),
            ],
            options={
                'verbose_name': 'رتبه\u200cبندی تورنمنت',
                'verbose_name_plural': 'رتبه\u200cبندی\u200cهای تورنمنت',
                'db_table': 'tournament_rankings',
                'ordering': ['rank'],
            },
        ),
        # Add unique constraints
        migrations.AddConstraint(
            model_name='playerbattlelog',
            constraint=models.UniqueConstraint(fields=('tournament', 'player_tag', 'battle_time', 'opponent_tag'), name='unique_battle_log'),
        ),
        migrations.AddConstraint(
            model_name='tournamentranking',
            constraint=models.UniqueConstraint(fields=('tournament', 'participant'), name='unique_tournament_ranking'),
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='playerbattlelog',
            index=models.Index(fields=['tournament', 'participant', '-battle_time'], name='battle_logs_tourn_part_time'),
        ),
        migrations.AddIndex(
            model_name='playerbattlelog',
            index=models.Index(fields=['player_tag', '-battle_time'], name='battle_logs_player_time'),
        ),
        migrations.AddIndex(
            model_name='playerbattlelog',
            index=models.Index(fields=['tournament', 'is_counted'], name='battle_logs_tourn_counted'),
        ),
        migrations.AddIndex(
            model_name='playerbattlelog',
            index=models.Index(fields=['battle_time'], name='battle_logs_time'),
        ),
        migrations.AddIndex(
            model_name='tournamentranking',
            index=models.Index(fields=['tournament', 'rank'], name='rankings_tourn_rank'),
        ),
        migrations.AddIndex(
            model_name='tournamentranking',
            index=models.Index(fields=['tournament', '-score'], name='rankings_tourn_score'),
        ),
        migrations.AddIndex(
            model_name='tournamentranking',
            index=models.Index(fields=['-score'], name='rankings_score'),
        ),
    ]
