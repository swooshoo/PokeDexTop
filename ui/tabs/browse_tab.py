"""
Enhanced Browse TCG Cards Tab - Extracted from app.py lines 849-1350
Provides advanced card browsing with cart functionality and import capabilities
"""

import sqlite3
import math
from difflib import SequenceMatcher
from typing import Dict, List, Optional

# PyQt6 imports - FIXED
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QTabWidget, QSizePolicy, QFrame, QComboBox, QLineEdit, 
    QCompleter, QMessageBox, QGroupBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QApplication
)
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QPixmap  # ✅ Removed QStringListModel
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QStringListModel  # ✅ Added QStringListModel here

# Internal imports
from data.database import DatabaseManager
from cache.image_loader import ImageLoader
from utils.session_cart import SessionCartManager
from ui.widgets.tcg_cards import ClickableTCGCard, CartItemWidget


class PokemonNameCompleter(QCompleter):
    """Custom completer for Pokemon names with fuzzy matching"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.pokemon_names = self.load_pokemon_names()
        self.setModel(QStringListModel(self.pokemon_names))
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
    
    def load_pokemon_names(self):
        """Load all unique Pokemon names from database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT name FROM silver_pokemon_master 
            ORDER BY name
        """)
        
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names
    
    def find_best_match(self, input_text):
        """Find the best fuzzy match for input text"""
        if not input_text:
            return None
        
        input_lower = input_text.lower()
        best_match = None
        best_ratio = 0
        
        for name in self.pokemon_names:
            name_lower = name.lower()
            
            # Exact match gets priority
            if input_lower == name_lower:
                return name
            
            # Starts with gets high priority
            if name_lower.startswith(input_lower):
                ratio = 0.9 + (len(input_text) / len(name)) * 0.1
            else:
                # Use sequence matcher for fuzzy matching
                ratio = SequenceMatcher(None, input_lower, name_lower).ratio()
            
            if ratio > best_ratio and ratio > 0.6:  # Minimum threshold
                best_ratio = ratio
                best_match = name
        
        return best_match


class EnhancedBrowseTCGTab(QWidget):
    """Enhanced Browse TCG Cards tab with cart functionality"""
    
    def __init__(self, db_manager, image_loader, cart_manager):
        super().__init__()
        self.db_manager = db_manager
        self.image_loader = image_loader
        self.cart_manager = cart_manager
        self.current_cards = []
        self.initUI()
        
        # Connect cart callbacks
        self.cart_manager.item_added_callback = self.update_cart_display
        self.cart_manager.item_removed_callback = self.update_cart_display
    
    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Left panel - Compact search and filters
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 0)  # Fixed width, no stretch
        
        # Center panel - Expanded card grid
        center_panel = self.create_center_panel()
        main_layout.addWidget(center_panel, 4)  # More space for cards
        
        # Right panel - Cart and analytics
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Load initial data
        self.load_cards()
        
    def create_left_panel(self):
        """Create a compact left search panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        panel.setFixedWidth(180)  # Reduced from 250
        panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)  # Reduced padding
        layout.setSpacing(8)  # Reduced spacing
        
        # Compact title
        title_label = QLabel("🔍 Search")
        title_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # Pokemon name search - compact
        name_label = QLabel("Pokemon:")
        name_label.setStyleSheet("color: #bdc3c7; font-size: 10px; margin-bottom: 2px;")
        layout.addWidget(name_label)
        
        self.name_search_input = QLineEdit()
        self.name_search_input.setPlaceholderText("Type name...")
        self.name_search_input.setFixedHeight(30)  # Smaller height
        
        # Set up completer
        self.pokemon_completer = PokemonNameCompleter(self.db_manager)
        self.name_search_input.setCompleter(self.pokemon_completer)
        self.name_search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.name_search_input)
        
        # Set search - compact
        set_label = QLabel("Set:")
        set_label.setStyleSheet("color: #bdc3c7; font-size: 10px; margin-top: 8px; margin-bottom: 2px;")
        layout.addWidget(set_label)
        
        self.set_search_input = QLineEdit()
        self.set_search_input.setPlaceholderText("Type set...")
        self.set_search_input.setFixedHeight(30)
        
        # Set up set completer
        self.setup_set_completer()
        self.set_search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.set_search_input)
        
        # Compact buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)
        
        search_btn = QPushButton("Search")
        search_btn.setFixedHeight(30)
        search_btn.clicked.connect(self.perform_search)
        button_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(25)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()  # Push everything to top
        
        return panel
    
    def setup_set_completer(self):
        """Setup autocompleter for sets"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT display_name, name FROM silver_tcg_sets 
            ORDER BY display_name
        """)
        
        set_names = []
        for row in cursor.fetchall():
            display_name, name = row
            if display_name:
                set_names.append(display_name)
            else:
                set_names.append(name)
        
        conn.close()
        
        set_completer = QCompleter(set_names)
        set_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        set_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.set_search_input.setCompleter(set_completer)
    
    def create_center_panel(self):
        """Create the center card display panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Header with stats
        header_layout = QHBoxLayout()
        
        self.results_label = QLabel("Browse TCG Cards")
        self.results_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.results_label.setStyleSheet("color: white; padding: 10px;")
        header_layout.addWidget(self.results_label)
        
        header_layout.addStretch()
        
        # Sort options
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("color: white;")
        header_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Name (A-Z)", "Name (Z-A)", 
            "Set Name", "Newest First", "Oldest First"
        ])
        self.sort_combo.currentTextChanged.connect(self.apply_sort)
        header_layout.addWidget(self.sort_combo)
        
        layout.addLayout(header_layout)
        
        # Card display area
        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_scroll.setStyleSheet("background-color: #2c3e50; border: none;")
        layout.addWidget(self.card_scroll)
        
        self.card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.card_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        return panel
    
    def create_right_panel(self):
        """Create the right panel with cart functionality"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        panel.setFixedWidth(260)  # Reduced from 300
        panel.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)  # Reduced padding
        
        # Cart section
        cart_group = QGroupBox("Import Cart")
        cart_layout = QVBoxLayout(cart_group)
        cart_layout.setSpacing(8)  # Reduced spacing
        
        # Cart counter
        self.cart_counter_label = QLabel("0 cards in cart")
        self.cart_counter_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        cart_layout.addWidget(self.cart_counter_label)
        
        # Import all button
        self.import_all_btn = QPushButton("IMPORT ALL")
        self.import_all_btn.setFixedHeight(35)  # Slightly smaller
        self.import_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.import_all_btn.clicked.connect(self.import_all_cards)
        self.import_all_btn.setEnabled(False)
        cart_layout.addWidget(self.import_all_btn)
        
        # Cart status label
        self.cart_status_label = QLabel("Double-click cards in the browse area to add them here")
        self.cart_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cart_status_label.setStyleSheet("""
            color: #7f8c8d; 
            font-size: 9px; 
            padding: 4px;
            background-color: #2c3e50;
            border-radius: 4px;
            margin: 3px 0px;
        """)
        self.cart_status_label.setWordWrap(True)
        cart_layout.addWidget(self.cart_status_label)
        
        # Cart items scroll area
        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setStyleSheet("background-color: #2c3e50; border: none;")
        cart_layout.addWidget(self.cart_scroll)
        
        layout.addWidget(cart_group)
        
        # Initialize cart display
        self.update_cart_display()
        
        return panel
    
    def on_search_changed(self):
        """Handle search input changes with debouncing"""
        # Auto-search when user stops typing (could add QTimer for debouncing)
        pass
    
    def perform_search(self):
        """Perform the search based on current inputs"""
        pokemon_name = self.name_search_input.text().strip()
        set_name = self.set_search_input.text().strip()
        
        # Handle Pokemon name with fuzzy matching
        if pokemon_name:
            best_match = self.pokemon_completer.find_best_match(pokemon_name)
            if best_match and best_match != pokemon_name:
                # Auto-correct the input
                self.name_search_input.setText(best_match)
                pokemon_name = best_match
        
        self.load_cards(pokemon_name, set_name)
    
    def clear_filters(self):
        """Clear all search filters"""
        self.name_search_input.clear()
        self.set_search_input.clear()
        self.load_cards()
    
    def load_cards(self, pokemon_name=None, set_name=None):
        """Load cards based on search criteria"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT DISTINCT c.card_id, c.name, c.set_name, c.artist, c.rarity, 
                   c.image_url_large, c.image_url_small, c.set_id
            FROM silver_tcg_cards c
            LEFT JOIN silver_team_up_cards t ON c.card_id = t.card_id
            WHERE 1=1
        """
        params = []
        
        if pokemon_name:
            query += " AND (c.pokemon_name = ? OR t.pokemon_name = ?)"
            params.extend([pokemon_name, pokemon_name])
        
        if set_name:
            query += " AND (c.set_name LIKE ? OR s.display_name LIKE ?)"
            params.extend([f'%{set_name}%', f'%{set_name}%'])
            query = query.replace("FROM silver_tcg_cards c", 
                                "FROM silver_tcg_cards c LEFT JOIN silver_tcg_sets s ON c.set_id = s.set_id")
        
        query += " ORDER BY c.name LIMIT 200"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        # Convert to card data format
        self.current_cards = []
        for row in results:
            card_data = {
                'card_id': row[0],
                'name': row[1],
                'set_name': row[2],
                'artist': row[3],
                'rarity': row[4],
                'image_url_large': row[5],
                'image_url_small': row[6],
                'set_id': row[7]
            }
            self.current_cards.append(card_data)
        
        self.display_cards()
        
        # Update results label
        result_text = f"Showing {len(self.current_cards)} cards"
        if pokemon_name:
            result_text += f" for {pokemon_name}"
        if set_name:
            result_text += f" from sets matching '{set_name}'"
        self.results_label.setText(result_text)
    
    def apply_sort(self):
        """Apply sorting to current cards"""
        sort_option = self.sort_combo.currentText()
        
        if sort_option == "Name (A-Z)":
            self.current_cards.sort(key=lambda x: x['name'])
        elif sort_option == "Name (Z-A)":
            self.current_cards.sort(key=lambda x: x['name'], reverse=True)
        elif sort_option == "Set Name":
            self.current_cards.sort(key=lambda x: x['set_name'])
        # Add more sorting options as needed
        
        self.display_cards()
    
    def display_cards(self):
        """Display the current cards in perfectly centered grid"""
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: #2c3e50;")
        
        # Create a container to center the grid
        main_layout = QVBoxLayout(grid_widget)
        main_layout.setContentsMargins(0, 20, 0, 20)  # Only top/bottom margins
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Create the actual card grid container
        cards_container = QWidget()
        cards_container.setStyleSheet("background-color: transparent;")
        
        # Calculate exact width needed for 3 cards
        card_width = 270
        cards_per_row = 3
        card_spacing = 15
        total_width = (cards_per_row * card_width) + ((cards_per_row - 1) * card_spacing)
        
        # Set fixed width for perfect centering
        cards_container.setFixedWidth(total_width)  # 270*3 + 15*2 = 840px
        
        # Grid layout for the cards
        grid_layout = QGridLayout(cards_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)  # No margins on grid itself
        grid_layout.setSpacing(card_spacing)
        
        row, col = 0, 0
        
        for card_data in self.current_cards:
            # Import ClickableTCGCard would be needed here
            card_widget = ClickableTCGCard(card_data, self.image_loader, self.cart_manager)
            card_widget.cardSelected.connect(self.on_card_selected)
            grid_layout.addWidget(card_widget, row, col)
            
            col += 1
            if col >= cards_per_row:
                col = 0
                row += 1
        
        if not self.current_cards:
            # Show empty state
            empty_label = QLabel("No cards found.\nTry adjusting your search or sync more data.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #7f8c8d; font-size: 16px; padding: 40px;")
            grid_layout.addWidget(empty_label, 0, 0, 1, cards_per_row)
        
        # Add the cards container to main layout and center it horizontally
        main_layout.addWidget(cards_container, 0, Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch()  # Push content to top
        
        self.card_scroll.setWidget(grid_widget)
    
    def on_card_selected(self, card_id, card_data):
        """Handle card selection"""
        self.update_cart_display()
    
    def update_cart_display(self, card_id=None, card_data=None):
        """Update the cart display"""
        cart_items = self.cart_manager.get_cart_items()
        cart_count = len(cart_items)
        
        # Update counter
        self.cart_counter_label.setText(f"{cart_count} cards in cart")
        
        # Update import button
        self.import_all_btn.setEnabled(cart_count > 0)
        
        # Update cart status label
        if cart_count > 0:
            self.cart_status_label.setText(f"🛒 {cart_count} cards ready to import")
            self.cart_status_label.setStyleSheet("""
                color: #27ae60; 
                font-size: 10px; 
                padding: 5px;
                background-color: #2c3e50;
                border-radius: 4px;
                margin: 5px 0px;
                font-weight: bold;
            """)
        else:
            self.cart_status_label.setText("Double-click cards in the browse area to add them here")
            self.cart_status_label.setStyleSheet("""
                color: #7f8c8d; 
                font-size: 10px; 
                padding: 5px;
                background-color: #2c3e50;
                border-radius: 4px;
                margin: 5px 0px;
            """)
        
        # Create cart items widget
        cart_widget = QWidget()
        cart_layout = QVBoxLayout(cart_widget)
        cart_layout.setContentsMargins(5, 5, 5, 5)
        cart_layout.setSpacing(5)
        
        for cart_card_id, cart_card_data in cart_items.items():
            # Import CartItemWidget would be needed here
            cart_item = CartItemWidget(cart_card_data, self.image_loader)
            cart_item.removeRequested.connect(self.remove_from_cart)
            cart_layout.addWidget(cart_item)
        
        cart_layout.addStretch()
        self.cart_scroll.setWidget(cart_widget)
    
    def remove_from_cart(self, card_id):
        """Remove a card from the cart"""
        self.cart_manager.remove_card(card_id)
        
        # Update any card widgets to show they're no longer in cart
        # This would require keeping track of card widgets, or refreshing the display
        self.display_cards()  # Refresh to update cart indicators
    
    def import_all_cards(self):
        """Import all cards in the cart"""
        cart_items = self.cart_manager.get_cart_items()
        
        if not cart_items:
            return
        
        success_count = 0
        error_count = 0
        
        for card_id, card_data in cart_items.items():
            try:
                # Extract Pokemon name and find Pokemon ID
                pokemon_name = self.extract_pokemon_name(card_data['name'])
                if pokemon_name:
                    pokemon_id = self.find_pokemon_id_by_name(pokemon_name)
                    if pokemon_id:
                        self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"Error importing {card_id}: {e}")
                error_count += 1
        
        # Show results
        if success_count > 0:
            QMessageBox.information(self, "Import Complete", 
                f"Successfully imported {success_count} cards!\n"
                f"Errors: {error_count}")
            
            # Clear the cart
            self.cart_manager.clear_cart()
            
            # Refresh card display to update indicators
            self.display_cards()
        else:
            QMessageBox.warning(self, "Import Failed", 
                "No cards were imported. Check that Pokemon names can be recognized.")
    
    def extract_pokemon_name(self, card_name):
        """Extract Pokemon name from card name"""
        # Use the same logic from your existing implementation
        return self.db_manager.extract_pokemon_name_from_card(card_name)
    
    def find_pokemon_id_by_name(self, pokemon_name):
        """Find Pokemon ID by name"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pokemon_id FROM silver_pokemon_master 
            WHERE LOWER(name) = LOWER(?)
        """, (pokemon_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None