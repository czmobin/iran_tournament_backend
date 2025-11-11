"""
Signals for automatic object creation when tournaments are created or modified.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Tournament, TournamentChat, TournamentParticipant

User = get_user_model()


@receiver(post_save, sender=Tournament)
def create_tournament_welcome_chat(sender, instance, created, **kwargs):
    """
    Automatically create a welcome chat message when a new tournament is created.
    This helps participants know the tournament chat is active.
    """
    if created and instance.created_by:
        # Create a welcome message from the tournament creator
        welcome_message = f"""🎮 به تورنومنت {instance.title} خوش آمدید!

📋 جزئیات تورنومنت:
• حداکثر شرکت‌کنندگان: {instance.max_participants}
• حالت بازی: {instance.get_game_mode_display()}
• شروع ثبت‌نام: {instance.registration_start.strftime('%Y/%m/%d %H:%M') if instance.registration_start else 'نامشخص'}
• شروع تورنومنت: {instance.start_date.strftime('%Y/%m/%d %H:%M') if instance.start_date else 'نامشخص'}

💬 از این چت برای هماهنگی و پیگیری مسابقات استفاده کنید.
موفق باشید! 🏆"""

        try:
            TournamentChat.objects.create(
                tournament=instance,
                sender=instance.created_by,
                message=welcome_message
            )
        except Exception as e:
            # Log error but don't break tournament creation
            print(f"Error creating welcome chat for tournament {instance.id}: {e}")


@receiver(post_save, sender=TournamentParticipant)
def create_participant_join_notification(sender, instance, created, **kwargs):
    """
    Automatically create a chat notification when a participant joins the tournament.
    Only for confirmed participants to avoid spam from pending registrations.
    """
    # Only notify when a new confirmed participant is added
    if instance.status == 'confirmed' and instance.tournament.created_by:
        # Only send notification for newly confirmed participants
        if created:
            try:
                # Create a join notification message
                join_message = f"🎉 {instance.user.get_full_name() or instance.user.username} به تورنومنت پیوست!"

                TournamentChat.objects.create(
                    tournament=instance.tournament,
                    sender=instance.tournament.created_by,
                    message=join_message
                )
            except Exception as e:
                # Log error but don't break participant registration
                print(f"Error creating join notification for participant {instance.id}: {e}")


@receiver(pre_save, sender=Tournament)
def track_tournament_status_changes(sender, instance, **kwargs):
    """
    Track tournament status changes to send appropriate notifications.
    """
    if instance.pk:  # Only for existing tournaments
        try:
            old_instance = Tournament.objects.get(pk=instance.pk)

            # If status changed to 'registration', notify participants
            if old_instance.status != instance.status and instance.status == 'registration':
                if instance.created_by:
                    registration_message = f"""📢 ثبت‌نام برای تورنومنت {instance.title} آغاز شد!

⏰ مهلت ثبت‌نام: {instance.registration_end.strftime('%Y/%m/%d %H:%M') if instance.registration_end else 'نامشخص'}
👥 ظرفیت: {instance.max_participants} نفر
💰 هزینه ورودی: {instance.entry_fee} تومان

برای ثبت‌نام اقدام کنید! 🎯"""

                    # Schedule this to be created after save
                    instance._pending_registration_message = registration_message

            # If status changed to 'ongoing', notify start
            elif old_instance.status != instance.status and instance.status == 'ongoing':
                if instance.created_by:
                    start_message = f"""🚀 تورنومنت {instance.title} شروع شد!

⚔️ بازی‌ها آغاز شده است. به پروفایل خود مراجعه کنید و مسابقات را پیگیری کنید.

همه را به رقابتی منصفانه و هیجان‌انگیز دعوت می‌کنیم! 💪"""

                    instance._pending_start_message = start_message

        except Tournament.DoesNotExist:
            pass


@receiver(post_save, sender=Tournament)
def send_tournament_status_notifications(sender, instance, created, **kwargs):
    """
    Send notifications that were prepared in pre_save signal.
    """
    if not created and instance.created_by:
        # Send pending registration message
        if hasattr(instance, '_pending_registration_message'):
            try:
                TournamentChat.objects.create(
                    tournament=instance,
                    sender=instance.created_by,
                    message=instance._pending_registration_message
                )
                delattr(instance, '_pending_registration_message')
            except Exception as e:
                print(f"Error creating registration notification: {e}")

        # Send pending start message
        if hasattr(instance, '_pending_start_message'):
            try:
                TournamentChat.objects.create(
                    tournament=instance,
                    sender=instance.created_by,
                    message=instance._pending_start_message
                )
                delattr(instance, '_pending_start_message')
            except Exception as e:
                print(f"Error creating start notification: {e}")
