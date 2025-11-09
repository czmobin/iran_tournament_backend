from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Q
from django.utils import timezone

from .models import Notification, NotificationPreference, NotificationTemplate
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationPreferenceSerializer, NotificationTemplateSerializer
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing notifications"""

    queryset = Notification.objects.select_related('user')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['notification_type', 'priority', 'is_read']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    def get_queryset(self):
        """Filter queryset to show only user's notifications"""
        user = self.request.user
        queryset = super().get_queryset()

        # Users see only their own notifications (unless admin)
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        # Filter out expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()

        # Check if user owns this notification
        if notification.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'شما مجاز به این عملیات نیستید'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_read()
        return Response({
            'message': 'اعلان به عنوان خوانده شده علامت خورد',
            'notification': NotificationSerializer(notification).data
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        user = request.user
        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False
        )

        count = unread_notifications.count()
        for notification in unread_notifications:
            notification.mark_as_read()

        return Response({
            'message': f'{count} اعلان به عنوان خوانده شده علامت خورد',
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        user = request.user
        count = Notification.objects.filter(
            user=user,
            is_read=False
        ).count()

        return Response({
            'unread_count': count
        })

    @action(detail=False, methods=['delete'], permission_classes=[IsAuthenticated])
    def delete_all_read(self, request):
        """Delete all read notifications"""
        user = request.user
        deleted_count, _ = Notification.objects.filter(
            user=user,
            is_read=True
        ).delete()

        return Response({
            'message': f'{deleted_count} اعلان خوانده شده حذف شد',
            'deleted_count': deleted_count
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification preferences"""

    queryset = NotificationPreference.objects.select_related('user')
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to show only user's preferences"""
        user = self.request.user
        queryset = super().get_queryset()

        # Users see only their own preferences
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's notification preferences"""
        user = request.user

        # Get or create preference
        preference, created = NotificationPreference.objects.get_or_create(user=user)

        if request.method == 'GET':
            serializer = NotificationPreferenceSerializer(preference)
            return Response(serializer.data)

        elif request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = NotificationPreferenceSerializer(
                preference,
                data=request.data,
                partial=partial
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification templates (admin only)"""

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_active']
