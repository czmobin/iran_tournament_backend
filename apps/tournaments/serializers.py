from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import Tournament, TournamentParticipant, TournamentInvitation


class UserBasicSerializer(serializers.Serializer):
    """Basic user info for nested serialization"""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    profile_picture = serializers.ImageField(read_only=True)
    clash_royale_tag = serializers.CharField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)


class TournamentListSerializer(serializers.ModelSerializer):
    """Serializer for tournament list"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    game_mode_display = serializers.CharField(source='get_game_mode_display', read_only=True)
    pricable_display = serializers.CharField(source='get_pricable_display', read_only=True)
    current_participants = serializers.IntegerField(source='current_participants_count', read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_register = serializers.BooleanField(read_only=True)
    prize_after_commission = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'slug', 'banner', 'game_mode', 'game_mode_display',
            'pricable', 'pricable_display', 'max_participants', 'current_participants',
            'entry_fee', 'prize_pool', 'prize_after_commission', 'registration_start',
            'registration_end', 'start_date', 'status', 'status_display',
            'is_featured', 'is_full', 'can_register', 'level_cap',
            'max_losses', 'time_duration', 'best_of', 'created_at'
        ]
        read_only_fields = ['current_participants', 'is_full', 'can_register', 'prize_after_commission']


class TournamentDetailSerializer(serializers.ModelSerializer):
    """Serializer for tournament detail"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    game_mode_display = serializers.CharField(source='get_game_mode_display', read_only=True)
    pricable_display = serializers.CharField(source='get_pricable_display', read_only=True)
    time_duration_display = serializers.CharField(source='get_time_duration_display', read_only=True)
    current_participants = serializers.IntegerField(source='current_participants_count', read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    can_register = serializers.BooleanField(read_only=True)
    prize_after_commission = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'slug', 'description', 'banner', 'game_mode',
            'game_mode_display', 'pricable', 'pricable_display', 'max_participants',
            'current_participants', 'level_cap', 'max_losses', 'time_duration',
            'time_duration_display', 'entry_fee', 'prize_pool', 'platform_commission',
            'prize_after_commission', 'registration_start', 'registration_end',
            'start_date', 'end_date', 'status', 'status_display', 'rules',
            'best_of', 'is_featured', 'created_by', 'total_participants',
            'total_matches', 'is_full', 'can_register', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'current_participants', 'is_full', 'can_register',
            'prize_after_commission', 'total_participants', 'total_matches'
        ]


class TournamentParticipantSerializer(serializers.ModelSerializer):
    """Serializer for tournament participants"""
    user = UserBasicSerializer(read_only=True)
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)
    tournament_slug = serializers.CharField(source='tournament.slug', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    win_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentParticipant
        fields = [
            'id', 'tournament', 'tournament_title', 'tournament_slug',
            'user', 'status', 'status_display', 'placement', 'prize_won',
            'matches_played', 'matches_won', 'win_rate',
            'disqualification_reason', 'joined_at'
        ]
        read_only_fields = [
            'tournament', 'user', 'status', 'placement',
            'prize_won', 'matches_played', 'matches_won'
        ]
    
    def get_win_rate(self, obj):
        """Calculate win rate"""
        if obj.matches_played == 0:
            return 0.0
        return round((obj.matches_won / obj.matches_played) * 100, 2)


class TournamentRegistrationSerializer(serializers.Serializer):
    """Serializer for tournament registration"""
    tournament_id = serializers.IntegerField()
    invitation_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_tournament_id(self, value):
        try:
            tournament = Tournament.objects.get(id=value)
        except Tournament.DoesNotExist:
            raise serializers.ValidationError("تورنومنت یافت نشد")
        
        if not tournament.can_register:
            raise serializers.ValidationError("امکان ثبت‌نام در این تورنومنت وجود ندارد")
        
        return value
    
    def validate(self, data):
        user = self.context['request'].user
        tournament = Tournament.objects.get(id=data['tournament_id'])
        
        # Check if already registered
        if TournamentParticipant.objects.filter(
            tournament=tournament,
            user=user,
            status__in=['pending', 'confirmed']
        ).exists():
            raise serializers.ValidationError("شما قبلاً در این تورنومنت ثبت‌نام کرده‌اید")
        
        return data


class TournamentInvitationSerializer(serializers.ModelSerializer):
    """Serializer for tournament invitations"""
    tournament = TournamentListSerializer(read_only=True)
    invited_user = UserBasicSerializer(read_only=True)
    invited_by = UserBasicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TournamentInvitation
        fields = [
            'id', 'tournament', 'invited_user', 'invited_by', 'code',
            'status', 'status_display', 'message', 'expires_at',
            'is_expired', 'created_at', 'responded_at'
        ]
        read_only_fields = ['code', 'status', 'responded_at', 'is_expired']


class TournamentLeaderboardSerializer(serializers.ModelSerializer):
    """Serializer for tournament leaderboard"""
    user = UserBasicSerializer(read_only=True)
    win_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentParticipant
        fields = [
            'placement', 'user', 'matches_played', 'matches_won',
            'win_rate', 'prize_won', 'status'
        ]
    
    def get_win_rate(self, obj):
        if obj.matches_played == 0:
            return 0.0
        return round((obj.matches_won / obj.matches_played) * 100, 2)


class TournamentStatsSerializer(serializers.Serializer):
    """Serializer for tournament statistics"""
    total_tournaments = serializers.IntegerField()
    active_tournaments = serializers.IntegerField()
    total_participants = serializers.IntegerField()
    total_prize_pool = serializers.DecimalField(max_digits=12, decimal_places=0)
    upcoming_tournaments = serializers.IntegerField()


class TournamentMinimalSerializer(serializers.ModelSerializer):
    """Minimal tournament info for listings"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'slug', 'banner', 'status', 'status_display',
            'prize_pool', 'entry_fee', 'start_date', 'is_featured'
        ]