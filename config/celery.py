import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('iran_tournament')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Periodic Tasks
app.conf.beat_schedule = {
    # Expire old pending payments every 5 minutes
    'expire-old-payments': {
        'task': 'apps.payments.tasks.expire_old_payments',
        'schedule': crontab(minute='*/5'),
    },
    
    # Expire old coupons every hour
    'expire-old-coupons': {
        'task': 'apps.payments.tasks.expire_old_coupons',
        'schedule': crontab(minute=0),
    },
    
    # Delete expired notifications daily at 3 AM
    'delete-expired-notifications': {
        'task': 'apps.notifications.tasks.delete_expired_notifications',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Expire old invitations daily at 4 AM
    'expire-old-invitations': {
        'task': 'apps.tournaments.tasks.expire_old_invitations',
        'schedule': crontab(hour=4, minute=0),
    },
    
    # Check tournament start times every minute
    'check-tournament-start-times': {
        'task': 'apps.tournaments.tasks.check_tournament_start_times',
        'schedule': crontab(minute='*/1'),
    },
    
    # Send match reminders every 5 minutes
    'send-match-reminders': {
        'task': 'apps.matches.tasks.send_match_reminders',
        'schedule': crontab(minute='*/5'),
    },
    
    # Update user rankings daily at 2 AM
    'update-user-rankings': {
        'task': 'apps.accounts.tasks.update_user_rankings',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Send daily digest to users at 8 AM
    'send-daily-digest': {
        'task': 'apps.notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },

    # Sync Clash Royale battle logs every 2 minutes for active tournaments
    'sync-tournament-battle-logs': {
        'task': 'apps.tournaments.tasks.sync_tournament_battle_logs',
        'schedule': crontab(minute='*/2'),
    },
}

# Task settings
app.conf.task_routes = {
    'apps.payments.tasks.*': {'queue': 'payments'},
    'apps.notifications.tasks.send_email': {'queue': 'notifications'},
    'apps.notifications.tasks.send_sms': {'queue': 'notifications'},
}

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# print('Celery app initialized successfully!')