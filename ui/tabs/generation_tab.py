"""
Generation Tab - Extracted from original app.py lines 2100-2250
Shows Pokemon by generation with collection status
"""

import sqlite3
from typing import Dict, Any, Optional

# PyQt6 imports
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGridLayout, QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# Internal imports
from data.database import DatabaseManager
from data.models import PokemonData, CollectionItem
from cache.image_loader import ImageLoader
from ui.widgets.pokemon_card import PokemonCard

class GenerationTab(QWidget):
    """Generation tab with Bronze-Silver-Gold data integration"""
    
    def __init__(self, gen_name, generation_num, db_manager, image_loader=None):
        super().__init__()
        self.gen_name = gen_name
        self.generation_num = generation_num
        self.db_manager = db_manager
        self.image_loader = image_loader or ImageLoader()
        self.pokemon_cards = []  # Keep track of pokemon cards for updates
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel(self.gen_name)
        title_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label, 3)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip("Refresh Pokemon data from database")
        refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_button, 1)
        
        main_layout.addLayout(header_layout)
        
        # Stats
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(self.stats_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #34495e;")
        main_layout.addWidget(line)
        
        # Scroll area for Pokemon grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #2c3e50;")
        
        # Load initial data
        self.refresh_data()
        
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
    
    def refresh_data(self):
        """Refresh Pokemon data from Gold layer"""
        # Cancel any pending image loads before clearing
        if hasattr(self, 'image_loader'):
            # If we want to be extra safe, we could cancel all pending requests
            # self.image_loader.cancel_all_requests()  # Uncomment if you add this method
            pass
        
        # Clear existing cards
        self.pokemon_cards.clear()
        
        # Clear the scroll area widget to ensure old widgets are deleted
        if self.scroll_area.widget():
            self.scroll_area.widget().deleteLater()
            QApplication.processEvents()  # Process deletion events
        
        # Get Pokemon for this generation
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        # Update stats
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        
        # Count Pokemon that have cards available
        pokemon_with_cards = len([p for p in pokemon_data.values() if p.get('card_count', 0) > 0])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        # Enhanced stats display
        self.stats_label.setText(
            f"Pokédex: {total_pokemon} | With TCG Cards: {pokemon_with_cards} | "
            f"Imported: {imported_count} | Total Available Cards: {total_cards}"
        )
        
        # Create grid widget
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: #2c3e50;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(15)
        
        # Set up grid
        columns = 4
        for i in range(columns):
            grid_layout.setColumnStretch(i, 1)
        
        # Add ALL Pokemon cards in Pokédex order
        row, col = 0, 0
        
        # Ensure we show Pokemon in correct Pokédex order
        sorted_pokemon = sorted(pokemon_data.items(), key=lambda x: int(x[0]))
        
        for pokemon_id, pokemon_info in sorted_pokemon:
            pokemon_card = PokemonCard(
                pokemon_info, 
                user_collection, 
                self.image_loader,
                self.db_manager
            )
            
            # Connect the import signal to refresh just the stats
            pokemon_card.cardImported.connect(self.on_card_imported)
            
            self.pokemon_cards.append(pokemon_card)
            grid_layout.addWidget(pokemon_card, row, col, Qt.AlignmentFlag.AlignCenter)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        # If no Pokemon found, show message
        if not pokemon_data:
            no_data_widget = QWidget()
            no_data_layout = QVBoxLayout(no_data_widget)
            
            no_data_label = QLabel(f"No Pokemon data found for {self.gen_name}")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("color: #7f8c8d; font-size: 16px;")
            no_data_layout.addWidget(no_data_label)
            
            sync_hint = QLabel("Use 'Sync Data' to fetch Pokemon card data from the TCG API")
            sync_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sync_hint.setStyleSheet("color: #95a5a6; font-size: 12px;")
            no_data_layout.addWidget(sync_hint)
            
            grid_layout.addWidget(no_data_widget, 0, 0, 1, columns)
        
        self.scroll_area.setWidget(grid_widget)
    
    def on_card_imported(self, pokemon_id, card_id):
        """Handle card import to update stats without full refresh"""
        # Update just the stats
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        self.stats_label.setText(
            f"Pokemon: {total_pokemon} | Imported: {imported_count} | Available Cards: {total_cards}"
        )