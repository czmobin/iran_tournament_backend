# Generated manually for tournament chat feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0003_clash_royale_integration'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create TournamentChat model
        migrations.CreateModel(
            name='TournamentChat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(max_length=1000, verbose_name='پیام')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='حذف شده')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان حذف')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')),
                ('deleted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_tournament_messages', to=settings.AUTH_USER_MODEL, verbose_name='حذف شده توسط')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='tournaments.tournamentchat', verbose_name='پاسخ به')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_tournament_messages', to=settings.AUTH_USER_MODEL, verbose_name='فرستنده')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='tournaments.tournament', verbose_name='تورنمنت')),
            ],
            options={
                'verbose_name': 'چت تورنمنت',
                'verbose_name_plural': 'چت‌های تورنمنت',
                'db_table': 'tournament_chats',
                'ordering': ['created_at'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='tournamentchat',
            index=models.Index(fields=['tournament', 'created_at'], name='chat_tourn_time'),
        ),
        migrations.AddIndex(
            model_name='tournamentchat',
            index=models.Index(fields=['sender', '-created_at'], name='chat_sender_time'),
        ),
        migrations.AddIndex(
            model_name='tournamentchat',
            index=models.Index(fields=['tournament', 'is_deleted'], name='chat_tourn_deleted'),
        ),
    ]
