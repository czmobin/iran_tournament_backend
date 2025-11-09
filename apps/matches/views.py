from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Match, Game, MatchDispute, MatchChat
from .serializers import (
    MatchSerializer, MatchListSerializer, MatchCreateSerializer,
    MatchUpdateSerializer, SubmitMatchResultSerializer,
    GameSerializer, GameCreateSerializer,
    MatchDisputeSerializer, MatchDisputeCreateSerializer, MatchDisputeResolveSerializer,
    MatchChatSerializer, MatchChatCreateSerializer
)


class MatchViewSet(viewsets.ModelViewSet):
    """ViewSet for managing matches"""

    queryset = Match.objects.select_related(
        'tournament', 'player1', 'player2', 'winner', 'verified_by'
    ).prefetch_related('games')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tournament', 'status', 'player1', 'player2']
    search_fields = ['player1__username', 'player2__username', 'tournament__title']
    ordering_fields = ['match_number', 'scheduled_time', 'created_at']
    ordering = ['match_number']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return MatchListSerializer
        elif self.action == 'create':
            return MatchCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MatchUpdateSerializer
        return MatchSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by user's matches if not admin
        if not user.is_staff:
            queryset = queryset.filter(
                Q(player1=user) | Q(player2=user)
            )

        # Filter by tournament
        tournament_id = self.request.query_params.get('tournament_id')
        if tournament_id:
            queryset = queryset.filter(tournament_id=tournament_id)

        return queryset

    def perform_create(self, serializer):
        """Create a new match"""
        # Only admins can create matches
        if not self.request.user.is_staff:
            raise PermissionError('فقط ادمین می‌تواند مسابقه ایجاد کند')
        serializer.save()

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a match"""
        match = self.get_object()

        # Check if user is one of the players or admin
        if not (request.user in [match.player1, match.player2] or request.user.is_staff):
            return Response(
                {'error': 'شما مجاز به شروع این مسابقه نیستید'},
                status=status.HTTP_403_FORBIDDEN
            )

        if match.start_match():
            return Response({
                'message': 'مسابقه شروع شد',
                'match': MatchSerializer(match).data
            })
        else:
            return Response(
                {'error': 'مسابقه نمی‌تواند شروع شود'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def submit_result(self, request, pk=None):
        """Submit match result"""
        match = self.get_object()

        # Check if user is one of the players
        if request.user not in [match.player1, match.player2]:
            return Response(
                {'error': 'فقط بازیکنان می‌توانند نتیجه ثبت کنند'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SubmitMatchResultSerializer(
            data=request.data,
            context={'match': match}
        )
        serializer.is_valid(raise_exception=True)

        # Mark that this player submitted result
        if request.user == match.player1:
            match.player1_submitted_result = True
        else:
            match.player2_submitted_result = True

        match.save(update_fields=['player1_submitted_result', 'player2_submitted_result'])

        # If both players submitted and results match, auto-complete
        if match.player1_submitted_result and match.player2_submitted_result:
            match.status = 'waiting_result'
            match.save(update_fields=['status'])

        return Response({
            'message': 'نتیجه ثبت شد',
            'match': MatchSerializer(match).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify match result (admin only)"""
        match = self.get_object()

        if match.status != 'waiting_result':
            return Response(
                {'error': 'مسابقه در حالت مناسب برای تایید نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )

        match.admin_verified = True
        match.verified_by = request.user
        match.status = 'completed'
        match.save(update_fields=['admin_verified', 'verified_by', 'status'])

        return Response({
            'message': 'نتیجه مسابقه تایید شد',
            'match': MatchSerializer(match).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        """Cancel a match (admin only)"""
        match = self.get_object()
        reason = request.data.get('reason', '')

        try:
            match.cancel(reason=reason)
            return Response({
                'message': 'مسابقه لغو شد',
                'match': MatchSerializer(match).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def games(self, request, pk=None):
        """Get all games for a match"""
        match = self.get_object()
        games = match.games.all()
        serializer = GameSerializer(games, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def chat(self, request, pk=None):
        """Get chat messages for a match"""
        match = self.get_object()

        # Check if user is one of the players
        if request.user not in [match.player1, match.player2]:
            return Response(
                {'error': 'فقط بازیکنان می‌توانند چت را مشاهده کنند'},
                status=status.HTTP_403_FORBIDDEN
            )

        messages = match.chat_messages.all()
        serializer = MatchChatSerializer(messages, many=True)
        return Response(serializer.data)


class GameViewSet(viewsets.ModelViewSet):
    """ViewSet for managing games"""

    queryset = Game.objects.select_related(
        'match', 'winner', 'submitted_by', 'verified_by'
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['match', 'winner', 'is_verified']
    ordering_fields = ['game_number', 'played_at']
    ordering = ['game_number']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'create':
            return GameCreateSerializer
        return GameSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by match
        match_id = self.request.query_params.get('match_id')
        if match_id:
            queryset = queryset.filter(match_id=match_id)

        # Filter by user's games if not admin
        if not user.is_staff:
            queryset = queryset.filter(
                Q(match__player1=user) | Q(match__player2=user)
            )

        return queryset

    def perform_create(self, serializer):
        """Create a new game"""
        # Set submitted_by to current user
        game = serializer.save(submitted_by=self.request.user)

        # Update match scores
        match = game.match
        if game.winner == match.player1:
            match.player1_wins += 1
        else:
            match.player2_wins += 1

        # Check if match is complete
        wins_needed = match.wins_needed
        if match.player1_wins >= wins_needed or match.player2_wins >= wins_needed:
            winner = match.player1 if match.player1_wins >= wins_needed else match.player2
            match.complete_match(winner)
        else:
            match.save(update_fields=['player1_wins', 'player2_wins'])

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify a game (admin only)"""
        game = self.get_object()

        if game.verify(request.user):
            return Response({
                'message': 'بازی تایید شد',
                'game': GameSerializer(game).data
            })
        else:
            return Response(
                {'error': 'بازی قبلاً تایید شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MatchDisputeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing match disputes"""

    queryset = MatchDispute.objects.select_related(
        'match', 'game', 'reporter', 'resolved_by'
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['match', 'status', 'dispute_type', 'priority']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', '-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'create':
            return MatchDisputeCreateSerializer
        return MatchDisputeSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Admins see all disputes
        if user.is_staff:
            return queryset

        # Users see only their disputes
        return queryset.filter(reporter=user)

    def perform_create(self, serializer):
        """Create a new dispute"""
        # Set reporter to current user
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def start_review(self, request, pk=None):
        """Start reviewing a dispute (admin only)"""
        dispute = self.get_object()

        if dispute.start_review(request.user):
            return Response({
                'message': 'بررسی اعتراض شروع شد',
                'dispute': MatchDisputeSerializer(dispute).data
            })
        else:
            return Response(
                {'error': 'اعتراض در حالت مناسب برای شروع بررسی نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def resolve(self, request, pk=None):
        """Resolve a dispute (admin only)"""
        dispute = self.get_object()
        serializer = MatchDisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = serializer.validated_data['response']
        action_taken = serializer.validated_data.get('action', '')

        if dispute.resolve(request.user, response, action_taken):
            return Response({
                'message': 'اعتراض حل شد',
                'dispute': MatchDisputeSerializer(dispute).data
            })
        else:
            return Response(
                {'error': 'اعتراض در حالت مناسب برای حل نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a dispute (admin only)"""
        dispute = self.get_object()
        response = request.data.get('response', '')

        if not response:
            return Response(
                {'error': 'پاسخ الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if dispute.reject(request.user, response):
            return Response({
                'message': 'اعتراض رد شد',
                'dispute': MatchDisputeSerializer(dispute).data
            })
        else:
            return Response(
                {'error': 'اعتراض در حالت مناسب برای رد نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MatchChatViewSet(viewsets.ModelViewSet):
    """ViewSet for match chat"""

    queryset = MatchChat.objects.select_related('match', 'sender')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['match', 'sender', 'is_read']
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'create':
            return MatchChatCreateSerializer
        return MatchChatSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by match
        match_id = self.request.query_params.get('match_id')
        if match_id:
            # Check if user is one of the players
            match = get_object_or_404(Match, id=match_id)
            if user not in [match.player1, match.player2]:
                return queryset.none()
            queryset = queryset.filter(match_id=match_id)
        else:
            # Only show messages from user's matches
            queryset = queryset.filter(
                Q(match__player1=user) | Q(match__player2=user)
            )

        return queryset

    def perform_create(self, serializer):
        """Create a new chat message"""
        # Set sender to current user
        message = serializer.save(sender=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()

        # Only the recipient can mark as read
        match = message.match
        if request.user == message.sender:
            return Response(
                {'error': 'شما نمی‌توانید پیام خود را به عنوان خوانده شده علامت بزنید'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user not in [match.player1, match.player2]:
            return Response(
                {'error': 'شما مجاز به این عملیات نیستید'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.mark_as_read()
        return Response({
            'message': 'پیام به عنوان خوانده شده علامت خورد',
            'chat': MatchChatSerializer(message).data
        })
