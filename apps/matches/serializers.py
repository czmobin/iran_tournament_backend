from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Match, Game, MatchChat
from apps.accounts.serializers import UserBasicSerializer

User = get_user_model()


class GameSerializer(serializers.ModelSerializer):
    """Serializer for Game model"""

    winner_username = serializers.CharField(source='winner.username', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'match', 'game_number', 'winner', 'winner_username',
            'player1_crowns', 'player2_crowns',
            'player1_towers_destroyed', 'player2_towers_destroyed',
            'is_overtime', 'duration_seconds',
            'is_verified', 'verified_by', 'verified_by_username', 'verified_at',
            'submitted_by', 'submitted_by_username', 'played_at'
        ]
        read_only_fields = ['id', 'is_verified', 'verified_by', 'verified_at', 'played_at']

    def validate(self, data):
        """Validate game data"""
        match = data.get('match')
        winner = data.get('winner')
        player1_crowns = data.get('player1_crowns', 0)
        player2_crowns = data.get('player2_crowns', 0)

        # Validate winner is one of the match players
        if match and winner:
            if winner not in [match.player1, match.player2]:
                raise serializers.ValidationError('برنده باید یکی از بازیکنان مسابقه باشد')

        # Validate crowns
        if match and winner:
            if winner == match.player1 and player1_crowns <= player2_crowns:
                raise serializers.ValidationError('تعداد کرون برنده باید بیشتر باشد')
            if winner == match.player2 and player2_crowns <= player1_crowns:
                raise serializers.ValidationError('تعداد کرون برنده باید بیشتر باشد')

        # At least one player must have scored
        if player1_crowns == 0 and player2_crowns == 0:
            raise serializers.ValidationError('حداقل یک بازیکن باید امتیاز داشته باشد')

        return data


class GameCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a game"""

    class Meta:
        model = Game
        fields = [
            'match', 'game_number', 'winner',
            'player1_crowns', 'player2_crowns',
            'player1_towers_destroyed', 'player2_towers_destroyed',
            'is_overtime', 'duration_seconds', 'submitted_by'
        ]

    def validate(self, data):
        """Validate game creation"""
        match = data.get('match')
        winner = data.get('winner')

        # Check if match is ongoing
        if match and match.status != 'ongoing':
            raise serializers.ValidationError('مسابقه باید در حال انجام باشد')

        # Validate winner
        if match and winner and winner not in [match.player1, match.player2]:
            raise serializers.ValidationError('برنده باید یکی از بازیکنان باشد')

        return data


class MatchSerializer(serializers.ModelSerializer):
    """Serializer for Match model"""

    tournament_title = serializers.CharField(source='tournament.title', read_only=True)
    player1_username = serializers.CharField(source='player1.username', read_only=True)
    player2_username = serializers.CharField(source='player2.username', read_only=True)
    winner_username = serializers.CharField(source='winner.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)

    games = GameSerializer(many=True, read_only=True)
    games_count = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id', 'tournament', 'tournament_title', 'match_number',
            'player1', 'player1_username', 'player2', 'player2_username',
            'best_of', 'player1_wins', 'player2_wins',
            'winner', 'winner_username', 'status',
            'scheduled_time', 'started_at', 'completed_at',
            'player1_submitted_result', 'player2_submitted_result',
            'notes', 'admin_verified', 'verified_by', 'verified_by_username',
            'games', 'games_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'player1_wins', 'player2_wins', 'winner',
            'started_at', 'completed_at', 'admin_verified',
            'verified_by', 'created_at', 'updated_at'
        ]

    def get_games_count(self, obj):
        """Get the number of games played"""
        return obj.games.count()


class MatchListSerializer(serializers.ModelSerializer):
    """Minimal serializer for match listings"""

    tournament_title = serializers.CharField(source='tournament.title', read_only=True)
    player1_username = serializers.CharField(source='player1.username', read_only=True)
    player2_username = serializers.CharField(source='player2.username', read_only=True)
    winner_username = serializers.CharField(source='winner.username', read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'tournament', 'tournament_title', 'match_number',
            'player1', 'player1_username', 'player2', 'player2_username',
            'player1_wins', 'player2_wins', 'winner', 'winner_username',
            'status', 'scheduled_time', 'started_at', 'completed_at'
        ]


class MatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a match"""

    class Meta:
        model = Match
        fields = [
            'tournament', 'match_number', 'player1', 'player2',
            'best_of', 'scheduled_time', 'notes'
        ]

    def validate(self, data):
        """Validate match creation"""
        player1 = data.get('player1')
        player2 = data.get('player2')

        if player1 == player2:
            raise serializers.ValidationError('بازیکنان نمی‌توانند یکسان باشند')

        return data


class MatchUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a match"""

    class Meta:
        model = Match
        fields = ['scheduled_time', 'notes', 'status']


class SubmitMatchResultSerializer(serializers.Serializer):
    """Serializer for submitting match result"""

    winner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    player1_wins = serializers.IntegerField(min_value=0)
    player2_wins = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate match result submission"""
        match = self.context.get('match')
        winner = data.get('winner')

        if not match:
            raise serializers.ValidationError('مسابقه یافت نشد')

        if winner not in [match.player1, match.player2]:
            raise serializers.ValidationError('برنده باید یکی از بازیکنان باشد')

        return data



class MatchChatSerializer(serializers.ModelSerializer):
    """Serializer for MatchChat model"""

    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_profile_picture = serializers.ImageField(source='sender.profile_picture', read_only=True)

    class Meta:
        model = MatchChat
        fields = [
            'id', 'match', 'sender', 'sender_username', 'sender_profile_picture',
            'message', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_read', 'read_at', 'created_at']

    def validate(self, data):
        """Validate chat message"""
        match = data.get('match')
        sender = data.get('sender')

        if match and sender and sender not in [match.player1, match.player2]:
            raise serializers.ValidationError('فقط بازیکنان مسابقه می‌توانند پیام بفرستند')

        return data


class MatchChatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a chat message"""

    class Meta:
        model = MatchChat
        fields = ['match', 'message']

    def validate_message(self, value):
        """Validate message length"""
        if len(value) > 500:
            raise serializers.ValidationError('پیام نمی‌تواند بیشتر از 500 کاراکتر باشد')
        return value
