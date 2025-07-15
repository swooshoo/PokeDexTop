"""
Data Models - Type definitions for the application
Replaces scattered data structures throughout original app.py
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class PokemonData:
    """Pokemon master data model"""
    id: int
    name: str
    generation: int
    pokedex_numbers: List[int] = field(default_factory=list)
    card_count: int = 0
    available_cards: List[str] = field(default_factory=list)


@dataclass
class CardData:
    """TCG card data model"""
    card_id: str
    name: str
    pokemon_name: Optional[str] = None
    set_id: Optional[str] = None
    set_name: Optional[str] = None
    artist: Optional[str] = None
    rarity: Optional[str] = None
    supertype: Optional[str] = None
    subtypes: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    hp: Optional[str] = None
    number: Optional[str] = None
    image_url_small: Optional[str] = None
    image_url_large: Optional[str] = None
    national_pokedex_numbers: List[int] = field(default_factory=list)
    legalities: Dict[str, str] = field(default_factory=dict)
    market_prices: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SetData:
    """TCG set data model"""
    set_id: str
    name: str
    display_name: Optional[str] = None
    series: Optional[str] = None
    printed_total: int = 0
    total: int = 0
    release_date: Optional[str] = None
    symbol_url: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class CollectionItem:
    """User collection item model"""
    pokemon_id: int
    pokemon_name: str
    card_id: Optional[str] = None
    card_name: Optional[str] = None
    set_name: Optional[str] = None
    image_url: Optional[str] = None
    imported_at: Optional[datetime] = None
    collection_type: str = 'personal'
    has_tcg_card: bool = False
    
    def __post_init__(self):
        self.has_tcg_card = self.card_id is not None
        if self.imported_at is None:
            self.imported_at = datetime.now()


@dataclass
class ExportConfig:
    """Export configuration model"""
    custom_title: str = 'My Pokémon Collection'
    include_pokedex_info: bool = True
    include_set_label: bool = True
    include_artist_label: bool = False
    cards_per_row: int = 4
    image_quality: str = 'high'
    generation_filter: str = 'all'
    format: str = 'PNG'
    file_path: Optional[str] = None
    include_header: bool = True
    include_footer: bool = True


@dataclass
class CacheStats:
    """Cache statistics model"""
    total_files: int = 0
    total_size: int = 0
    cache_types: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class GenerationInfo:
    """Pokemon generation information"""
    generation: int
    name: str
    start_id: int
    end_id: int
    region: str
    total_pokemon: int = 0
    imported_pokemon: int = 0
    completion_rate: float = 0.0
    
    def __post_init__(self):
        if self.total_pokemon > 0:
            self.completion_rate = (self.imported_pokemon / self.total_pokemon) * 100


@dataclass
class SearchResult:
    """Search result model for cards and Pokemon"""
    result_type: str  # 'pokemon' or 'card'
    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CartItem:
    """Shopping cart item for browse tab"""
    card_id: str
    card_name: str
    pokemon_name: Optional[str] = None
    set_name: Optional[str] = None
    artist: Optional[str] = None
    rarity: Optional[str] = None
    image_url: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)


@dataclass
class ImportResult:
    """Result of card import operation"""
    success: bool
    pokemon_id: Optional[int] = None
    card_id: Optional[str] = None
    error_message: Optional[str] = None
    pokemon_name: Optional[str] = None
    card_name: Optional[str] = None


@dataclass
class SyncProgress:
    """Progress tracking for sync operations"""
    current: int = 0
    total: int = 0
    operation: str = "Initializing..."
    errors: List[str] = field(default_factory=list)
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100


@dataclass
class DatabaseStats:
    """Database statistics model"""
    pokemon_count: int = 0
    card_count: int = 0
    set_count: int = 0
    imported_count: int = 0
    recent_records: int = 0
    missing_images: int = 0
    
    @property
    def completion_rate(self) -> float:
        if self.pokemon_count == 0:
            return 0.0
        return (self.imported_count / self.pokemon_count) * 100


@dataclass
class ImageInfo:
    """Image information model"""
    url: str
    entity_id: str
    entity_type: str  # 'pokemon', 'card', 'set'
    image_type: str   # 'sprite', 'card_large', 'card_small', 'symbol', 'logo'
    cached_path: Optional[str] = None
    file_size: Optional[int] = None
    cached_at: Optional[datetime] = None


@dataclass
class QualityConfig:
    """Image quality configuration"""
    name: str
    max_width: int
    max_height: int
    jpeg_quality: int
    png_compression: int
    description: str = ""


@dataclass
class ExportProgress:
    """Export operation progress tracking"""
    stage: str = "Initializing"
    current_item: int = 0
    total_items: int = 0
    current_stage: int = 0
    total_stages: int = 5
    message: str = ""
    
    @property
    def item_percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.current_item / self.total_items) * 100
    
    @property
    def overall_percentage(self) -> float:
        if self.total_stages == 0:
            return 0.0
        stage_weight = 100 / self.total_stages
        completed_stages = (self.current_stage - 1) * stage_weight
        current_stage_progress = stage_weight * (self.item_percentage / 100)
        return completed_stages + current_stage_progress


@dataclass
class TeamUpMapping:
    """Team-up card Pokemon mapping"""
    card_id: str
    pokemon_names: List[str]
    positions: List[int]  # Position of each Pokemon in the team-up


@dataclass
class FilterCriteria:
    """Filter criteria for browsing cards"""
    pokemon_name: Optional[str] = None
    set_name: Optional[str] = None
    rarity: Optional[str] = None
    generation: Optional[int] = None
    has_image: Optional[bool] = None
    sort_by: str = "name"  # 'name', 'set', 'rarity', 'date'
    sort_order: str = "asc"  # 'asc', 'desc'
    limit: int = 200


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Type aliases for common structures
PokemonCollection = Dict[str, CollectionItem]
CardCollection = Dict[str, CardData]
SetCollection = Dict[str, SetData]