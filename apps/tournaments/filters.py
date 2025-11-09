import django_filters
from django.utils import timezone
from .models import Tournament, TournamentParticipant


class TournamentFilter(django_filters.FilterSet):
    """Advanced filtering for tournaments"""
    
    # Date range filters
    registration_start_after = django_filters.DateTimeFilter(
        field_name='registration_start',
        lookup_expr='gte'
    )
    registration_start_before = django_filters.DateTimeFilter(
        field_name='registration_start',
        lookup_expr='lte'
    )
    start_date_after = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='gte'
    )
    start_date_before = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='lte'
    )
    
    # Prize pool range
    min_prize = django_filters.NumberFilter(
        field_name='prize_pool',
        lookup_expr='gte'
    )
    max_prize = django_filters.NumberFilter(
        field_name='prize_pool',
        lookup_expr='lte'
    )
    
    # Entry fee range
    min_entry_fee = django_filters.NumberFilter(
        field_name='entry_fee',
        lookup_expr='gte'
    )
    max_entry_fee = django_filters.NumberFilter(
        field_name='entry_fee',
        lookup_expr='lte'
    )
    
    # Custom filters
    has_space = django_filters.BooleanFilter(
        method='filter_has_space',
        label='Has available space'
    )
    
    is_active = django_filters.BooleanFilter(
        method='filter_is_active',
        label='Is currently active'
    )
    
    can_register_now = django_filters.BooleanFilter(
        method='filter_can_register',
        label='Can register now'
    )
    
    class Meta:
        model = Tournament
        fields = {
            'status': ['exact', 'in'],
            'game_mode': ['exact', 'in'],
            'pricable': ['exact'],
            'is_featured': ['exact'],
            'level_cap': ['exact', 'gte', 'lte'],
            'max_losses': ['exact', 'gte', 'lte'],
            'time_duration': ['exact'],
        }
    
    def filter_has_space(self, queryset, name, value):
        """Filter tournaments that have available space"""
        if value:
            from django.db.models import Count, F
            queryset = queryset.annotate(
                confirmed_count=Count(
                    'participants',
                    filter=django_filters.Q(participants__status='confirmed')
                )
            ).filter(confirmed_count__lt=F('max_participants'))
        return queryset
    
    def filter_is_active(self, queryset, name, value):
        """Filter active tournaments"""
        if value:
            queryset = queryset.filter(
                status__in=['registration', 'ready', 'ongoing']
            )
        else:
            queryset = queryset.exclude(
                status__in=['registration', 'ready', 'ongoing']
            )
        return queryset
    
    def filter_can_register(self, queryset, name, value):
        """Filter tournaments that are open for registration"""
        if value:
            now = timezone.now()
            from django.db.models import Count, F
            queryset = queryset.filter(
                status='registration',
                registration_start__lte=now,
                registration_end__gte=now
            ).annotate(
                confirmed_count=Count(
                    'participants',
                    filter=django_filters.Q(participants__status='confirmed')
                )
            ).filter(confirmed_count__lt=F('max_participants'))
        return queryset


class ParticipantFilter(django_filters.FilterSet):
    """Filtering for tournament participants"""
    
    tournament_slug = django_filters.CharFilter(
        field_name='tournament__slug',
        lookup_expr='exact'
    )
    
    tournament_status = django_filters.CharFilter(
        field_name='tournament__status',
        lookup_expr='exact'
    )
    
    has_placement = django_filters.BooleanFilter(
        method='filter_has_placement'
    )
    
    min_matches_played = django_filters.NumberFilter(
        field_name='matches_played',
        lookup_expr='gte'
    )
    
    class Meta:
        model = TournamentParticipant
        fields = {
            'status': ['exact', 'in'],
            'placement': ['exact', 'gte', 'lte'],
            'matches_played': ['exact', 'gte'],
            'matches_won': ['exact', 'gte'],
        }
    
    def filter_has_placement(self, queryset, name, value):
        """Filter participants with/without placement"""
        if value:
            queryset = queryset.filter(placement__isnull=False)
        else:
            queryset = queryset.filter(placement__isnull=True)
        return queryset