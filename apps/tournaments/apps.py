from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tournaments'

    def ready(self):
        """
        Import signals when the app is ready.
        This ensures automatic chat creation for tournaments.
        """
        import apps.tournaments.signals  # noqa: F401
