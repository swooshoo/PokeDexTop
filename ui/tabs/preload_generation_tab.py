"""
Generation tab with full preloading for smooth scrolling experience.
Shows loading dialog during generation switch, then perfect performance.
"""

import sqlite3
import time
from typing import Dict, Any, Optional

# PyQt6 imports
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QGridLayout, QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# Internal imports
from data.database import DatabaseManager
from data.models import PokemonData, CollectionItem
from cache.image_loader import ImageLoader
from ui.widgets.pokemon_card import PokemonCard


class GenerationPreloader(QThread):
    """
    FIXED: Thread-safe background preloader
    
    Key fixes:
    - Uses signal/slot mechanism instead of direct calls
    - Doesn't call ImageLoader from background thread
    - Properly triggers UI updates on main thread
    """
    
    progressUpdate = pyqtSignal(int, int, str)  # current, total, message
    preloadComplete = pyqtSignal()
    preloadError = pyqtSignal(str)
    
    # NEW: Signal to trigger card loading on main thread
    loadCardSignal = pyqtSignal(object)  # pokemon_card
    
    def __init__(self, pokemon_cards, image_loader):
        super().__init__()
        self.pokemon_cards = pokemon_cards
        self.image_loader = image_loader
        self.should_stop = False
        self.loaded_count = 0
    
    def run(self):
        """
        FIXED: Thread-safe preloading
        
        Instead of calling refresh_card_display() directly from background thread,
        we emit signals to trigger loading on the main thread.
        """
        try:
            total_cards = len(self.pokemon_cards)
            
            self.progressUpdate.emit(0, total_cards, "Starting preload...")
            
            for i, pokemon_card in enumerate(self.pokemon_cards):
                if self.should_stop:
                    return
                
                pokemon_name = getattr(pokemon_card, 'pokemon_data', {}).get('name', f'Pokemon {i+1}')
                self.progressUpdate.emit(i, total_cards, f"Loading {pokemon_name}...")
                
                # FIXED: Emit signal instead of direct call
                self.loadCardSignal.emit(pokemon_card)
                
                # Wait a moment for the main thread to process
                self.msleep(100)  # Increased from 50ms to 100ms for stability
            
            self.progressUpdate.emit(total_cards, total_cards, f"Completed! Loaded {total_cards} cards")
            self.msleep(200)
            self.preloadComplete.emit()
            
        except Exception as e:
            self.preloadError.emit(str(e))
    
    def stop_preload(self):
        """Stop the preloading process"""
        self.should_stop = True


class PreloadGenerationTab(QWidget):
    """
    Generation tab with complete preloading for smooth scrolling
    
    Features:
    - Shows loading dialog when generation is switched
    - Preloads ALL images for the generation in background
    - Perfect smooth scrolling once loaded
    - Memory efficient (only current generation loaded)
    """
    
    def __init__(self, gen_name, generation_num, db_manager, image_loader=None):
        super().__init__()
        self.gen_name = gen_name
        self.generation_num = generation_num
        self.db_manager = db_manager
        self.image_loader = image_loader or ImageLoader()
        self.pokemon_cards = []
        
        # Preloading state
        self.preloader = None
        self.is_loaded = False
        self.is_loading = False
        
        # Performance tracking
        self.load_start_time = None
        
        self.initUI()
    
    def initUI(self):
        """Initialize the UI structure"""
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
        refresh_button.setToolTip("Refresh Pokemon data and reload generation")
        refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_button, 1)
        
        main_layout.addLayout(header_layout)
        
        # Stats and loading status
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(self.stats_label)
        
        # Loading status label
        self.loading_status_label = QLabel("")
        self.loading_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_status_label.setStyleSheet("color: #3498db; font-size: 12px;")
        main_layout.addWidget(self.loading_status_label)
        
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
        
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        
        # Create the grid but don't load images yet
        self.create_pokemon_grid()
    
    def create_pokemon_grid(self):
        """Create the Pokemon grid structure without loading images"""
        print(f"🏗️  Creating Pokemon grid for {self.gen_name}...")
        
        # Get Pokemon data
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
        
        # Clear existing cards
        self.pokemon_cards.clear()
        
        # Create ALL Pokemon cards in Pokédex order (but don't load images yet)
        row, col = 0, 0
        sorted_pokemon = sorted(pokemon_data.items(), key=lambda x: int(x[0]))
        
        for pokemon_id, pokemon_info in sorted_pokemon:
            # Create Pokemon card without loading images initially
            pokemon_card = PreloadablePokemonCard(
                pokemon_info, 
                user_collection, 
                self.image_loader,
                self.db_manager
            )
            
            # Connect the import signal
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
        
        # Set the widget
        self.scroll_area.setWidget(grid_widget)
        
        print(f"✅ Created grid with {len(self.pokemon_cards)} Pokemon cards")
    
    def start_preloading(self):
        """Start preloading all images for this generation - FIXED VERSION"""
        if self.is_loaded or self.is_loading or not self.pokemon_cards:
            return
        
        print(f"🚀 Starting preload for {self.gen_name} ({len(self.pokemon_cards)} cards)...")
        
        self.is_loading = True
        self.load_start_time = time.time()
        
        # Create and start preloader thread
        self.preloader = GenerationPreloader(self.pokemon_cards, self.image_loader)
        
        # Connect existing signals
        self.preloader.progressUpdate.connect(self.on_progress_update)
        self.preloader.preloadComplete.connect(self.on_preload_complete)
        self.preloader.preloadError.connect(self.on_preload_error)
        
        # FIXED: Connect new signal to load cards on main thread
        self.preloader.loadCardSignal.connect(self.load_card_on_main_thread)
        
        # Start the preloading
        self.preloader.start()

    def load_card_on_main_thread(self, pokemon_card):
        """
        FIXED: Load card on main thread to avoid threading issues
        
        This method runs on the main thread, so it can safely call
        refresh_card_display() which uses QNetworkAccessManager.
        """
        try:
            # Debug: Check if card has collection data
            pokemon_id = str(pokemon_card.pokemon_data.get('id', ''))
            has_card = pokemon_id in pokemon_card.user_collection
            pokemon_name = pokemon_card.pokemon_data.get('name', 'Unknown')
            
            print(f"🔄 Loading {pokemon_name} (ID {pokemon_id}): has_imported_card={has_card}")
            
            if has_card:
                card_info = pokemon_card.user_collection[pokemon_id]
                print(f"   → Will show TCG: {card_info.get('card_name', 'Unknown')}")
            else:
                print(f"   → Will show sprite")
            
            # Now safely call refresh_card_display on main thread
            pokemon_card.refresh_card_display()
            
        except Exception as e:
            print(f"❌ Error loading card on main thread: {e}")


    # DEBUGGING: Add this to your PreloadablePokemonCard.refresh_card_display():

    def refresh_card_display(self):
        """Load the actual image - FIXED with debugging"""
        if self.is_image_loaded:
            return
        
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        user_card = self.user_collection.get(str(pokemon_id))
        
        print(f"🔄 refresh_card_display for {pokemon_name}:")
        print(f"   pokemon_id: {pokemon_id}")
        print(f"   user_collection size: {len(self.user_collection)}")
        print(f"   has user_card: {bool(user_card)}")
        
        if user_card:
            print(f"   user_card data: {user_card}")
        else:
            print(f"   user_collection keys: {list(self.user_collection.keys())[:10]}")
        
        if user_card and user_card.get('image_url'):
            print(f"   → Loading TCG card: {user_card.get('card_name')}")
            
            # TCG card loading - EXACT same logic as original
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
            tooltip_text = f"🃏 TCG Card: {user_card.get('card_name', 'Unknown')}"
            if user_card.get('set_name'):
                tooltip_text += f"\n Set: {user_card['set_name']}"
            tooltip_text += f"\n\n Imported for #{pokemon_id} {pokemon_name}"
            self.image_label.setToolTip(tooltip_text)
            
        else:
            print(f"   → Loading sprite")
            
            # Sprite loading - EXACT same logic as original
            sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
            
            # Set loading state
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
            
            # Load sprite
            if self.image_loader:
                self.image_loader.load_image(
                    sprite_url, 
                    self.image_label, 
                    (120, 120),
                    entity_id=str(pokemon_id),
                    cache_type='sprite'
                )
            
            # Set tooltip
            tooltip_text = f"🎮 #{pokemon_id} {pokemon_name}\n👾 Game Sprite\n"
            if self.pokemon_data.get('card_count', 0) == 0:
                tooltip_text += f"📭 No TCG cards available"
            else:
                tooltip_text += f"🃏 Click to import TCG card"
            self.image_label.setToolTip(tooltip_text)
        
        self.is_image_loaded = True
        print(f"✅ {pokemon_name} loading initiated")
    
    def on_progress_update(self, current: int, total: int, message: str):
        """Handle progress updates from preloader"""
        if total > 0:
            progress_percent = (current / total) * 100
            self.loading_status_label.setText(
                f"🔄 Loading {self.gen_name}: {current}/{total} ({progress_percent:.0f}%) - {message}"
            )
        else:
            self.loading_status_label.setText(f"🔄 {message}")
    
    def on_preload_complete(self):
        """Handle preload completion"""
        self.is_loading = False
        self.is_loaded = True
        
        if self.load_start_time:
            load_time = time.time() - self.load_start_time
            self.loading_status_label.setText(
                f"✅ {self.gen_name} loaded in {load_time:.2f}s - Smooth scrolling ready!"
            )
            print(f"✅ {self.gen_name} preload completed in {load_time:.2f}s")
        else:
            self.loading_status_label.setText(f"✅ {self.gen_name} loaded - Smooth scrolling ready!")
        
        # Hide loading status after a few seconds
        QTimer.singleShot(3000, lambda: self.loading_status_label.setText(""))
        
        # Cleanup preloader
        if self.preloader:
            self.preloader.deleteLater()
            self.preloader = None
    
    def on_preload_error(self, error_message: str):
        """Handle preload errors"""
        self.is_loading = False
        self.loading_status_label.setText(f"❌ Error loading {self.gen_name}: {error_message}")
        print(f"❌ Preload error: {error_message}")
        
        # Cleanup preloader
        if self.preloader:
            self.preloader.deleteLater()
            self.preloader = None
    
    def refresh_data(self):
        """Refresh the generation data and restart preloading"""
        print(f"🔄 Refreshing {self.gen_name}...")
        
        # Stop any ongoing preload
        self.stop_preloading()
        
        # Reset state
        self.is_loaded = False
        self.is_loading = False
        
        # Recreate the grid
        self.create_pokemon_grid()
        
        # Start preloading immediately
        QTimer.singleShot(100, self.start_preloading)
    
    def stop_preloading(self):
        """Stop any ongoing preloading"""
        if self.preloader and self.preloader.isRunning():
            self.preloader.stop_preload()
            self.preloader.wait(2000)  # Wait up to 2 seconds
            self.preloader.deleteLater()
            self.preloader = None
        
        self.is_loading = False
    
    def on_card_imported(self, pokemon_id, card_id):
        """Handle card import to update stats"""
        # Update stats without full refresh
        pokemon_data = self.db_manager.get_pokemon_by_generation(self.generation_num)
        user_collection = self.db_manager.get_user_collection()
        
        total_pokemon = len(pokemon_data)
        imported_count = len([p for p in pokemon_data.keys() if p in user_collection])
        total_cards = sum(p.get('card_count', 0) for p in pokemon_data.values())
        
        self.stats_label.setText(
            f"Pokemon: {total_pokemon} | Imported: {imported_count} | Available Cards: {total_cards}"
        )
    
    def showEvent(self, event):
        """Start preloading when tab becomes visible"""
        super().showEvent(event)
        if not self.is_loaded and not self.is_loading:
            # Small delay to let UI settle before starting preload
            QTimer.singleShot(200, self.start_preloading)
    
    def hideEvent(self, event):
        """Optional: Could implement memory cleanup when tab is hidden"""
        super().hideEvent(event)
        # For now, we keep images loaded for fast return to tab
        # Could implement unloading here if memory becomes an issue


class PreloadablePokemonCard(PokemonCard):
    """
    Pokemon card that can be preloaded but starts with a placeholder
    """
    
    def __init__(self, pokemon_data: Dict[str, Any], 
                 user_collection: Optional[Dict[str, Any]] = None,
                 image_loader: Optional[ImageLoader] = None,
                 db_manager: Optional[DatabaseManager] = None):
        
        # Store data
        self.pokemon_data = pokemon_data
        self.user_collection = user_collection
        self.image_loader = image_loader
        self.db_manager = db_manager
        self.is_image_loaded = False
        
        # Initialize the base widget structure
        QFrame.__init__(self)
        
        # Set up UI but don't load image yet
        self.initUI()
        self.show_loading_placeholder()
    
    def initUI(self):
        """Initialize the Pokemon card UI structure"""
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
        self.image_label.setFixedHeight(360)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label)
        
        # Pokemon info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 5, 0, 5)
        info_layout.setSpacing(2)
        
        # Pokemon name and number
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        
        name_label = QLabel(f"#{pokemon_id:03d} {pokemon_name}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # Card count info
        card_count = self.pokemon_data.get('card_count', 0)
        if card_count > 0:
            count_label = QLabel(f"🃏 {card_count} TCG cards available")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("""
                color: #3498db; 
                font-size: 10px; 
                background: transparent;
                font-weight: bold;
            """)
            info_layout.addWidget(count_label)
        else:
            no_cards_label = QLabel("No cards available")
            no_cards_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_cards_label.setStyleSheet("""
                color: #7f8c8d; 
                font-size: 10px; 
                background: transparent;
                font-style: italic;
            """)
            info_layout.addWidget(no_cards_label)
        
        layout.addWidget(info_container)
        self.setLayout(layout)
        
        # Connect click event
        self.mousePressEvent = self.show_card_selection
    
    def show_loading_placeholder(self):
        """Show a loading placeholder instead of the image"""
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        
        # Determine what type of image this will show
        user_card = self.user_collection.get(str(pokemon_id))
        
        if user_card and user_card.get('image_url'):
            # Will show TCG card
            self.image_label.setText(f"#{pokemon_id}\n{pokemon_name}\n⏳ Loading TCG...")
            self.image_label.setStyleSheet("""
                background-color: #2c3e50;
                border-radius: 6px;
                color: #95a5a6;
                font-size: 10px;
                border: 1px solid #34495e;
                padding: 15px;
            """)
        else:
            # Will show sprite
            self.image_label.setText(f"#{pokemon_id}\n{pokemon_name}\n⏳ Loading sprite...")
            self.image_label.setStyleSheet("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                border-radius: 6px; 
                color: #4a90e2;
                font-size: 10px;
                border: 2px solid #87ceeb;
                padding: 15px;
            """)
    
    def refresh_card_display(self):
        """Load the actual image (called by preloader)"""
        if self.is_image_loaded:
            return  # Already loaded
        
        # Use the original PokemonCard loading logic
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        user_card = self.user_collection.get(str(pokemon_id))
        
        if user_card and user_card.get('image_url'):
            # TCG card loading
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
            self.image_label.setToolTip(tooltip_text)
            
        else:
            # Sprite loading
            sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
            
            # Set loading state
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
            
            # Load sprite
            if self.image_loader:
                self.image_loader.load_image(
                    sprite_url, 
                    self.image_label, 
                    (120, 120),
                    entity_id=str(pokemon_id),
                    cache_type='sprite'
                )
            
            # Set tooltip
            tooltip_text = f"🎮 #{pokemon_id} {pokemon_name}\n"
            tooltip_text += f"👾 Game Sprite\n"
            if self.pokemon_data.get('card_count', 0) == 0:
                tooltip_text += f"📭 No TCG cards available"
            else:
                tooltip_text += f"🃏 Click to import TCG card"
            self.image_label.setToolTip(tooltip_text)
        
        self.is_image_loaded = True
    
    def show_card_selection(self, event):
        """Show card selection dialog - uses parent logic"""
        if self.pokemon_data.get('card_count', 0) == 0:
            return
        
        # Import required classes
        from PyQt6.QtWidgets import QMessageBox, QDialog
        from ui.dialogs.card_selection import CardSelectionDialog
        
        pokemon_name = self.pokemon_data['name']
        available_cards = self.pokemon_data.get('available_cards', [])
        
        if not available_cards:
            available_cards = self.fetch_available_cards(pokemon_name)
        
        if not available_cards:
            QMessageBox.information(self, "No Cards", 
                f"No TCG cards found for {pokemon_name}.\n"
                "Use 'Sync Data' to search for cards.")
            return
        
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
        
        import sqlite3
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
        
        # Reset image loaded state and reload
        self.is_image_loaded = False
        self.refresh_card_display()
        
        # Emit signal
        from PyQt6.QtCore import pyqtSignal
        if hasattr(self, 'cardImported'):
            self.cardImported.emit(str(pokemon_id), card_id)
    
    def get_card_details(self, card_id: str) -> Dict[str, Any]:
        """Get card details from database"""
        if not self.db_manager:
            return {}
        
        import sqlite3
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