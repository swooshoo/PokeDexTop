"""
TCG API Client - Extracted from app.py lines 1650-1850
Pokemon TCG API client using the official SDK
"""

import time
import json
from typing import List, Dict, Any, Optional

# Pokemon TCG SDK imports
try:
    from pokemontcgsdk import Card, Set
    from pokemontcgsdk.restclient import RestClient, PokemonTcgException
except ImportError:
    print("Warning: Pokemon TCG SDK not installed. Run: pip install pokemontcgsdk")
    # Create dummy classes for development
    class Card:
        @staticmethod
        def where(**kwargs): return []
        @staticmethod
        def find(card_id): return None
    
    class Set:
        @staticmethod
        def all(): return []
        @staticmethod
        def find(set_id): return None
    
    class RestClient:
        @staticmethod
        def configure(api_key): pass
    
    class PokemonTcgException(Exception): pass

from data.database import DatabaseManager


class TCGAPIClient:
    """Pokemon TCG API client using the official SDK"""
    
    def __init__(self, db_manager: DatabaseManager, api_key: Optional[str] = None):
        self.db_manager = db_manager
        
        # Configure API key for higher rate limits
        if api_key:
            RestClient.configure(api_key)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def search_cards_by_pokemon_name(self, pokemon_name: str) -> List[Dict[str, Any]]:
        """Search cards by Pokemon name"""
        try:
            self._rate_limit()
            
            # Search for cards containing the Pokemon name
            query = f'name:"{pokemon_name}"'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                try:
                    # Convert card object to dict for storage
                    card_data = self._card_to_dict(card)
                    bronze_id = self.db_manager.store_bronze_card_data(card_data)
                    stored_cards.append(card_data)
                except Exception as store_error:
                    print(f"Warning: Failed to store card {card.id}: {store_error}")
                    # Still add the card data even if storage fails
                    card_data = self._card_to_dict(card)
                    stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error searching for {pokemon_name}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error searching for {pokemon_name}: {e}")
            return []
    
    def search_cards_by_pokedex_number(self, pokedex_number: int) -> List[Dict[str, Any]]:
        """Search cards by National Pokedex number"""
        try:
            self._rate_limit()
            
            query = f'nationalPokedexNumbers:{pokedex_number}'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                card_data = self._card_to_dict(card)
                self.db_manager.store_bronze_card_data(card_data)
                stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error for Pokedex #{pokedex_number}: {e}")
            return []
    
    def get_all_sets(self) -> List[Dict[str, Any]]:
        """Fetch all TCG sets"""
        try:
            self._rate_limit()
            
            sets = Set.all()
            stored_sets = []
            
            for tcg_set in sets:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
                stored_sets.append(set_data)
            
            return stored_sets
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching sets: {e}")
            return []
    
    def get_cards_from_set(self, set_id: str, page_size: int = 250) -> List[Dict[str, Any]]:
        """Get all cards from a specific set"""
        try:
            page = 1
            all_cards = []
            
            # First, get and store the set information
            self._rate_limit()
            tcg_set = Set.find(set_id)
            if tcg_set:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
            
            # Then get all cards from the set
            while True:
                self._rate_limit()
                
                query = f'set.id:{set_id}'
                cards = Card.where(q=query, page=page, pageSize=page_size)
                
                if not cards:
                    break
                
                for card in cards:
                    card_data = self._card_to_dict(card)
                    self.db_manager.store_bronze_card_data(card_data)
                    all_cards.append(card_data)
                
                page += 1
                
                # Safety break for large sets
                if page > 20:
                    break
            
            return all_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching set {set_id}: {e}")
            return []
    
    def _card_to_dict(self, card) -> Dict[str, Any]:
        """Convert Card object to dictionary for storage"""
        return {
            'id': card.id,
            'name': card.name,
            'supertype': card.supertype,
            'subtypes': card.subtypes or [],
            'types': card.types or [],
            'hp': card.hp,
            'evolvesFrom': card.evolvesFrom,
            'attacks': [self._attack_to_dict(attack) for attack in (card.attacks or [])],
            'weaknesses': [self._weakness_to_dict(w) for w in (card.weaknesses or [])],
            'resistances': [self._resistance_to_dict(r) for r in (card.resistances or [])],
            'retreatCost': card.retreatCost or [],
            'convertedRetreatCost': card.convertedRetreatCost,
            'set': self._set_to_dict(card.set),
            'number': card.number,
            'artist': card.artist,
            'rarity': card.rarity,
            'flavorText': card.flavorText,
            'nationalPokedexNumbers': card.nationalPokedexNumbers or [],
            'legalities': self._legalities_to_dict(card.legalities),
            'images': {
                'small': card.images.small,
                'large': card.images.large
            } if card.images else {},
            'tcgplayer': self._tcgplayer_to_dict(card.tcgplayer) if card.tcgplayer else {}
        }
    
    def _set_to_dict(self, tcg_set) -> Dict[str, Any]:
        """Convert Set object to dictionary"""
        return {
            'id': tcg_set.id,
            'name': tcg_set.name,
            'series': tcg_set.series,
            'printedTotal': tcg_set.printedTotal,
            'total': tcg_set.total,
            'legalities': self._legalities_to_dict(tcg_set.legalities),
            'ptcgoCode': tcg_set.ptcgoCode,
            'releaseDate': tcg_set.releaseDate,
            'updatedAt': tcg_set.updatedAt,
            'images': {
                'symbol': tcg_set.images.symbol,
                'logo': tcg_set.images.logo
            } if tcg_set.images else {}
        }
    
    def _attack_to_dict(self, attack) -> Dict[str, Any]:
        """Convert Attack object to dictionary"""
        return {
            'name': attack.name,
            'cost': attack.cost or [],
            'convertedEnergyCost': attack.convertedEnergyCost,
            'damage': attack.damage,
            'text': attack.text
        }
    
    def _weakness_to_dict(self, weakness) -> Dict[str, Any]:
        """Convert Weakness object to dictionary"""
        return {
            'type': weakness.type,
            'value': weakness.value
        }
    
    def _resistance_to_dict(self, resistance) -> Dict[str, Any]:
        """Convert Resistance object to dictionary"""
        return {
            'type': resistance.type,
            'value': resistance.value
        }
    
    def _legalities_to_dict(self, legalities) -> Dict[str, Any]:
        """Convert Legalities object to dictionary"""
        if not legalities:
            return {}
        
        return {
            'unlimited': legalities.unlimited,
            'expanded': legalities.expanded,
            'standard': legalities.standard
        }
    
    def _tcgplayer_to_dict(self, tcgplayer) -> Dict[str, Any]:
        """Convert TCGPlayer object to dictionary"""
        return {
            'url': tcgplayer.url,
            'updatedAt': tcgplayer.updatedAt,
            'prices': self._prices_to_dict(tcgplayer.prices) if tcgplayer.prices else {}
        }
    
    def _prices_to_dict(self, prices) -> Dict[str, Any]:
        """Convert TCGPrices object to dictionary"""
        result = {}
        
        if prices.normal:
            result['normal'] = self._price_to_dict(prices.normal)
        if prices.holofoil:
            result['holofoil'] = self._price_to_dict(prices.holofoil)
        if prices.reverseHolofoil:
            result['reverseHolofoil'] = self._price_to_dict(prices.reverseHolofoil)
        if prices.firstEditionNormal:
            result['firstEditionNormal'] = self._price_to_dict(prices.firstEditionNormal)
        if prices.firstEditionHolofoil:
            result['firstEditionHolofoil'] = self._price_to_dict(prices.firstEditionHolofoil)
        
        return result
    
    def _price_to_dict(self, price) -> Dict[str, Any]:
        """Convert TCGPrice object to dictionary"""
        return {
            'low': price.low,
            'mid': price.mid,
            'high': price.high,
            'market': price.market,
            'directLow': price.directLow
        }