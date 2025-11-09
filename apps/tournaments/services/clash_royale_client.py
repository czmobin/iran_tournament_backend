"""
Clash Royale API Client Service
Handles all interactions with the official Clash Royale API
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone as dt_timezone
from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)


class ClashRoyaleAPIError(Exception):
    """Base exception for Clash Royale API errors"""
    pass


class ClashRoyaleClient:
    """
    Client for interacting with Clash Royale API

    Official API Documentation: https://developer.clashroyale.com/
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.CLASH_ROYALE_API_KEY
        self.base_url = settings.CLASH_ROYALE_API_URL

        if not self.api_key:
            logger.warning("Clash Royale API key not configured")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        })

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Clash Royale API

        Args:
            endpoint: API endpoint (e.g., '/players/%23ABC123')
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            ClashRoyaleAPIError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise ClashRoyaleAPIError(f"Resource not found: {endpoint}")
            elif response.status_code == 403:
                raise ClashRoyaleAPIError("Invalid API key or access denied")
            elif response.status_code == 429:
                raise ClashRoyaleAPIError("Rate limit exceeded")
            elif response.status_code == 503:
                raise ClashRoyaleAPIError("Clash Royale API is currently unavailable")
            else:
                raise ClashRoyaleAPIError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            raise ClashRoyaleAPIError("Request timed out")
        except requests.exceptions.ConnectionError:
            raise ClashRoyaleAPIError("Failed to connect to Clash Royale API")
        except requests.exceptions.RequestException as e:
            raise ClashRoyaleAPIError(f"Request failed: {str(e)}")

    @staticmethod
    def normalize_tag(tag: str) -> str:
        """
        Normalize player/tournament tag for API usage

        Args:
            tag: Player or tournament tag (e.g., '#ABC123' or 'ABC123')

        Returns:
            URL-encoded tag (e.g., '%23ABC123')
        """
        # Remove # if present
        tag = tag.replace('#', '')
        # Add # and URL encode
        return f"%23{tag.upper()}"

    def get_player(self, player_tag: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get player information by tag

        Args:
            player_tag: Player tag (e.g., '#ABC123')
            use_cache: Whether to use cached data (default: True)

        Returns:
            Player data dictionary or None if not found
        """
        cache_key = f"cr_player_{player_tag}"

        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Using cached player data for {player_tag}")
                return cached_data

        try:
            normalized_tag = self.normalize_tag(player_tag)
            endpoint = f"/players/{normalized_tag}"

            data = self._make_request(endpoint)

            # Cache for 5 minutes
            if data:
                cache.set(cache_key, data, timeout=300)

            logger.info(f"Successfully fetched player data for {player_tag}")
            return data

        except ClashRoyaleAPIError as e:
            logger.error(f"Failed to get player {player_tag}: {str(e)}")
            return None

    def get_player_battle_log(self, player_tag: str, use_cache: bool = False) -> List[Dict]:
        """
        Get player's battle log (last 25 battles)

        Args:
            player_tag: Player tag (e.g., '#ABC123')
            use_cache: Whether to use cached data (default: False for battle logs)

        Returns:
            List of battle dictionaries
        """
        cache_key = f"cr_battles_{player_tag}"

        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Using cached battle log for {player_tag}")
                return cached_data

        try:
            normalized_tag = self.normalize_tag(player_tag)
            endpoint = f"/players/{normalized_tag}/battlelog"

            data = self._make_request(endpoint)

            battles = data if isinstance(data, list) else []

            # Cache for 1 minute (battle logs change frequently)
            if battles:
                cache.set(cache_key, battles, timeout=60)

            logger.info(f"Successfully fetched {len(battles)} battles for {player_tag}")
            return battles

        except ClashRoyaleAPIError as e:
            logger.error(f"Failed to get battle log for {player_tag}: {str(e)}")
            return []

    def get_tournament(self, tournament_tag: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get tournament information by tag

        Args:
            tournament_tag: Tournament tag (e.g., '#ABC123')
            use_cache: Whether to use cached data (default: True)

        Returns:
            Tournament data dictionary or None if not found
        """
        cache_key = f"cr_tournament_{tournament_tag}"

        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Using cached tournament data for {tournament_tag}")
                return cached_data

        try:
            normalized_tag = self.normalize_tag(tournament_tag)
            endpoint = f"/tournaments/{normalized_tag}"

            data = self._make_request(endpoint)

            # Cache for 2 minutes
            if data:
                cache.set(cache_key, data, timeout=120)

            logger.info(f"Successfully fetched tournament data for {tournament_tag}")
            return data

        except ClashRoyaleAPIError as e:
            logger.error(f"Failed to get tournament {tournament_tag}: {str(e)}")
            return None

    def verify_player_tag(self, player_tag: str) -> bool:
        """
        Verify if a player tag exists and is valid

        Args:
            player_tag: Player tag to verify

        Returns:
            True if tag is valid, False otherwise
        """
        player_data = self.get_player(player_tag, use_cache=False)
        return player_data is not None

    def get_player_name(self, player_tag: str) -> Optional[str]:
        """
        Get player's display name

        Args:
            player_tag: Player tag

        Returns:
            Player name or None
        """
        player_data = self.get_player(player_tag)
        return player_data.get('name') if player_data else None

    @staticmethod
    def parse_battle_time(battle_time_str: str) -> datetime:
        """
        Parse battle time string from API to datetime

        Args:
            battle_time_str: Time string from API (e.g., '20231215T123456.000Z')

        Returns:
            Timezone-aware datetime object
        """
        # API returns format: 20231215T123456.000Z
        dt = datetime.strptime(battle_time_str, '%Y%m%dT%H%M%S.%fZ')
        return dt.replace(tzinfo=dt_timezone.utc)

    def extract_battle_data(self, battle: Dict, player_tag: str) -> Dict:
        """
        Extract and normalize battle data for a specific player

        Args:
            battle: Raw battle dictionary from API
            player_tag: The tag of the player we're tracking

        Returns:
            Normalized battle data
        """
        # Normalize player tag for comparison
        normalized_player_tag = player_tag.upper().replace('#', '')

        # Find player and opponent in the battle data
        battle_type = battle.get('type', 'other')
        game_mode = battle.get('gameMode', {}).get('name', '')
        battle_time = self.parse_battle_time(battle.get('battleTime'))

        # Extract team and opponent data
        team = battle.get('team', [])
        opponent = battle.get('opponent', [])

        if not team or not opponent:
            logger.warning(f"Battle missing team or opponent data")
            return {}

        # Get player data (usually first in team)
        player_data = team[0] if team else {}
        opponent_data = opponent[0] if opponent else {}

        # Determine winner
        player_crowns = player_data.get('crowns', 0)
        opponent_crowns = opponent_data.get('crowns', 0)

        is_winner = player_crowns > opponent_crowns
        is_draw = player_crowns == opponent_crowns

        # Extract arena info
        arena = battle.get('arena', {})

        # Extract cards
        player_cards = [
            {
                'name': card.get('name', ''),
                'id': card.get('id', 0),
                'level': card.get('level', 0),
            }
            for card in player_data.get('cards', [])
        ]

        opponent_cards = [
            {
                'name': card.get('name', ''),
                'id': card.get('id', 0),
                'level': card.get('level', 0),
            }
            for card in opponent_data.get('cards', [])
        ]

        return {
            'battle_time': battle_time,
            'battle_type': battle_type,
            'game_mode': game_mode,
            'player_tag': player_data.get('tag', '').replace('#', ''),
            'player_name': player_data.get('name', ''),
            'player_crowns': player_crowns,
            'player_king_tower_hp': player_data.get('kingTowerHitPoints'),
            'player_princess_towers_hp': player_data.get('princessTowersHitPoints', []),
            'opponent_tag': opponent_data.get('tag', '').replace('#', ''),
            'opponent_name': opponent_data.get('name', ''),
            'opponent_crowns': opponent_crowns,
            'opponent_king_tower_hp': opponent_data.get('kingTowerHitPoints'),
            'opponent_princess_towers_hp': opponent_data.get('princessTowersHitPoints', []),
            'is_winner': is_winner,
            'is_draw': is_draw,
            'player_cards': player_cards,
            'opponent_cards': opponent_cards,
            'arena_name': arena.get('name', ''),
            'arena_id': arena.get('id'),
            'raw_battle_data': battle,  # Store complete battle data
        }


# Singleton instance
_client_instance = None


def get_clash_royale_client() -> ClashRoyaleClient:
    """
    Get singleton instance of ClashRoyaleClient

    Returns:
        ClashRoyaleClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = ClashRoyaleClient()
    return _client_instance
