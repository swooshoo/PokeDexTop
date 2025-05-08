import sys
import os
import json
import math
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QScrollArea,
                            QGridLayout, QTabWidget, QSizePolicy, QFrame,
                            QSplitter)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize

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
    def __init__(self, card_path, card_id, card_name="Unknown", artist="Unknown"):
        super().__init__()
        self.card_path = card_path
        self.card_id = card_id
        self.card_name = card_name
        self.artist = artist
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
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Create layout
        layout = QVBoxLayout()
        
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
        layout.addWidget(name_label)
        
        # Add artist if known
        if self.artist and self.artist != "Unknown":
            artist_label = QLabel(f"Artist: {self.artist}")
            artist_label.setAlignment(Qt.AlignCenter)
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
                
            tcg_card = TCGCard(card_file, card_number, card_name, artist)
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