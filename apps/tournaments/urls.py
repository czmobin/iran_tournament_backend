from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TournamentViewSet,
    TournamentParticipantViewSet,
    TournamentInvitationViewSet,
    PlayerBattleLogViewSet,
    TournamentRankingViewSet,
    TournamentChatViewSet
)

app_name = 'tournaments'

router = DefaultRouter()
router.register(r'', TournamentViewSet, basename='tournament')
router.register(r'participants', TournamentParticipantViewSet, basename='participant')
router.register(r'invitations', TournamentInvitationViewSet, basename='invitation')
router.register(r'battle-logs', PlayerBattleLogViewSet, basename='battle-log')
router.register(r'rankings', TournamentRankingViewSet, basename='ranking')
router.register(r'chat', TournamentChatViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
]
