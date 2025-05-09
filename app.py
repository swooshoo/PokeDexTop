import sys
import os
import json
import math
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QScrollArea,
                            QGridLayout, QTabWidget, QSizePolicy, QFrame,
                            QSplitter, QComboBox, QLineEdit, QCompleter)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QStringListModel

# Path to metadata files
POKEMON_METADATA_FILE = os.path.join('assets', 'pokemon_metadata.json')
TCG_METADATA_FILE = os.path.join('assets', 'tcg_cards', 'index.json')

class PokemonCard(QFrame):
    """A custom widget to display a Pokémon card"""
    def __init__(self, pokemon_data):
        super().__init__()
        self.pokemon_data = pokemon_data
        self.initUI()
        
    def initUI(self):
        # Set frame properties
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            PokemonCard {
                background-color: darkgray;
                border-radius: 8px;
                margin: 5px;
            }
            PokemonCard:hover {
                background-color: gray;
            }
        """)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add Pokémon sprite
        sprite_path = self.pokemon_data.get('local_sprite', '').lstrip('/')
        if os.path.exists(sprite_path):
            sprite_label = QLabel()
            pixmap = QPixmap(sprite_path)
            pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            sprite_label.setPixmap(pixmap)
            sprite_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(sprite_label)
        
        # Add Pokémon name and number
        name_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 10, QFont.Bold))
        layout.addWidget(name_label)
        
        self.setLayout(layout)
        
class TCGCard(QFrame):
    """A custom widget to display a TCG card"""
    def __init__(self, card_path, card_id, card_name="Unknown", artist="Unknown", set_name=None):
        super().__init__()
        self.card_path = card_path
        self.card_id = card_id
        self.card_name = card_name
        self.artist = artist
        self.set_name = set_name  # Only display if not None
        self.initUI()
        
    def initUI(self):
        # Set frame properties
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            TCGCard {
                background-color: darkgray;
                border-radius: 8px;
                margin: 5px;
            }
            TCGCard:hover {
                background-color: gray;
            }
        """)
        
        # Set fixed size policy to prevent stretching
        self.setFixedWidth(280)  # Set a fixed width that looks good for TCG cards
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Add card image
        if os.path.exists(self.card_path):
            card_label = QLabel()
            pixmap = QPixmap(self.card_path)
            pixmap = pixmap.scaled(240, 336, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            card_label.setPixmap(pixmap)
            card_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(card_label)
        
        # Add card name and ID
        name_label = QLabel(f"#{self.card_id}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 10, QFont.Bold))
        name_label.setWordWrap(True)  # Allow text to wrap
        layout.addWidget(name_label)
        
        # Add set name if provided AND not None (None means explicitly don't show it)
        if self.set_name is not None and self.set_name != "Unknown":
            set_label = QLabel(f"Set: {self.set_name}")
            set_label.setAlignment(Qt.AlignCenter)
            set_label.setWordWrap(True)  # Allow text to wrap
            layout.addWidget(set_label)
        
        # Add artist if known
        if self.artist and self.artist != "Unknown":
            artist_label = QLabel(f"Artist: {self.artist}")
            artist_label.setAlignment(Qt.AlignCenter)
            artist_label.setWordWrap(True)  # Allow text to wrap
            layout.addWidget(artist_label)
        
        self.setLayout(layout)
        
class GenerationTab(QWidget):
    """A widget representing a single generation tab"""
    def __init__(self, gen_name, start_id, end_id, pokemon_metadata):
        super().__init__()
        self.gen_name = gen_name
        self.start_id = start_id
        self.end_id = end_id
        self.pokemon_metadata = pokemon_metadata
        self.initUI()
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.gen_name)
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Range label
        range_label = QLabel(f"Pokémon #{self.start_id} - #{self.end_id}")
        range_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(range_label)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Create a scroll area for the Pokémon grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create the grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        
        # Number of columns for the grid
        columns = 4
        
        # Add Pokémon cards to the grid
        row, col = 0, 0
        for pokemon_id in range(self.start_id, self.end_id + 1):
            pokemon_data = self.get_pokemon_data(pokemon_id)
            if pokemon_data:
                pokemon_card = PokemonCard(pokemon_data)
                grid_layout.addWidget(pokemon_card, row, col)
                
                # Move to the next column or row
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
        
        # Set the grid widget as the scroll area's content
        grid_widget.setLayout(grid_layout)
        scroll_area.setWidget(grid_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
    
    def get_pokemon_data(self, pokemon_id):
        """Get a specific Pokémon by ID"""
        pokemon_id = str(pokemon_id)
        if pokemon_id in self.pokemon_metadata:
            return self.pokemon_metadata[pokemon_id]
        return None

class TCGSetTab(QWidget):
    """A widget representing a TCG set tab"""
    def __init__(self, set_name, set_path, set_metadata=None):
        super().__init__()
        self.set_name = set_name
        self.set_path = set_path
        self.set_metadata = set_metadata
        self.initUI()
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.set_name)
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Card count label (if metadata available)
        if self.set_metadata and 'total_cards' in self.set_metadata:
            count_label = QLabel(f"Total Cards: {self.set_metadata['total_cards']}")
            count_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(count_label)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Create a scroll area for the TCG card grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create the grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        
        # Number of columns for the grid
        columns = 4  # Fewer columns for TCG cards as they're larger
        
        # Find all PNG images in the set directory
        card_files = glob.glob(os.path.join(self.set_path, "*.png"))
        
        # Sort card files by the numeric part at the beginning of the filename
        def get_card_number(file_path):
            filename = os.path.basename(file_path).split('.')[0]
            # Extract the number from the start of the filename
            # This handles filenames like "46 Alolan Golem"
            try:
                # Split by space and get the first part as number
                num_part = filename.split(' ')[0]
                return int(num_part)  # Convert to int for proper sorting
            except (ValueError, IndexError):
                # If parsing fails, return the original filename
                return filename
        
        # Sort the files numerically by the number at the start of the filename
        card_files = sorted(card_files, key=get_card_number)
        
        # Add TCG cards to the grid
        row, col = 0, 0
        for card_file in card_files:
            # Get the full filename without extension
            filename = os.path.basename(card_file).split('.')[0]
            
            # Try to get metadata if available
            card_name = f"Card #{filename}"
            artist = "Unknown"
            
            # Check if this exact filename is in the metadata
            if self.set_metadata and 'cards' in self.set_metadata and filename in self.set_metadata['cards']:
                card_data = self.set_metadata['cards'][filename]
                card_name = card_data.get('name', card_name)
                artist = card_data.get('artist', artist)
            
            # Extract the card number for display
            try:
                card_number = filename.split(' ')[0]
            except (IndexError, ValueError):
                card_number = filename
                
            # Create TCG card without passing set_name (set to None to ensure it's not displayed)
            tcg_card = TCGCard(card_file, card_number, card_name, artist, None)
            grid_layout.addWidget(tcg_card, row, col)
            
            # Move to the next column or row
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        # Set the grid widget as the scroll area's content
        grid_widget.setLayout(grid_layout)
        scroll_area.setWidget(grid_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)

class PokemonSearchTab(QWidget):
    """A tab for searching TCG cards by Pokemon name"""
    def __init__(self, pokemon_metadata, tcg_metadata):
        super().__init__()
        self.pokemon_metadata = pokemon_metadata
        self.tcg_metadata = tcg_metadata
        # Extract all Pokemon names from metadata
        self.pokemon_names = self.get_pokemon_names()
        self.current_search_results = []
        self.initUI()
        
    def get_pokemon_names(self):
        """Extract all Pokemon names from the metadata"""
        pokemon_names = []
        for pokemon_id, pokemon_data in self.pokemon_metadata.items():
            if 'name' in pokemon_data:
                pokemon_names.append(pokemon_data['name'])
        return sorted(pokemon_names)
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Search TCG Cards by Pokémon")
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Search section
        search_layout = QHBoxLayout()
        
        # Create a custom SearchInput that handles Enter key
        class SearchInput(QLineEdit):
            def __init__(self, parent=None):
                super().__init__(parent)
                
            def keyPressEvent(self, event):
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    # If parent is PokemonSearchTab, call its search_cards method
                    if isinstance(self.parent(), PokemonSearchTab):
                        self.parent().search_cards()
                    event.accept()  # Mark event as handled
                else:
                    super().keyPressEvent(event)  # Handle other keys normally
        
        # Search input with autocomplete
        self.search_input = SearchInput(self)
        self.search_input.setPlaceholderText("Enter a Pokémon name...")
        
        # Set up autocomplete
        completer = QCompleter(self.pokemon_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.search_input.setCompleter(completer)
        
        # Connect enter key to search function (belt and suspenders approach)
        self.search_input.returnPressed.connect(self.search_cards)
        
        search_layout.addWidget(self.search_input, 3)
        
        # Search button
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_cards)
        search_layout.addWidget(search_button, 1)
        
        main_layout.addLayout(search_layout)
        
        # Quick selection dropdown
        dropdown_layout = QHBoxLayout()
        dropdown_label = QLabel("Or select a Pokémon:")
        dropdown_layout.addWidget(dropdown_label)
        
        self.pokemon_dropdown = QComboBox()
        self.pokemon_dropdown.addItems([""] + self.pokemon_names)  # Add empty option first
        self.pokemon_dropdown.currentTextChanged.connect(self.on_dropdown_changed)
        dropdown_layout.addWidget(self.pokemon_dropdown)
        
        main_layout.addLayout(dropdown_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Results section
        self.results_layout = QVBoxLayout()
        
        # Results count label
        self.results_count_label = QLabel("Enter a Pokémon name to see matching TCG cards")
        self.results_count_label.setAlignment(Qt.AlignCenter)
        self.results_layout.addWidget(self.results_count_label)
        
        # Create a scroll area for search results
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        
        # Create a container for the results grid
        self.results_container = QWidget()
        self.results_grid = QGridLayout(self.results_container)
        
        # Configure grid layout to maintain fixed card sizes
        self.results_grid.setSpacing(10)  # Set spacing between cards
        self.results_grid.setContentsMargins(20, 20, 20, 20)  # Add margins around the grid
        
        self.results_scroll.setWidget(self.results_container)
        self.results_layout.addWidget(self.results_scroll)
        
        main_layout.addLayout(self.results_layout)
        
        self.setLayout(main_layout)
    
    def on_dropdown_changed(self, text):
        """Handle dropdown selection change"""
        if text:
            self.search_input.setText(text)
            self.search_cards()
            
    def search_cards(self):
        """Search for TCG cards containing the specified Pokemon name"""
        # Get the search term
        search_term = self.search_input.text().strip()
        
        if not search_term:
            self.results_count_label.setText("Please enter a Pokémon name to search")
            self.clear_results()
            return
            
        # Find matching cards
        matching_cards = self.find_matching_cards(search_term)
        self.current_search_results = matching_cards
        
        # Update results count
        if matching_cards:
            self.results_count_label.setText(f"Found {len(matching_cards)} TCG cards featuring {search_term}")
        else:
            self.results_count_label.setText(f"No TCG cards found for {search_term}")
            
        # Display results
        self.display_results(matching_cards)
    
    def find_matching_cards(self, pokemon_name):
        """Find all TCG cards that contain the Pokemon name in their card_name"""
        matching_cards = []
        
        # If no TCG metadata, return empty list
        if not self.tcg_metadata or 'sets' not in self.tcg_metadata:
            return matching_cards
        
        # Search through all sets and their cards
        for set_id, set_data in self.tcg_metadata['sets'].items():
            if 'cards' not in set_data:
                continue
                
            for card_id, card_data in set_data['cards'].items():
                card_name = card_data.get('name', '')
                
                # Check if Pokemon name is in the card name (case insensitive)
                if pokemon_name.lower() in card_name.lower():
                    # Add card path, set name and set ID for reference
                    card_info = {
                        'set_id': set_id,
                        'set_name': set_data.get('name', set_id),
                        'card_id': card_id,
                        'card_name': card_name,
                        'artist': card_data.get('artist', 'Unknown'),
                        'card_path': card_data.get('image_path', '').lstrip('/')
                    }
                    
                    matching_cards.append(card_info)
        
        return matching_cards
    
    def clear_results(self):
        """Clear all search results"""
        # Remove all widgets from the grid
        for i in reversed(range(self.results_grid.count())):
            widget = self.results_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
    
    def display_results(self, cards):
        """Display the search results in a grid"""
        # Clear previous results
        self.clear_results()
        
        if not cards:
            return
            
        # Set up the grid
        columns = 4  # Using 4 columns to match other tabs
        row, col = 0, 0
        
        # Configure the grid to prevent stretching
        for i in range(columns):
            self.results_grid.setColumnStretch(i, 1)
        
        # Add cards to the grid
        for card_info in cards:
            # Create TCG card widget
            card_path = card_info.get('card_path', '')
            if os.path.exists(card_path):
                tcg_card = TCGCard(
                    card_path, 
                    card_info.get('card_id', ''), 
                    card_info.get('card_name', ''),
                    card_info.get('artist', 'Unknown'),
                    card_info.get('set_name', 'Unknown')
                )
                # Fix the size policy to prevent stretching
                tcg_card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                self.results_grid.addWidget(tcg_card, row, col)
                
                # Move to the next column or row
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
            else:
                print(f"Card image not found: {card_path}")

class PokemonDashboard(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.pokemon_metadata = self.load_pokemon_metadata()
        self.tcg_metadata = self.load_tcg_metadata()
        self.generations = {
            "Generation 1": (1, 151),      # Kanto
            "Generation 2": (152, 251),    # Johto
            "Generation 3": (252, 386),    # Hoenn
            "Generation 4": (387, 493),    # Sinnoh
            "Generation 5": (494, 649),    # Unova
            "Generation 6": (650, 721),    # Kalos
            "Generation 7": (722, 809),    # Alola
            "Generation 8": (810, 905),    # Galar
            "Generation 9": (906, 1025)    # Paldea
        }
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Pokémon Dashboard')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create the central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create main tab widget
        main_tabs = QTabWidget()
        
        # Create Pokémon Sprites Tab
        sprites_tab = QWidget()
        sprites_layout = QVBoxLayout(sprites_tab)
        
        # Create a tab widget for generations
        gen_tabs = QTabWidget()
        
        # Add tabs for each generation
        for gen_name, (start_id, end_id) in self.generations.items():
            gen_tab = GenerationTab(gen_name, start_id, end_id, self.pokemon_metadata)
            gen_tabs.addTab(gen_tab, gen_name)
        
        sprites_layout.addWidget(gen_tabs)
        
        # Add the sprites tab to main tabs
        main_tabs.addTab(sprites_tab, "Pokémon Sprites")
        
        # Create TCG Cards Tab
        tcg_tab = QWidget()
        tcg_layout = QVBoxLayout(tcg_tab)
        
        # Create a tab widget for TCG sets
        tcg_tabs = QTabWidget()
        
        # Add tabs for each TCG set
        tcg_sets_path = os.path.join('assets', 'tcg_cards')
        if os.path.exists(tcg_sets_path):
            # Get all directories in the TCG cards folder
            set_dirs = [d for d in os.listdir(tcg_sets_path) 
                       if os.path.isdir(os.path.join(tcg_sets_path, d))]
            
            # Sort alphabetically
            set_dirs.sort()
            
            for set_dir in set_dirs:
                set_path = os.path.join(tcg_sets_path, set_dir)
                
                # Get set metadata if available
                set_metadata = None
                set_name = set_dir.replace('_', ' ').title()
                
                if self.tcg_metadata and 'sets' in self.tcg_metadata and set_dir in self.tcg_metadata['sets']:
                    set_metadata = self.tcg_metadata['sets'][set_dir]
                    set_name = set_metadata.get('name', set_name)
                
                # Create the set tab
                set_tab = TCGSetTab(set_name, set_path, set_metadata)
                tcg_tabs.addTab(set_tab, set_name)
        else:
            # If no TCG sets found, display a message
            no_cards_label = QLabel("No TCG card sets found. Please add them to assets/tcg_cards/")
            no_cards_label.setAlignment(Qt.AlignCenter)
            tcg_layout.addWidget(no_cards_label)
        
        tcg_layout.addWidget(tcg_tabs)
        
        # Add the TCG tab to main tabs
        main_tabs.addTab(tcg_tab, "TCG Cards")
        
        # Create Search by Pokemon Tab
        search_tab = PokemonSearchTab(self.pokemon_metadata, self.tcg_metadata)
        main_tabs.addTab(search_tab, "Search by Pokémon")
        
        # Add the main tab widget to the layout
        main_layout.addWidget(main_tabs)
        
        # Set up status bar
        pokemon_count = len(self.pokemon_metadata)
        tcg_set_count = len(set_dirs) if 'set_dirs' in locals() else 0
        
        self.statusBar().showMessage(
            f"Pokémon: {pokemon_count} | TCG Sets: {tcg_set_count}"
        )
        
    def load_pokemon_metadata(self):
        """Load Pokémon metadata from file"""
        if os.path.exists(POKEMON_METADATA_FILE):
            try:
                with open(POKEMON_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
                    print(f"Loaded metadata for {len(metadata)} Pokémon")
                    return metadata
            except Exception as e:
                print(f"Error loading Pokémon metadata: {e}")
        else:
            print(f"Pokémon metadata file not found: {POKEMON_METADATA_FILE}")
        
        return {}
    
    def load_tcg_metadata(self):
        """Load TCG card metadata from file"""
        if os.path.exists(TCG_METADATA_FILE):
            try:
                with open(TCG_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
                    if 'sets' in metadata:
                        print(f"Loaded metadata for {len(metadata['sets'])} TCG sets")
                    return metadata
            except Exception as e:
                print(f"Error loading TCG metadata: {e}")
        else:
            print(f"TCG metadata file not found: {TCG_METADATA_FILE}")
        
        return {}

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show the main window
    mainWindow = PokemonDashboard()
    mainWindow.show()
    
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()