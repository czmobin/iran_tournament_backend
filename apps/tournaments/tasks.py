"""
Celery tasks for tournament management and Clash Royale API integration
"""

import logging
from datetime import timedelta
from typing import List
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from apps.tournaments.models import (
    Tournament,
    TournamentParticipant,
    TournamentInvitation,
    PlayerBattleLog,
    TournamentRanking,
)
from apps.tournaments.services import get_clash_royale_client
from apps.notifications.models import Notification


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def expire_old_invitations(self):
    """Expire old pending tournament invitations"""
    try:
        count = TournamentInvitation.expire_old_invitations()
        logger.info(f"Expired {count} old tournament invitations")
        return count
    except Exception as e:
        logger.error(f"Failed to expire invitations: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def check_tournament_start_times(self):
    """
    Check for tournaments that should start and trigger notifications
    Runs every minute
    """
    try:
        now = timezone.now()

        # Find tournaments that should start now
        tournaments_to_start = Tournament.objects.filter(
            status='ready',
            start_date__lte=now,
            start_date__gte=now - timedelta(minutes=2)  # Within last 2 minutes
        )

        started_count = 0
        for tournament in tournaments_to_start:
            try:
                # Start tournament
                tournament.start_tournament()

                # Enable auto-tracking if Clash Royale integration is configured
                if tournament.clash_royale_tournament_tag and not tournament.auto_tracking_enabled:
                    tournament.auto_tracking_enabled = True
                    tournament.tracking_started_at = now
                    tournament.save(update_fields=['auto_tracking_enabled', 'tracking_started_at'])

                # Send notifications to participants
                send_tournament_start_notifications.delay(tournament.id)

                started_count += 1
                logger.info(f"Started tournament: {tournament.title}")

            except Exception as e:
                logger.error(f"Failed to start tournament {tournament.id}: {str(e)}")

        return started_count

    except Exception as e:
        logger.error(f"Failed to check tournament start times: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_tournament_start_notifications(self, tournament_id: int):
    """
    Send email and SMS notifications when tournament starts

    Args:
        tournament_id: Tournament ID
    """
    try:
        tournament = Tournament.objects.select_related().get(id=tournament_id)

        # Get all confirmed participants
        participants = tournament.participants.filter(status='confirmed').select_related('user')

        if not participants.exists():
            logger.warning(f"No participants to notify for tournament {tournament_id}")
            return 0

        # Prepare tournament info
        tournament_info = {
            'title': tournament.title,
            'tag': tournament.clash_royale_tournament_tag,
            'password': tournament.tournament_password,
            'start_date': tournament.start_date,
            'duration': tournament.time_duration,
            'max_losses': tournament.max_losses,
        }

        notifications_sent = 0

        for participant in participants:
            user = participant.user

            # Create in-app notification
            Notification.create_notification(
                user=user,
                notification_type='tournament_starting',
                title=f'تورنمنت {tournament.title} شروع شد!',
                message=f'تورنمنت با تگ {tournament.clash_royale_tournament_tag} و رمز {tournament.tournament_password} آماده است.',
                priority='high',
                link=f'/tournaments/{tournament.slug}/',
                metadata={
                    'tournament_tag': tournament.clash_royale_tournament_tag,
                    'tournament_password': tournament.tournament_password,
                }
            )

            # Send email if enabled
            if hasattr(user, 'notification_preferences'):
                prefs = user.notification_preferences

                if prefs.should_send_email('tournament_starting'):
                    send_tournament_email.delay(user.id, tournament_info)

                if prefs.should_send_sms('tournament_starting'):
                    send_tournament_sms.delay(user.id, tournament_info)

            notifications_sent += 1

        logger.info(f"Sent {notifications_sent} notifications for tournament {tournament.title}")
        return notifications_sent

    except Tournament.DoesNotExist:
        logger.error(f"Tournament {tournament_id} not found")
        return 0
    except Exception as e:
        logger.error(f"Failed to send tournament notifications: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_tournament_email(self, user_id: int, tournament_info: dict):
    """
    Send tournament start email to user

    Args:
        user_id: User ID
        tournament_info: Dictionary with tournament information
    """
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)

        if not user.email:
            logger.warning(f"User {user_id} has no email address")
            return False

        subject = f"تورنمنت {tournament_info['title']} شروع شد!"

        # Create email body
        message = f"""
سلام {user.get_full_name() or user.username}،

تورنمنت {tournament_info['title']} شروع شده است!

📋 جزئیات تورنمنت:
• تگ تورنمنت: {tournament_info['tag']}
• رمز تورنمنت: {tournament_info['password']}
• زمان شروع: {tournament_info['start_date'].strftime('%Y-%m-%d %H:%M')}
• مدت زمان: {tournament_info['duration']}
• حداکثر باخت: {tournament_info['max_losses']}

🎮 نحوه شرکت:
1. بازی Clash Royale را باز کنید
2. به بخش Tournaments بروید
3. روی "Join" کلیک کنید
4. تگ تورنمنت را وارد کنید: {tournament_info['tag']}
5. رمز را وارد کنید: {tournament_info['password']}

موفق باشید! 🏆

تیم پشتیبانی Iran Tournament
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Sent tournament email to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_tournament_sms(self, user_id: int, tournament_info: dict):
    """
    Send tournament start SMS to user

    Args:
        user_id: User ID
        tournament_info: Dictionary with tournament information
    """
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)

        if not user.phone_number:
            logger.warning(f"User {user_id} has no phone number")
            return False

        # Create SMS message (max 160 characters for single SMS)
        message = (
            f"تورنمنت {tournament_info['title']} شروع شد!\n"
            f"تگ: {tournament_info['tag']}\n"
            f"رمز: {tournament_info['password']}\n"
            f"موفق باشید!"
        )

        # TODO: Integrate with SMS provider (Kavenegar, Ghasedak, etc.)
        # For now, just log
        logger.info(f"SMS to {user.phone_number}: {message}")

        # Example Kavenegar integration:
        # from kavenegar import KavenegarAPI
        # api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
        # api.sms_send({
        #     'receptor': user.phone_number,
        #     'message': message
        # })

        return True

    except Exception as e:
        logger.error(f"Failed to send SMS to user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_tournament_battle_logs(self):
    """
    Sync battle logs for all active tournaments with auto-tracking enabled
    Runs every 2 minutes
    """
    try:
        now = timezone.now()

        # Find active tournaments with auto-tracking enabled
        active_tournaments = Tournament.objects.filter(
            status='ongoing',
            auto_tracking_enabled=True,
            clash_royale_tournament_tag__isnull=False
        ).prefetch_related('participants__user')

        if not active_tournaments.exists():
            logger.debug("No active tournaments to sync")
            return 0

        total_battles_synced = 0

        for tournament in active_tournaments:
            try:
                battles_synced = sync_single_tournament_battles.delay(tournament.id)
                logger.info(f"Queued battle sync for tournament: {tournament.title}")
                total_battles_synced += 1

            except Exception as e:
                logger.error(f"Failed to queue battle sync for tournament {tournament.id}: {str(e)}")

        return total_battles_synced

    except Exception as e:
        logger.error(f"Failed to sync tournament battle logs: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_single_tournament_battles(self, tournament_id: int):
    """
    Sync battle logs for a single tournament

    Args:
        tournament_id: Tournament ID

    Returns:
        Number of new battles synced
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)

        if not tournament.clash_royale_tournament_tag:
            logger.warning(f"Tournament {tournament_id} has no Clash Royale tag")
            return 0

        # Get all confirmed participants
        participants = tournament.participants.filter(status='confirmed').select_related('user')

        if not participants.exists():
            logger.warning(f"No participants to sync for tournament {tournament_id}")
            return 0

        client = get_clash_royale_client()
        total_new_battles = 0

        for participant in participants:
            user = participant.user

            if not user.clash_royale_tag:
                logger.debug(f"User {user.username} has no Clash Royale tag")
                continue

            try:
                # Fetch battle log from API
                battles = client.get_player_battle_log(user.clash_royale_tag, use_cache=False)

                if not battles:
                    logger.debug(f"No battles found for {user.username}")
                    continue

                # Filter battles that occurred during tournament time
                tournament_start = tournament.tracking_started_at or tournament.start_date
                now = timezone.now()

                new_battles_count = 0

                for battle_raw in battles:
                    try:
                        # Extract battle data
                        battle_data = client.extract_battle_data(battle_raw, user.clash_royale_tag)

                        if not battle_data:
                            continue

                        battle_time = battle_data['battle_time']

                        # Only process battles during tournament time
                        if battle_time < tournament_start or battle_time > now:
                            continue

                        # Check if battle already exists
                        existing = PlayerBattleLog.objects.filter(
                            tournament=tournament,
                            player_tag=battle_data['player_tag'],
                            battle_time=battle_time,
                            opponent_tag=battle_data['opponent_tag']
                        ).exists()

                        if existing:
                            continue

                        # Create new battle log entry
                        PlayerBattleLog.objects.create(
                            tournament=tournament,
                            participant=participant,
                            **battle_data
                        )

                        new_battles_count += 1

                    except Exception as e:
                        logger.error(f"Failed to process battle for {user.username}: {str(e)}")
                        continue

                if new_battles_count > 0:
                    logger.info(f"Synced {new_battles_count} new battles for {user.username}")
                    total_new_battles += new_battles_count

            except Exception as e:
                logger.error(f"Failed to sync battles for user {user.username}: {str(e)}")
                continue

        # Update last sync time
        tournament.last_battle_sync_time = timezone.now()
        tournament.save(update_fields=['last_battle_sync_time'])

        # Trigger leaderboard calculation if new battles were added
        if total_new_battles > 0:
            calculate_tournament_rankings.delay(tournament_id)

        logger.info(f"Synced {total_new_battles} total new battles for tournament {tournament.title}")
        return total_new_battles

    except Tournament.DoesNotExist:
        logger.error(f"Tournament {tournament_id} not found")
        return 0
    except Exception as e:
        logger.error(f"Failed to sync battles for tournament {tournament_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


@shared_task(bind=True, max_retries=3)
def calculate_tournament_rankings(self, tournament_id: int):
    """
    Calculate and update tournament rankings based on battle logs

    Args:
        tournament_id: Tournament ID

    Returns:
        Number of rankings updated
    """
    try:
        tournament = Tournament.objects.get(id=tournament_id)

        # Get all participants
        participants = tournament.participants.filter(status='confirmed')

        if not participants.exists():
            logger.warning(f"No participants for tournament {tournament_id}")
            return 0

        rankings_updated = 0

        with transaction.atomic():
            for participant in participants:
                # Get or create ranking
                ranking, created = TournamentRanking.objects.get_or_create(
                    tournament=tournament,
                    participant=participant,
                    defaults={'rank': 999999}  # Temporary rank
                )

                # Update stats from battle logs
                ranking.update_stats()
                rankings_updated += 1

            # Now assign ranks based on score
            rankings = TournamentRanking.objects.filter(
                tournament=tournament
            ).order_by('-score', '-total_wins', '-total_crowns', 'last_battle_time')

            for index, ranking in enumerate(rankings, start=1):
                ranking.rank = index
                ranking.save(update_fields=['rank'])

        logger.info(f"Updated {rankings_updated} rankings for tournament {tournament.title}")
        return rankings_updated

    except Tournament.DoesNotExist:
        logger.error(f"Tournament {tournament_id} not found")
        return 0
    except Exception as e:
        logger.error(f"Failed to calculate rankings for tournament {tournament_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
