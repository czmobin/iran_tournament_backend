from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TournamentViewSet,
    TournamentParticipantViewSet,
    TournamentInvitationViewSet
)

app_name = 'tournaments'

router = DefaultRouter()
router.register(r'', TournamentViewSet, basename='tournament')
router.register(r'participants', TournamentParticipantViewSet, basename='participant')
router.register(r'invitations', TournamentInvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
]
