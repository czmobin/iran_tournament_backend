from rest_framework import permissions


class IsTournamentParticipant(permissions.BasePermission):
    """
    Permission to check if user is tournament participant
    """
    def has_object_permission(self, request, view, obj):
        # Check if user is a participant in the tournament
        from .models import TournamentParticipant
        
        if hasattr(obj, 'tournament'):
            tournament = obj.tournament
        else:
            tournament = obj
        
        return TournamentParticipant.objects.filter(
            tournament=tournament,
            user=request.user,
            status__in=['confirmed', 'pending']
        ).exists()


class IsTournamentOwner(permissions.BasePermission):
    """
    Permission to check if user created the tournament
    """
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class CanRegisterTournament(permissions.BasePermission):
    """
    Permission to check if user can register for tournament
    """
    def has_object_permission(self, request, view, obj):
        from .models import TournamentParticipant
        
        # Check if tournament allows registration
        if not obj.can_register:
            return False
        
        # Check if user is already registered
        if TournamentParticipant.objects.filter(
            tournament=obj,
            user=request.user,
            status__in=['pending', 'confirmed']
        ).exists():
            return False
        
        return True


class IsInvitationRecipient(permissions.BasePermission):
    """
    Permission to check if user is invitation recipient
    """
    def has_object_permission(self, request, view, obj):
        return obj.invited_user == request.user