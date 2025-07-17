"""
Export Widget Factory - Creates consistent, high-quality widgets for export
Implements the Widget Factory pattern from the hybrid strategy
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

from config.settings import WIDGET_DIMENSIONS, CACHE_CONFIG
from cache.manager import CacheManager
from export.widgets import ExportPokemonCard, ExportTCGCard, ExportSpriteCard


class ExportWidgetFactory:
    """
    Factory for creating export-quality widgets with proper caching and dimensions
    Centralizes all widget creation logic for consistent exports
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    @staticmethod
    def create_widget(item_data: Dict[str, Any], config: Dict[str, Any]) -> QFrame:
        """
        Main factory method - creates the appropriate widget for the given data
        
        Args:
            item_data: Data about the Pokemon/card to display
            config: Export configuration (quality, dimensions, etc.)
        
        Returns:
            Properly configured export widget
        """
        content_type = item_data.get('content_type')
        quality_level = config.get('image_quality', 'high')
        
        if content_type == 'tcg_card':
            return ExportWidgetFactory.create_tcg_card_widget(item_data, config)
        elif content_type == 'sprite':
            return ExportWidgetFactory.create_sprite_widget(item_data, config)
        elif content_type == 'pokemon_collection':
            return ExportWidgetFactory.create_pokemon_collection_widget(item_data, config)
        else:
            raise ValueError(f"Unknown content type: {content_type}")
    
    @staticmethod
    def create_tcg_card_widget(card_data: Dict[str, Any], config: Dict[str, Any]) -> ExportTCGCard:
        """
        Create export-quality TCG card widget
        
        Args:
            card_data: TCG card information
            config: Export configuration
        
        Returns:
            Configured ExportTCGCard widget
        """
        quality_level = config.get('image_quality', 'high')
        
        # Get widget dimensions from config
        widget_size = WIDGET_DIMENSIONS['export'][quality_level]['tcg_card']
        image_size = WIDGET_DIMENSIONS['export'][quality_level]['image_sizes']['tcg_card']
        
        # Create the widget
        widget = ExportTCGCard(card_data, config)
        widget.setFixedSize(*widget_size)
        widget.set_image_size(image_size)
        
        return widget
    
    @staticmethod
    def create_sprite_widget(pokemon_data: Dict[str, Any], config: Dict[str, Any]) -> ExportSpriteCard:
        """
        Create export-quality sprite widget
        
        Args:
            pokemon_data: Pokemon information
            config: Export configuration
        
        Returns:
            Configured ExportSpriteCard widget
        """
        quality_level = config.get('image_quality', 'high')
        
        # Get widget dimensions from config
        widget_size = WIDGET_DIMENSIONS['export'][quality_level]['sprite_card']
        image_size = WIDGET_DIMENSIONS['export'][quality_level]['image_sizes']['sprite']
        
        # Create the widget
        widget = ExportSpriteCard(pokemon_data, config)
        widget.setFixedSize(*widget_size)
        widget.set_image_size(image_size)
        
        return widget
    
    @staticmethod
    def create_pokemon_collection_widget(pokemon_data: Dict[str, Any], config: Dict[str, Any]) -> ExportPokemonCard:
        """
        Create export-quality Pokemon collection widget (TCG card or sprite fallback)
        
        Args:
            pokemon_data: Pokemon with collection information
            config: Export configuration
        
        Returns:
            Configured ExportPokemonCard widget
        """
        quality_level = config.get('image_quality', 'high')
        
        # Determine if this Pokemon has a TCG card or should show sprite
        has_tcg_card = pokemon_data.get('card_id') is not None
        
        if has_tcg_card:
            # Create TCG card version
            widget_size = WIDGET_DIMENSIONS['export'][quality_level]['pokemon_card']
            image_size = WIDGET_DIMENSIONS['export'][quality_level]['image_sizes']['tcg_card']
            content_type = 'tcg_card'
        else:
            # Create sprite version
            widget_size = WIDGET_DIMENSIONS['export'][quality_level]['sprite_card']
            image_size = WIDGET_DIMENSIONS['export'][quality_level]['image_sizes']['sprite']
            content_type = 'sprite'
        
        # Create the widget
        widget = ExportPokemonCard(pokemon_data, config, content_type)
        widget.setFixedSize(*widget_size)
        widget.set_image_size(image_size)
        
        return widget
    
    @staticmethod
    def get_widget_dimensions(content_type: str, quality: str) -> tuple:
        """
        Get widget dimensions for given content type and quality
        
        Args:
            content_type: 'tcg_card', 'sprite', 'pokemon_card'
            quality: 'high', 'medium', 'low'
        
        Returns:
            (width, height) tuple
        """
        try:
            return WIDGET_DIMENSIONS['export'][quality][content_type]
        except KeyError:
            # Fallback to high quality dimensions
            return WIDGET_DIMENSIONS['export']['high'].get(content_type, (280, 420))
    
    @staticmethod
    def get_image_dimensions(content_type: str, quality: str) -> tuple:
        """
        Get image dimensions for given content type and quality
        
        Args:
            content_type: 'tcg_card', 'sprite'
            quality: 'high', 'medium', 'low'
        
        Returns:
            (width, height) tuple
        """
        try:
            image_key = 'tcg_card' if content_type in ['tcg_card', 'pokemon_card'] else 'sprite'
            return WIDGET_DIMENSIONS['export'][quality]['image_sizes'][image_key]
        except KeyError:
            # Fallback dimensions
            if content_type in ['tcg_card', 'pokemon_card']:
                return (240, 336)  # Standard TCG card
            else:
                return (200, 200)  # Square sprite
    
    @staticmethod
    def calculate_grid_dimensions(item_count: int, cards_per_row: int) -> tuple:
        """
        Calculate grid dimensions for layout
        
        Args:
            item_count: Total number of items
            cards_per_row: Cards per row
        
        Returns:
            (rows, cols) tuple
        """
        import math
        rows = math.ceil(item_count / cards_per_row)
        cols = min(cards_per_row, item_count)
        return rows, cols
    
    @staticmethod
    def calculate_total_dimensions(item_count: int, cards_per_row: int, 
                                 widget_size: tuple, spacing: int = 15,
                                 header_height: int = 80, footer_height: int = 60) -> tuple:
        """
        Calculate total export image dimensions
        
        Args:
            item_count: Total number of items
            cards_per_row: Cards per row
            widget_size: (width, height) of individual widgets
            spacing: Spacing between widgets
            header_height: Height of header section
            footer_height: Height of footer section
        
        Returns:
            (total_width, total_height) tuple
        """
        import math
        
        widget_width, widget_height = widget_size
        rows = math.ceil(item_count / cards_per_row)
        
        # Calculate total width
        total_width = (cards_per_row * widget_width) + ((cards_per_row + 1) * spacing)
        
        # Calculate total height
        grid_height = (rows * widget_height) + ((rows + 1) * spacing)
        total_height = header_height + grid_height + footer_height
        
        return total_width, total_height


class ExportConfigValidator:
    """
    Validates export configuration and provides defaults
    """
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fill in missing export configuration values
        
        Args:
            config: Export configuration dictionary
        
        Returns:
            Validated and complete configuration
        """
        from config.settings import EXPORT_CONFIG
        
        validated = config.copy()
        
        # Validate quality level
        if 'image_quality' not in validated or validated['image_quality'] not in ['high', 'medium', 'low']:
            validated['image_quality'] = EXPORT_CONFIG['default_quality']
        
        # Validate cards per row
        cards_per_row = validated.get('cards_per_row', EXPORT_CONFIG['default_cards_per_row'])
        min_cards, max_cards = EXPORT_CONFIG['cards_per_row_range']
        validated['cards_per_row'] = max(min_cards, min(max_cards, cards_per_row))
        
        # Validate format
        if 'format' not in validated or validated['format'] not in EXPORT_CONFIG['supported_formats']:
            validated['format'] = EXPORT_CONFIG['default_format']
        
        # Validate title
        if 'custom_title' not in validated or not validated['custom_title'].strip():
            validated['custom_title'] = EXPORT_CONFIG['default_title']
        
        # Set defaults for optional settings
        defaults = {
            'include_pokedex_info': True,
            'include_set_label': True,
            'include_artist_label': False,
            'generation_filter': 'all',
            'include_header': True,
            'include_footer': True
        }
        
        for key, default_value in defaults.items():
            if key not in validated:
                validated[key] = default_value
        
        return validated


class ExportPreparationHelper:
    """
    Helper class for preparing data and cache for export
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def prepare_collection_data(self, collection: Dict[str, Any], config: Dict[str, Any]) -> list:
        """
        Prepare collection data for export, ensuring all images are cached
        
        Args:
            collection: User collection data
            config: Export configuration
        
        Returns:
            List of prepared item data dictionaries
        """
        prepared_items = []
        quality_level = f"export_{config['image_quality']}"
        
        for pokemon_id, collection_item in collection.items():
            item_data = {
                'pokemon_id': pokemon_id,
                'pokemon_name': collection_item.get('pokemon_name', f"Pokemon {pokemon_id}"),
                'content_type': 'pokemon_collection'
            }
            
            # Check if has TCG card
            if collection_item.get('card_id'):
                item_data.update({
                    'card_id': collection_item['card_id'],
                    'card_name': collection_item.get('card_name', ''),
                    'set_name': collection_item.get('set_name', ''),
                    'image_url': collection_item.get('image_url', ''),
                    'has_tcg_card': True
                })
                
                # Ensure TCG card is cached
                if item_data['image_url']:
                    self.cache_manager.cache_image(
                        item_data['image_url'], 
                        item_data['card_id'],
                        'tcg_card',
                        quality_level
                    )
            else:
                # Sprite fallback
                item_data.update({
                    'has_tcg_card': False,
                    'sprite_url': f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
                })
                
                # Ensure sprite is cached
                self.cache_manager.cache_image(
                    item_data['sprite_url'],
                    pokemon_id,
                    'sprite',
                    quality_level
                )
            
            prepared_items.append(item_data)
        
        return prepared_items
    
    def get_missing_cache_items(self, collection_data: list, quality_level: str) -> list:
        """
        Get list of items that need to be cached before export
        
        Args:
            collection_data: Prepared collection data
            quality_level: Required quality level
        
        Returns:
            List of items that need caching
        """
        missing_items = []
        
        for item in collection_data:
            if item.get('has_tcg_card'):
                cached_path = self.cache_manager.get_cached_path(
                    item['card_id'], 'tcg_card', quality_level
                )
                if not cached_path:
                    missing_items.append(item)
            else:
                cached_path = self.cache_manager.get_cached_path(
                    item['pokemon_id'], 'sprite', quality_level
                )
                if not cached_path:
                    missing_items.append(item)
        
        return missing_items