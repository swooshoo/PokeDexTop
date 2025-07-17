"""
Pokemon Card Widget - Individual Pokemon display component
Extracted from the monolithic app.py
"""

import sqlite3
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QMessageBox,
                            QDialog, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from cache.image_loader import ImageLoader
from data.database import DatabaseManager
from ui.dialogs.card_selection import CardSelectionDialog


class PokemonCard(QFrame):
    """
    Pokemon card widget with enhanced image support and card selection
    Shows either TCG card or game sprite based on collection status
    """
    
    # Signal emitted when a card is imported
    cardImported = pyqtSignal(str, str)  # pokemon_id, card_id
    
    def __init__(self, pokemon_data: Dict[str, Any], 
                 user_collection: Optional[Dict[str, Any]] = None,
                 image_loader: Optional[ImageLoader] = None,
                 db_manager: Optional[DatabaseManager] = None):
        super().__init__()
        
        self.pokemon_data = pokemon_data
        self.user_collection = user_collection or {}
        self.image_loader = image_loader
        self.db_manager = db_manager
        
        self.initUI()
    
    def initUI(self):
        """Initialize the Pokemon card UI"""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            PokemonCard {
                background-color: #34495e;
                border-radius: 8px;
                margin: 5px;
                border: 2px solid #2c3e50;
            }
            PokemonCard:hover {
                background-color: #3498db;
                border: 2px solid #2980b9;
            }
        """)
        
        self.setFixedWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Image container
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(220)
        self.image_label.setMaximumHeight(380)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("background-color: #2c3e50; border-radius: 6px;")
        
        # Load the appropriate image
        self.refresh_card_display()
        
        layout.addWidget(self.image_label, 1, Qt.AlignmentFlag.AlignCenter)
        
        # Pokemon info section
        info_container = self.create_info_section()
        layout.addWidget(info_container)
        
        self.setLayout(layout)
        
        # Make clickable only if cards are available
        card_count = self.pokemon_data.get('card_count', 0)
        if card_count > 0:
            self.mousePressEvent = self.show_card_selection
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def create_info_section(self) -> QFrame:
        """Create the Pokemon information section"""
        info_container = QFrame()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)
        
        # Pokemon name with Pokedex number
        name_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        name_label.setStyleSheet("""
            color: white; 
            background: transparent;
            padding: 5px;
            border-radius: 4px;
        """)
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Card availability status
        card_count = self.pokemon_data.get('card_count', 0)
        
        if card_count > 0:
            # Cards are available
            count_label = QLabel(f"{card_count} cards available")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("""
                color: #3498db; 
                font-size: 10px; 
                background: transparent;
                font-weight: bold;
            """)
            info_layout.addWidget(count_label)
        else:
            # No cards available
            no_cards_label = QLabel("No cards available")
            no_cards_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_cards_label.setStyleSheet("""
                color: #7f8c8d; 
                font-size: 10px; 
                background: transparent;
                font-style: italic;
            """)
            info_layout.addWidget(no_cards_label)
        
        return info_container
    
    def refresh_card_display(self):
        """Refresh the card display with proper TCG vs sprite loading"""
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        user_card = self.user_collection.get(str(pokemon_id))
        
        if user_card and user_card.get('image_url'):
            # TCG card loading - clean, no loading text
            self.image_label.setText("")
            self.image_label.setStyleSheet("""
                background-color: #2c3e50; 
                border-radius: 6px;
            """)
            
            # Load TCG card image
            if self.image_loader:
                self.image_loader.load_image(
                    user_card['image_url'], 
                    self.image_label, 
                    (260, 360),
                    entity_id=user_card.get('card_id'),
                    cache_type='tcg_card'
                )
            
            # Set tooltip
            tooltip_text = f"🃏 TCG Card: {user_card['card_name']}"
            if user_card.get('set_name'):
                tooltip_text += f"\n Set: {user_card['set_name']}"
            tooltip_text += f"\n\n Imported for #{pokemon_id} {pokemon_name}"
            tooltip_text += f"\n Click to change card"
            
            self.image_label.setToolTip(tooltip_text)
            
        else:
            # No TCG cards - load Pokémon game sprite
            sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
            
            # Set initial loading state for sprites
            self.image_label.setText(f"Loading\n#{pokemon_id}")
            self.image_label.setStyleSheet("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                border-radius: 6px; 
                color: #4a90e2;
                font-size: 10px;
                border: 2px dashed #87ceeb;
                padding: 15px;
            """)
            
            # Load game sprite
            if self.image_loader:
                self.image_loader.load_image(
                    sprite_url, 
                    self.image_label, 
                    (120, 120),
                    entity_id=str(pokemon_id),
                    cache_type='sprite'
                )
            
            # Set tooltip for sprite
            tooltip_text = f"🎮 #{pokemon_id} {pokemon_name}\n"
            tooltip_text += f"👾 Game Sprite\n"
            tooltip_text += f"📭 No TCG cards available\n"
            tooltip_text += f"🔄 Use 'Sync Data' to search for cards"
            self.image_label.setToolTip(tooltip_text)
    
    def show_card_selection(self, event):
        """Show card selection dialog"""
        if self.pokemon_data.get('card_count', 0) == 0:
            # No cards available - don't show dialog
            return
        
        pokemon_name = self.pokemon_data['name']
        available_cards = self.pokemon_data.get('available_cards', [])
        
        if not available_cards:
            # Try to fetch cards from database including team-ups
            available_cards = self.fetch_available_cards(pokemon_name)
        
        if not available_cards:
            QMessageBox.information(self, "No Cards", 
                f"No TCG cards found for {pokemon_name}.\n"
                "Use 'Sync Data' to search for cards.")
            return
        
        # Create card selection dialog
        dialog = CardSelectionDialog(
            pokemon_name,
            available_cards,
            pokemon_id=self.pokemon_data['id'],
            image_loader=self.image_loader,
            db_manager=self.db_manager,
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_card_id = dialog.get_selected_card()
            if selected_card_id:
                self.import_card(selected_card_id)
    
    def fetch_available_cards(self, pokemon_name: str) -> list:
        """Fetch available cards from database"""
        if not self.db_manager:
            return []
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT card_id FROM (
                SELECT card_id FROM silver_tcg_cards WHERE pokemon_name = ?
                UNION
                SELECT card_id FROM silver_team_up_cards WHERE pokemon_name = ?
            )
        """, (pokemon_name, pokemon_name))
        
        results = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in results]
    
    def import_card(self, card_id: str):
        """Import a card for this Pokemon"""
        if not self.db_manager:
            return
        
        pokemon_id = self.pokemon_data['id']
        
        # Add to database
        self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
        
        # Update local collection data
        self.user_collection[str(pokemon_id)] = self.get_card_details(card_id)
        
        # Refresh the display
        self.refresh_card_display()
        
        # Emit signal for parent to know about the import
        self.cardImported.emit(str(pokemon_id), card_id)
    
    def get_card_details(self, card_id: str) -> Dict[str, Any]:
        """Get card details from database"""
        if not self.db_manager:
            return {}
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT card_id, name, image_url_large, set_name
            FROM silver_tcg_cards
            WHERE card_id = ?
        """, (card_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'card_id': result[0],
                'card_name': result[1],
                'image_url': result[2],
                'set_name': result[3]
            }
        return {}
    
    def update_collection(self, user_collection: Dict[str, Any]):
        """Update the user collection and refresh display"""
        self.user_collection = user_collection
        self.refresh_card_display()
    
    def get_pokemon_data(self) -> Dict[str, Any]:
        """Get the Pokemon data for this card"""
        return self.pokemon_data.copy()
    
    def is_imported(self) -> bool:
        """Check if this Pokemon has been imported to collection"""
        pokemon_id = str(self.pokemon_data['id'])
        return pokemon_id in self.user_collection
    
    def get_imported_card_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the imported card, if any"""
        pokemon_id = str(self.pokemon_data['id'])
        return self.user_collection.get(pokemon_id)