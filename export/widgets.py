"""
Export-optimized widget classes for high-quality rendering
These widgets are designed specifically for export, not UI interaction
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor

from cache.manager import CacheManager


class BaseExportWidget(QFrame):
    """
    Base class for all export widgets with common functionality
    """
    
    def __init__(self, data: Dict[str, Any], config: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.config = config
        self.image_size = (240, 336)  # Default TCG card size
        self.cached_image_path = None
        
        # Set common styling
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
                margin: 0px;
                border: 2px solid #2c3e50;
            }
        """)
    
    def set_image_size(self, size: Tuple[int, int]):
        """Set the target image size for this widget"""
        self.image_size = size
    
    def load_cached_image(self, entity_id: str, cache_type: str, cache_manager: CacheManager) -> Optional[QPixmap]:
        """
        Load image from cache with proper quality
        
        Args:
            entity_id: Pokemon ID or Card ID
            cache_type: 'tcg_card', 'sprite', 'artwork'
            cache_manager: CacheManager instance
        
        Returns:
            QPixmap if successful, None otherwise
        """
        quality_level = f"export_{self.config.get('image_quality', 'high')}"
        
        cached_path = cache_manager.get_cached_path(entity_id, cache_type, quality_level)
        
        if cached_path and cached_path.exists():
            pixmap = QPixmap(str(cached_path))
            if not pixmap.isNull():
                # Single high-quality scaling operation (legacy approach)
                return pixmap.scaled(
                    self.image_size[0], self.image_size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
        
        return None
    
    def create_placeholder_image(self, text: str = "No Image") -> QPixmap:
        """Create a placeholder image for missing images"""
        pixmap = QPixmap(self.image_size[0], self.image_size[1])
        pixmap.fill(QColor(52, 73, 94))  # Dark gray
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(127, 140, 141))
        painter.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        
        rect = pixmap.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        
        return pixmap


class ExportTCGCard(BaseExportWidget):
    """
    Export-optimized TCG card widget
    Designed for high-quality export rendering
    """
    
    def __init__(self, card_data: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(card_data, config)
        self.initUI()
    
    def initUI(self):
        """Initialize the TCG card UI for export"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Card image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(int(self.image_size[1]))
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Card information section
        if self.config.get('include_card_info', True):
            info_layout = self.create_card_info_section()
            layout.addLayout(info_layout)
        
        # Load the cached image
        self.load_card_image()
    
    def create_card_info_section(self) -> QVBoxLayout:
        """Create the card information section"""
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Card name
        card_name = self.data.get('card_name', self.data.get('name', 'Unknown Card'))
        name_label = QLabel(card_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(45)
        info_layout.addWidget(name_label)
        
        # Set information
        if self.config.get('include_set_label', True) and self.data.get('set_name'):
            set_label = QLabel(f"📦 {self.data['set_name']}")
            set_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            set_label.setStyleSheet("color: #3498db; font-size: 10px; font-weight: bold;")
            set_label.setWordWrap(True)
            info_layout.addWidget(set_label)
        
        # Artist information
        if self.config.get('include_artist_label', False) and self.data.get('artist'):
            artist_label = QLabel(f"🎨 {self.data['artist']}")
            artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            artist_label.setStyleSheet("color: #95a5a6; font-size: 9px;")
            info_layout.addWidget(artist_label)
        
        return info_layout
    
    def load_card_image(self):
        """Load the card image from cache"""
        # This would typically use the cache manager
        # For now, create a placeholder
        card_id = self.data.get('card_id')
        if card_id:
            # In real implementation, this would use cache_manager
            # placeholder for now
            placeholder = self.create_placeholder_image("TCG Card")
            self.image_label.setPixmap(placeholder)
        else:
            placeholder = self.create_placeholder_image("No Card")
            self.image_label.setPixmap(placeholder)


class ExportSpriteCard(BaseExportWidget):
    """
    Export-optimized sprite card widget
    Shows Pokemon game sprites with styling
    """
    
    def __init__(self, pokemon_data: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(pokemon_data, config)
        self.image_size = (200, 200)  # Square for sprites
        self.initUI()
    
    def initUI(self):
        """Initialize the sprite card UI for export"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Sprite image with special styling
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(int(self.image_size[1]))
        self.image_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                border-radius: 6px;
                border: 2px solid #4a90e2;
                padding: 8px;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Pokemon information
        if self.config.get('include_pokedex_info', True):
            info_layout = self.create_pokemon_info_section()
            layout.addLayout(info_layout)
        
        # Load the cached sprite
        self.load_sprite_image()
    
    def create_pokemon_info_section(self) -> QVBoxLayout:
        """Create the Pokemon information section"""
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Pokemon name with Pokedex number
        pokemon_id = self.data.get('pokemon_id', '')
        pokemon_name = self.data.get('pokemon_name', f'Pokemon {pokemon_id}')
        
        name_label = QLabel(f"#{pokemon_id:03d} {pokemon_name}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Generation information
        generation = self.data.get('generation')
        if generation:
            gen_label = QLabel(f"Generation {generation}")
            gen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            gen_label.setStyleSheet("color: #4a90e2; font-size: 10px; font-weight: bold;")
            info_layout.addWidget(gen_label)
        
        return info_layout
    
    def load_sprite_image(self):
        """Load the sprite image from cache"""
        pokemon_id = self.data.get('pokemon_id')
        if pokemon_id:
            # Create placeholder for sprite
            placeholder = self.create_placeholder_image(f"#{pokemon_id}")
            self.image_label.setPixmap(placeholder)
        else:
            placeholder = self.create_placeholder_image("No Sprite")
            self.image_label.setPixmap(placeholder)


class ExportPokemonCard(BaseExportWidget):
    """
    Export-optimized Pokemon collection card widget
    Can display either TCG card or sprite based on availability
    """
    
    def __init__(self, pokemon_data: Dict[str, Any], config: Dict[str, Any], content_type: str = 'tcg_card'):
        super().__init__(pokemon_data, config)
        self.content_type = content_type
        
        # Set image size based on content type
        if content_type == 'tcg_card':
            self.image_size = (240, 336)
        else:  # sprite
            self.image_size = (200, 200)
        
        self.initUI()
    
    def initUI(self):
        """Initialize the Pokemon collection card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Image section
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(int(self.image_size[1] * 0.75))
        
        # Apply appropriate styling based on content type
        if self.content_type == 'tcg_card':
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #2c3e50;
                    border-radius: 6px;
                    border: 1px solid #34495e;
                }
            """)
        else:  # sprite
            self.image_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                    border-radius: 6px;
                    border: 2px solid #4a90e2;
                    padding: 8px;
                }
            """)
        
        layout.addWidget(self.image_label)
        
        # Pokemon information section
        if self.config.get('include_pokedex_info', True):
            info_layout = self.create_pokemon_info_section()
            layout.addLayout(info_layout)
        
        # Load the appropriate image
        self.load_pokemon_image()
    
    def create_pokemon_info_section(self) -> QVBoxLayout:
        """Create the Pokemon information section"""
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Pokemon name with Pokedex number
        pokemon_id = self.data.get('pokemon_id', '')
        pokemon_name = self.data.get('pokemon_name', f'Pokemon {pokemon_id}')
        
        name_label = QLabel(f"#{pokemon_id:03d} {pokemon_name}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Additional info based on content type
        if self.content_type == 'tcg_card':
            # Show set information for TCG cards
            if self.config.get('include_set_label', True) and self.data.get('set_name'):
                set_label = QLabel(f"📦 {self.data['set_name']}")
                set_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                set_label.setStyleSheet("color: #3498db; font-size: 10px; font-weight: bold;")
                set_label.setWordWrap(True)
                info_layout.addWidget(set_label)
        else:
            # Show generation for sprites
            generation = self.data.get('generation')
            if generation:
                gen_label = QLabel(f"Generation {generation}")
                gen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                gen_label.setStyleSheet("color: #4a90e2; font-size: 10px; font-weight: bold;")
                info_layout.addWidget(gen_label)
        
        return info_layout
    
    def load_pokemon_image(self):
        """Load the appropriate image (TCG card or sprite)"""
        if self.content_type == 'tcg_card' and self.data.get('card_id'):
            # Load TCG card
            placeholder = self.create_placeholder_image("TCG Card")
            self.image_label.setPixmap(placeholder)
        else:
            # Load sprite
            pokemon_id = self.data.get('pokemon_id', '')
            placeholder = self.create_placeholder_image(f"#{pokemon_id}")
            self.image_label.setPixmap(placeholder)


class ExportHeaderWidget(QFrame):
    """
    Export header widget with collection title and metadata
    """
    
    def __init__(self, config: Dict[str, Any], collection_stats: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.collection_stats = collection_stats
        self.initUI()
    
    def initUI(self):
        """Initialize the header UI"""
        self.setStyleSheet("""
            QFrame {
                background-color: #52, 73, 94;
                border-radius: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        # Collection title
        title = self.config.get('custom_title', 'My Pokémon Collection')
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)
        
        # Collection statistics
        total_cards = self.collection_stats.get('total_cards', 0)
        generation_filter = self.config.get('generation_filter', 'all')
        
        if generation_filter == 'all':
            subtitle = f"{total_cards} cards from all generations"
        else:
            subtitle = f"{total_cards} cards from Generation {generation_filter}"
        
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont('Arial', 14))
        subtitle_label.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(subtitle_label)


class ExportFooterWidget(QFrame):
    """
    Export footer widget with export date and branding
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.initUI()
    
    def initUI(self):
        """Initialize the footer UI"""
        from datetime import datetime
        
        self.setStyleSheet("""
            QFrame {
                background-color: #52, 73, 94;
                border-radius: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(5)
        
        # Export date
        export_date = datetime.now().strftime('%B %d, %Y')
        date_label = QLabel(f"Exported on {export_date}")
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_label.setFont(QFont('Arial', 12))
        date_label.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(date_label)
        
        # Branding
        branding_label = QLabel("Exported by PokéDextop")
        branding_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        branding_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        branding_label.setStyleSheet("color: #3498db;")
        layout.addWidget(branding_label)