from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchViewSet, GameViewSet, MatchChatViewSet

router = DefaultRouter()
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'games', GameViewSet, basename='game')
router.register(r'chats', MatchChatViewSet, basename='match-chat')

urlpatterns = router.urls
