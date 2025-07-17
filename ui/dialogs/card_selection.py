"""
Card Selection Dialog - extracted from app.py
Shows available TCG cards for a Pokemon and allows selection
"""
import sqlite3
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                            QScrollArea, QGridLayout, QFrame, QWidget, QDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .common import BaseDialog
from cache.image_loader import ImageLoader
from data.database import DatabaseManager


class CardSelectionDialog(QDialog):
    """Dialog for selecting which TCG card to import - Much larger images"""
    
    def __init__(self, pokemon_name, card_ids, pokemon_id=None, image_loader=None, db_manager=None, parent=None):
        super().__init__(parent)
        self.pokemon_name = pokemon_name
        self.pokemon_id = pokemon_id
        self.card_ids = card_ids
        self.selected_card_id = None
        self.image_loader = image_loader or ImageLoader()
        self.db_manager = db_manager or DatabaseManager()
        self.selected_widget = None
        self.setWindowTitle(f"Select Card for {pokemon_name}")
        self.setMinimumWidth(1000)  # Much wider: was 800, now 1000
        self.setMinimumHeight(800)  # Much taller: was 600, now 800
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title with larger font
        title = QLabel(f"Select a TCG card for {self.pokemon_name}:")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))  # Larger font: was 14, now 16
        title.setStyleSheet("color: white; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # Card count info with larger font
        count_info = QLabel(f"Found {len(self.card_ids)} available cards")
        count_info.setStyleSheet("color: #bdc3c7; font-size: 13px; margin-bottom: 20px;")  # Larger font
        layout.addWidget(count_info)
        
        # Card grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #34495e;
                background-color: #2c3e50;
            }
        """)
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(20)  # Much more spacing: was 15, now 20
        
        row, col = 0, 0
        columns = 2  # Reduced from 3 to 2 for much larger cards
        
        for card_id in self.card_ids:
            card_info = self.get_card_info(self.db_manager, card_id)
            if card_info:
                card_widget = self.create_extra_large_card_widget(card_info)
                grid_layout.addWidget(card_widget, row, col)
                
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
        
        # Add some padding at the bottom
        grid_layout.setRowStretch(row + 1, 1)
        
        scroll_area.setWidget(grid_widget)
        layout.addWidget(scroll_area)
        
        # Buttons with larger size
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)  # Taller buttons: was 35, now 40
        cancel_btn.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        import_btn = QPushButton("Import Selected")
        import_btn.setMinimumHeight(40)  # Taller buttons
        import_btn.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        import_btn.clicked.connect(self.accept)
        import_btn.setEnabled(False)
        import_btn.setStyleSheet("""
            QPushButton:disabled {
                background-color: #7f8c8d;
                color: #bdc3c7;
            }
        """)
        self.import_btn = import_btn
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
    
    def create_extra_large_card_widget(self, card_info):
        """Create an extra large, detailed card widget"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        widget.setFixedSize(320, 500)  # Much larger: was 240x380, now 320x500
        widget.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 3px solid #3498db;
                background-color: #3d5a75;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)  # More padding
        layout.setSpacing(8)
        
        # Card image - Much larger
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedHeight(320)  # Much larger: was 220, now 320
        image_label.setScaledContents(False)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(image_label)
        
        # Load high-quality image with much larger size
        if card_info['image_url_large']:
            # Use large image for best quality
            self.image_loader.load_image(card_info['image_url_large'], 
                                       image_label, (300, 320))  # Much larger display
        elif card_info['image_url_small']:
            # Fallback to small image but display larger
            self.image_loader.load_image(card_info['image_url_small'], 
                                       image_label, (300, 320))
        else:
            image_label.setText("No Image\nAvailable")
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #2c3e50;
                    color: #7f8c8d;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 6px;
                }
            """)
        
        # Card info section with larger fonts
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        # Card name - Larger typography
        name_label = QLabel(card_info['name'])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))  # Larger font: was 10, now 12
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(50)  # More height for long names
        info_layout.addWidget(name_label)
        
        # Set info with larger styling
        set_label = QLabel(f"📦 Set: {card_info['set_name']}")
        set_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label.setStyleSheet("color: #3498db; font-size: 11px; font-weight: bold;")  # Larger font
        set_label.setWordWrap(True)
        info_layout.addWidget(set_label)
        
        # Rarity with larger color coding
        if card_info['rarity']:
            rarity_label = QLabel(f"⭐ {card_info['rarity']}")
            rarity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Color code rarities
            rarity_colors = {
                'Common': '#95a5a6',
                'Uncommon': '#3498db', 
                'Rare': '#e74c3c',
                'Rare Holo': '#e67e22',
                'Ultra Rare': '#9b59b6',
                'Secret Rare': '#f1c40f'
            }
            color = rarity_colors.get(card_info['rarity'], '#f39c12')
            rarity_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")  # Larger font
            info_layout.addWidget(rarity_label)
        
        # Artist info with larger font
        if card_info['artist']:
            artist_label = QLabel(f"🎨 Artist: {card_info['artist']}")
            artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            artist_label.setStyleSheet("color: #95a5a6; font-size: 10px;")  # Larger font
            info_layout.addWidget(artist_label)
        
        layout.addWidget(info_container)
        
        # Make clickable with better feedback
        widget.card_id = card_info['card_id']
        widget.card_info = card_info
        widget.mousePressEvent = lambda event: self.select_card(widget)
        
        # Add tooltip with full card name
        widget.setToolTip(f"{card_info['name']}\n{card_info['set_name']}\n{card_info['rarity'] or 'Unknown Rarity'}")
        
        return widget
    
    def select_card(self, widget):
        """Select a card with improved visual feedback"""
        # Deselect previous
        if self.selected_widget:
            self.selected_widget.setStyleSheet("""
                QFrame {
                    background-color: #34495e;
                    border: 2px solid #2c3e50;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border: 3px solid #3498db;
                    background-color: #3d5a75;
                }
            """)
        
        # Select new with enhanced styling
        widget.setStyleSheet("""
            QFrame {
                background-color: #2980b9;
                border: 4px solid #3498db;
                border-radius: 8px;
            }
        """)
        
        self.selected_widget = widget
        self.selected_card_id = widget.card_id
        self.import_btn.setEnabled(True)
        
        # Update button text to show selected card
        card_name = widget.card_info['name']
        if len(card_name) > 25:
            card_name = card_name[:22] + "..."
        self.import_btn.setText(f"Import '{card_name}'")
    
    def get_card_info(self, db_manager, card_id):
        """Get card information from database"""
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT card_id, name, set_name, artist, rarity, image_url_large, image_url_small
            FROM silver_tcg_cards 
            WHERE card_id = ?
        """, (card_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'card_id': result[0],
                'name': result[1],
                'set_name': result[2],
                'artist': result[3],
                'rarity': result[4],
                'image_url_large': result[5],
                'image_url_small': result[6]
            }
        return None
    
    def get_selected_card(self):
        """Get the selected card ID"""
        return self.selected_card_id