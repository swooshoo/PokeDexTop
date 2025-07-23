# ui/tabs/generation_tab.py - REPLACE the entire class with proper lazy loading

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
    """Generation tab with tab-level lazy loading"""
    
    def __init__(self, gen_name, generation_num, db_manager, image_loader=None):
        super().__init__()
        self.gen_name = gen_name
        self.generation_num = generation_num
        self.db_manager = db_manager
        self.image_loader = image_loader or ImageLoader()
        self.pokemon_cards = []
        
        # ✅ LAZY LOADING STATE
        self.is_loaded = False
        self.is_visible = False
        
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
        refresh_button.clicked.connect(self.force_refresh)
        header_layout.addWidget(refresh_button, 1)
        
        main_layout.addLayout(header_layout)
        
        # Stats label
        self.stats_label = QLabel("Loading generation data...")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("color: white; font-size: 12px; padding: 10px;")
        main_layout.addWidget(self.stats_label)
        
        # Scroll area for Pokemon grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2c3e50;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #34495e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3498db;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        
        # ✅ DON'T LOAD DATA YET - wait for tab activation
        self.show_loading_placeholder()
    
    def show_loading_placeholder(self):
        """Show placeholder until tab is activated"""
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        
        loading_label = QLabel(f"Ready to load {self.gen_name}")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("""
            color: #95a5a6; 
            font-size: 18px; 
            font-weight: bold;
            padding: 50px;
        """)
        placeholder_layout.addWidget(loading_label)
        
        hint_label = QLabel("Images will load when you switch to this tab")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        placeholder_layout.addWidget(hint_label)
        
        self.scroll_area.setWidget(placeholder_widget)
        
        # Update stats to show we're ready but not loaded
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        total_pokemon = len(pokemon_data)
        self.stats_label.setText(f"Ready to load: {total_pokemon} Pokemon (click tab to load images)")
    
    def on_tab_activated(self):
        """Called when this tab becomes visible - triggers loading"""
        self.is_visible = True
        
        if not self.is_loaded:
            print(f"📊 Loading {self.gen_name} images...")
            self.load_generation_data()
            self.is_loaded = True
    
    def on_tab_deactivated(self):
        """Called when tab becomes hidden"""
        self.is_visible = False
    
    def load_generation_data(self):
        """Load all Pokemon data and images for this generation"""
        # Clear existing cards
        self.pokemon_cards.clear()
        
        # Get data
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        # Update stats
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        pokemon_with_cards = len([p for p in pokemon_data.values() if p.get('card_count', 0) > 0])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
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
        
        # ✅ AUTO-LOAD: Create Pokemon cards with immediate image loading
        row, col = 0, 0
        sorted_pokemon = sorted(pokemon_data.items(), key=lambda x: int(x[0]))
        
        for pokemon_id, pokemon_info in sorted_pokemon:
            pokemon_card = PokemonCard(
                pokemon_info, 
                user_collection, 
                self.image_loader,
                self.db_manager,
                auto_load=True  # ✅ AUTO-LOAD when tab is active
            )
            
            pokemon_card.cardImported.connect(self.on_card_imported)
            self.pokemon_cards.append(pokemon_card)
            grid_layout.addWidget(pokemon_card, row, col, Qt.AlignmentFlag.AlignCenter)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        # Handle empty generation
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
        print(f"✅ {self.gen_name} loaded: {total_pokemon} Pokemon with automatic image loading")
    
    def force_refresh(self):
        """Force refresh generation data"""
        self.is_loaded = False
        if self.is_visible:
            self.load_generation_data()
            self.is_loaded = True
        else:
            self.show_loading_placeholder()
    
    def refresh_data(self):
        """Legacy method - now calls proper loading logic"""
        if self.is_visible and not self.is_loaded:
            self.load_generation_data()
            self.is_loaded = True
    
    def on_card_imported(self, pokemon_id, card_id):
        """Handle card import to update stats without full refresh"""
        if not self.is_loaded:
            return
            
        # Update just the stats
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        self.stats_label.setText(
            f"Pokemon: {total_pokemon} | Imported: {imported_count} | Available Cards: {total_cards}"
        )