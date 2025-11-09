from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from .models import Tournament, TournamentParticipant, TournamentInvitation
from .serializers import (
    TournamentListSerializer, TournamentDetailSerializer,
    TournamentParticipantSerializer, TournamentRegistrationSerializer,
    TournamentInvitationSerializer, TournamentLeaderboardSerializer,
    TournamentStatsSerializer
)
from .filters import TournamentFilter, ParticipantFilter
from .pagination import TournamentPagination, ParticipantPagination


class TournamentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for tournaments"""
    queryset = Tournament.objects.select_related('created_by').all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TournamentFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'prize_pool', 'entry_fee', 'registration_start']
    ordering = ['-created_at']
    pagination_class = TournamentPagination
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TournamentDetailSerializer
        return TournamentListSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'stats', 'leaderboard', 'participants']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param == 'active':
            queryset = queryset.filter(
                status__in=['registration', 'ready', 'ongoing']
            )
        elif status_param == 'upcoming':
            queryset = queryset.filter(
                status='registration',
                registration_start__lte=timezone.now(),
                registration_end__gte=timezone.now()
            )
        elif status_param == 'finished':
            queryset = queryset.filter(status='finished')
        
        # Filter by availability
        available = self.request.query_params.get('available')
        if available == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                status='registration',
                registration_start__lte=now,
                registration_end__gte=now
            )
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, slug=None):
        """Register user for tournament"""
        tournament = self.get_object()
        
        # Check if tournament allows registration
        if not tournament.can_register:
            return Response(
                {'error': 'امکان ثبت‌نام در این تورنومنت وجود ندارد'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already registered
        existing = TournamentParticipant.objects.filter(
            tournament=tournament,
            user=request.user,
            status__in=['pending', 'confirmed']
        ).first()
        
        if existing:
            return Response(
                {'error': 'شما قبلاً در این تورنومنت ثبت‌نام کرده‌اید'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Create participant
                participant = TournamentParticipant.objects.create(
                    tournament=tournament,
                    user=request.user,
                    status='pending'
                )
                
                # Handle free tournaments
                if tournament.pricable == 'free':
                    participant.confirm_registration()
                    return Response(
                        {
                            'message': 'ثبت‌نام شما با موفقیت انجام شد',
                            'participant_id': participant.id
                        },
                        status=status.HTTP_201_CREATED
                    )
                
                # Create payment for premium tournaments
                from apps.payments.models import Payment
                payment = Payment.objects.create(
                    user=request.user,
                    amount=tournament.entry_fee,
                    payment_type='tournament_entry',
                    description=f'هزینه ثبت‌نام در تورنومنت {tournament.title}',
                    status='pending'
                )
                participant.payment = payment
                participant.save()
                
                return Response(
                    {
                        'message': 'لطفاً هزینه ثبت‌نام را پرداخت کنید',
                        'participant_id': participant.id,
                        'payment_id': payment.id,
                        'amount': str(tournament.entry_fee),
                        'payment_url': f'/payments/{payment.id}/pay/'
                    },
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_registration(self, request, slug=None):
        """Cancel tournament registration"""
        tournament = self.get_object()
        
        try:
            participant = TournamentParticipant.objects.get(
                tournament=tournament,
                user=request.user,
                status__in=['pending', 'confirmed']
            )
        except TournamentParticipant.DoesNotExist:
            return Response(
                {'error': 'شما در این تورنومنت ثبت‌نام نکرده‌اید'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if tournament has started
        if tournament.status in ['ongoing', 'finished']:
            return Response(
                {'error': 'امکان لغو ثبت‌نام بعد از شروع تورنومنت وجود ندارد'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant.refund(reason='لغو توسط کاربر')
            return Response(
                {'message': 'ثبت‌نام شما با موفقیت لغو شد'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def participants(self, request, slug=None):
        """Get tournament participants"""
        tournament = self.get_object()
        participants = tournament.participants.filter(
            status='confirmed'
        ).select_related('user').order_by('joined_at')
        
        # Pagination
        page = self.paginate_queryset(participants)
        if page is not None:
            serializer = TournamentParticipantSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TournamentParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def leaderboard(self, request, slug=None):
        """Get tournament leaderboard"""
        tournament = self.get_object()
        participants = tournament.participants.filter(
            status='confirmed'
        ).select_related('user').order_by('placement', '-matches_won', '-matches_played')
        
        serializer = TournamentLeaderboardSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def my_participation(self, request, slug=None):
        """Get user's participation in tournament"""
        tournament = self.get_object()
        
        try:
            participant = TournamentParticipant.objects.select_related('user').get(
                tournament=tournament,
                user=request.user
            )
            serializer = TournamentParticipantSerializer(participant)
            return Response(serializer.data)
        except TournamentParticipant.DoesNotExist:
            return Response(
                {'error': 'شما در این تورنومنت ثبت‌نام نکرده‌اید'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get tournament statistics"""
        total = Tournament.objects.count()
        
        active = Tournament.objects.filter(
            status__in=['registration', 'ready', 'ongoing']
        ).count()
        
        participants_count = TournamentParticipant.objects.filter(
            status='confirmed'
        ).count()
        
        prize_pool_sum = Tournament.objects.filter(
            status__in=['registration', 'ready', 'ongoing']
        ).aggregate(total=Sum('prize_pool'))['total'] or 0
        
        upcoming = Tournament.objects.filter(
            status='registration',
            registration_start__lte=timezone.now(),
            registration_end__gte=timezone.now()
        ).count()
        
        data = {
            'total_tournaments': total,
            'active_tournaments': active,
            'total_participants': participants_count,
            'total_prize_pool': prize_pool_sum,
            'upcoming_tournaments': upcoming
        }
        
        serializer = TournamentStatsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_tournaments(self, request):
        """Get user's tournaments"""
        participations = TournamentParticipant.objects.filter(
            user=request.user
        ).select_related('tournament', 'user').order_by('-joined_at')
        
        # Pagination
        page = self.paginate_queryset(participations)
        if page is not None:
            serializer = TournamentParticipantSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TournamentParticipantSerializer(participations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured tournaments"""
        tournaments = self.get_queryset().filter(is_featured=True)[:6]
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)


class TournamentParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for tournament participants"""
    queryset = TournamentParticipant.objects.select_related('tournament', 'user').all()
    serializer_class = TournamentParticipantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ParticipantFilter
    ordering_fields = ['joined_at', 'placement', 'matches_played', 'matches_won']
    ordering = ['-joined_at']
    pagination_class = ParticipantPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by tournament slug
        tournament_slug = self.request.query_params.get('tournament_slug')
        if tournament_slug:
            queryset = queryset.filter(tournament__slug=tournament_slug)
        
        # Only show user's own participations
        return queryset.filter(user=self.request.user)


class TournamentInvitationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for tournament invitations"""
    queryset = TournamentInvitation.objects.select_related('tournament', 'invited_user', 'invited_by').all()
    serializer_class = TournamentInvitationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Show only user's invitations
        return TournamentInvitation.objects.filter(
            invited_user=self.request.user,
            status='pending'
        ).select_related('tournament', 'invited_by')
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept invitation"""
        invitation = self.get_object()
        
        # Check ownership
        if invitation.invited_user != request.user:
            return Response(
                {'error': 'این دعوتنامه برای شما نیست'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            with transaction.atomic():
                invitation.accept()
                
                # Register user in tournament if possible
                tournament = invitation.tournament
                if tournament.can_register:
                    # Check if not already registered
                    if not TournamentParticipant.objects.filter(
                        tournament=tournament,
                        user=request.user,
                        status__in=['pending', 'confirmed']
                    ).exists():
                        # Create participant
                        TournamentParticipant.objects.create(
                            tournament=tournament,
                            user=request.user,
                            status='pending'
                        )
                
                return Response(
                    {'message': 'دعوتنامه با موفقیت پذیرفته شد'},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline invitation"""
        invitation = self.get_object()
        
        # Check ownership
        if invitation.invited_user != request.user:
            return Response(
                {'error': 'این دعوتنامه برای شما نیست'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            invitation.decline()
            return Response(
                {'message': 'دعوتنامه رد شد'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )