from rest_framework import serializers
from .models import Notification, NotificationPreference, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_username', 'notification_type',
            'priority', 'title', 'message', 'link', 'action_text',
            'is_read', 'read_at', 'is_sent_email', 'is_sent_sms',
            'is_sent_push', 'metadata', 'expires_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'is_read', 'read_at', 'is_sent_email',
            'is_sent_sms', 'is_sent_push', 'created_at'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Minimal serializer for notification listings"""

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'priority', 'title',
            'message', 'is_read', 'created_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""

    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_username',
            # Email preferences
            'email_enabled', 'email_tournament_created', 'email_match_scheduled',
            'email_match_starting', 'email_match_reminder', 'email_prize_awarded',
            'email_payment', 'email_withdrawal', 'email_dispute', 'email_system',
            # SMS preferences
            'sms_enabled', 'sms_match_starting', 'sms_match_reminder',
            'sms_payment', 'sms_withdrawal',
            # Push preferences
            'push_enabled', 'push_tournament', 'push_match',
            'push_payment', 'push_dispute',
            # Quiet hours
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            # Digest
            'digest_enabled', 'digest_frequency',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model"""

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'notification_type', 'email_subject', 'email_body',
            'sms_body', 'push_title', 'push_body', 'app_title',
            'app_body', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
