# ui/widgets/pokemon_card.py - REPLACE the entire class

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
                 db_manager: Optional[DatabaseManager] = None,
                 auto_load: bool = False):  # ✅ ADD auto_load parameter
        super().__init__()
        
        self.pokemon_data = pokemon_data
        self.user_collection = user_collection or {}
        self.image_loader = image_loader
        self.db_manager = db_manager
        self.auto_load = auto_load  # ✅ NEW: Control automatic loading
        
        self.image_label = None  # Will be set in initUI
        
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
        self.image_label.setFixedSize(260, 360)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Pokemon info
        info_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        info_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(info_label)
        
        # Card count info
        card_count = self.pokemon_data.get('card_count', 0)
        if card_count > 0:
            count_label = QLabel(f"📦 {card_count} TCG cards available")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("color: #3498db; font-size: 10px; background: transparent;")
            layout.addWidget(count_label)
        
        self.setLayout(layout)
        
        # ✅ CONDITIONAL LOADING: Only auto-load if enabled
        if self.auto_load:
            self.refresh_card_display()
        else:
            self.show_placeholder()
        
        # ✅ KEEP EXISTING CLICK LOGIC: Card selection, not image loading
        self.mousePressEvent = self.handle_click
    
    def show_placeholder(self):
        """Show placeholder without loading images"""
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        
        self.image_label.setText(f"#{pokemon_id}\n{pokemon_name}")
        self.image_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #ecf0f1, stop: 1 #bdc3c7);
                border-radius: 6px; 
                border: 2px solid #95a5a6;
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
            }
        """)
    
    def refresh_card_display(self):
        """Refresh the card display with proper TCG vs sprite loading"""
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        user_card = self.user_collection.get(str(pokemon_id))
        
        if user_card and user_card.get('image_url'):
            # ✅ TCG CARD LOADING - load imported card automatically
            self.image_label.setText("")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #2c3e50; 
                    border-radius: 6px;
                    border: 1px solid #34495e;
                }
            """)
            
            # Fix entity_id for TCG cards
            entity_id = (user_card.get('card_id') or 
                         user_card.get('id') or 
                         str(pokemon_id))
            
            # Load TCG card image automatically
            if self.image_loader:
                self.image_loader.load_image(
                    user_card['image_url'], 
                    self.image_label, 
                    (260, 360),
                    entity_id=entity_id,
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
            # ✅ SPRITE LOADING - load sprite automatically if auto_load enabled
            self.image_label.setText(f"#{pokemon_id}\n{pokemon_name}")
            self.image_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                    border-radius: 6px; 
                    border: 2px solid #95a5a6;
                    color: #2c3e50;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 8px;
                }
            """)
            
            # Load sprite automatically if auto_load is enabled
            if self.auto_load and self.image_loader:
                self.image_loader.load_image(
                    f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png",
                    self.image_label,
                    (260, 360),
                    entity_id=str(pokemon_id),
                    cache_type='sprite'
                )
            
            # Set tooltip
            tooltip_text = f"🎯 #{pokemon_id} {pokemon_name}"
            if self.pokemon_data.get('card_count', 0) > 0:
                tooltip_text += f"\n💼 {self.pokemon_data['card_count']} TCG cards available"
                tooltip_text += f"\n🔍 Click to browse and import cards"
            else:
                tooltip_text += f"\n❌ No TCG cards found"
            
            self.image_label.setToolTip(tooltip_text)

    # ✅ EXISTING CLICK LOGIC - Keep your existing implementation
    def handle_click(self, event):
        """Handle card clicks for importing cards"""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        
        pokemon_name = self.pokemon_data['name']
        available_cards = self.fetch_available_cards(pokemon_name)
        
        if not available_cards:
            QMessageBox.information(self, "No Cards Available", 
                f"No TCG cards found for {pokemon_name}.")
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