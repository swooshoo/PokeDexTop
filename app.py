import sys
import os
import json
import math
import glob
import re
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QScrollArea,
                            QGridLayout, QTabWidget, QSizePolicy, QFrame,
                            QSplitter, QComboBox, QLineEdit, QCompleter,
                            QToolButton, QMessageBox, QDialog, QGroupBox, QRadioButton, 
                            QCheckBox, QButtonGroup, QDialogButtonBox, QFileDialog)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QPainter, QPen # QPainter and QPen should be in QtGui, not QtCore
from PyQt5.QtCore import Qt, QSize, QStringListModel, pyqtSignal, QObject, QRectF # QRectF is in QtCore
from PyQt5.QtPrintSupport import QPrinter # Only QPrinter is in QtPrintSupport
import datetime


# Path to metadata files
POKEMON_METADATA_FILE = os.path.join('assets', 'pokemon_metadata.json')
TCG_METADATA_FILE = os.path.join('assets', 'tcg_cards', 'index.json')
IMPORTED_CARDS_FILE = os.path.join('assets', 'imported_cards.json')

# Global dashboard reference that will be set when the dashboard is created
# This is a simple approach for immediate functionality
DASHBOARD = None

# Signal hub for passing messages between components
class SignalHub(QObject):
    # Signal for when a card should be imported
    import_card_signal = pyqtSignal(str, str)  # (pokemon_name, card_path)
    
# Create a global signal hub instance
SIGNAL_HUB = SignalHub()

class PokemonCard(QFrame):
    """A custom widget to display a Pokémon card with dimensions matching TCGCard"""
    def __init__(self, pokemon_data, imported_cards=None):
        super().__init__()
        self.pokemon_data = pokemon_data
        self.imported_cards = imported_cards or {}  # Dictionary of imported card paths
        self.initUI()
        
    def initUI(self):
        # Set frame properties - match TCGCard styling
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            PokemonCard {
                background-color: gray;
                border-radius: 8px;
                margin: 5px;
            }
            PokemonCard:hover {
                background-color: darkgray;
            }
        """)
        
        # Set fixed width to match TCGCard
        self.setFixedWidth(280)  # Same as TCGCard
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Create layout with same margins as TCGCard
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # Same as TCGCard
        
        # Check if this Pokémon has an imported card
        pokemon_id = str(self.pokemon_data['id'])
        imported_card_path = self.imported_cards.get(pokemon_id)
        
        # Add either the imported card image or the default sprite
        if imported_card_path and os.path.exists(imported_card_path):
            # Use imported TCG card image - same scale as TCGCard
            card_label = QLabel()
            pixmap = QPixmap(imported_card_path)
            # Scale to match TCGCard dimensions
            pixmap = pixmap.scaled(240, 336, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            card_label.setPixmap(pixmap)
            card_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(card_label)
        else:
            # Use default sprite - scaled to similar proportions as TCG cards
            sprite_path = self.pokemon_data.get('local_sprite', '').lstrip('/')
            if os.path.exists(sprite_path):
                sprite_container = QWidget()
                sprite_layout = QVBoxLayout(sprite_container)
                sprite_layout.setContentsMargins(0, 0, 0, 0)
                
                sprite_label = QLabel()
                pixmap = QPixmap(sprite_path)
                # Scale sprite larger to better match TCG card dimensions
                # Using same aspect ratio scaling as TCGCard but slightly smaller
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                sprite_label.setPixmap(pixmap)
                sprite_label.setAlignment(Qt.AlignCenter)
                sprite_layout.addWidget(sprite_label)
                
                # Add the sprite container with some vertical padding to center it
                layout.addWidget(sprite_container, 1, Qt.AlignCenter)
                
                # Add spacer to help align with TCG card proportions
                layout.addSpacing(20)
        
        # Add Pokémon name and ID in the same format as TCGCard
        name_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 10, QFont.Bold))
        name_label.setWordWrap(True)  # Allow text to wrap
        layout.addWidget(name_label)
        
        self.setLayout(layout)

class ImportButton(QToolButton):
    """A button for importing TCG cards as Pokémon sprites"""
    def __init__(self, card_info, parent=None):
        super().__init__(parent)
        self.card_info = card_info
        self.initUI()
        
    def initUI(self):
        # Set button properties
        self.setText("+")
        self.setToolTip("Import this card to My Pokédex")
        self.setFixedSize(30, 30)
        
        # Set cursor to pointing hand (this is the key fix for cursor)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set stylesheet with distinct colors for normal/hover/pressed states
        self.setStyleSheet("""
            QToolButton {
                background-color: #00AA00;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 15px;
                border: 2px solid white;
            }
            QToolButton:hover {
                background-color: #FF8C00;
                border: 2px solid #FFD700;
            }
            QToolButton:pressed {
                background-color: #FF0000;
            }
        """)
        
class TCGCard(QFrame):
    """A custom widget to display a TCG card"""
    def __init__(self, card_path, card_id, card_name="Unknown", artist="Unknown", set_name=None, parent=None):
        super().__init__(parent)
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
                background-color: gray;
                border-radius: 8px;
                margin: 5px;
                position: relative;  /* For positioning the import button */
            }
            TCGCard:hover {
                background-color: darkgray;
            }
        """)
        
        # Set fixed size policy to prevent stretching
        self.setFixedWidth(280)  # Set a fixed width that looks good for TCG cards
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Create layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add card image
        if os.path.exists(self.card_path):
            card_label = QLabel()
            pixmap = QPixmap(self.card_path)
            pixmap = pixmap.scaled(240, 336, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            card_label.setPixmap(pixmap)
            card_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(card_label)
        
        # Add card ID - now properly display alphanumeric IDs
        name_label = QLabel(f"#{self.card_id}")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 10, QFont.Bold))
        name_label.setWordWrap(True)  # Allow text to wrap
        self.main_layout.addWidget(name_label)
        
        # Add set name if provided AND not None (None means explicitly don't show it)
        if self.set_name is not None and self.set_name != "Unknown":
            set_label = QLabel(f"Set: {self.set_name}")
            set_label.setAlignment(Qt.AlignCenter)
            set_label.setWordWrap(True)  # Allow text to wrap
            self.main_layout.addWidget(set_label)
        
        # Add artist if known
        if self.artist and self.artist != "Unknown":
            artist_label = QLabel(f"Artist: {self.artist}")
            artist_label.setAlignment(Qt.AlignCenter)
            artist_label.setWordWrap(True)  # Allow text to wrap
            self.main_layout.addWidget(artist_label)
        
        # Create a container widget to position the card content and import button
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addLayout(self.main_layout)
        
        # Create import button (positioned at bottom right)
        card_info = {
            'path': self.card_path,
            'name': self.card_name,
            'id': self.card_id,
            'set': self.set_name
        }
        
        self.import_button = ImportButton(card_info, self)
        self.import_button.clicked.connect(self.import_card)
        
        # Set fixed position for the import button (bottom right)
        self.import_button.setParent(self)
        
        self.setLayout(container_layout)
        
    def resizeEvent(self, event):
        """Handle resize events to reposition the import button"""
        super().resizeEvent(event)
        # Position the import button at the bottom right with some margin
        button_x = self.width() - self.import_button.width() - 10
        button_y = self.height() - self.import_button.height() - 10
        self.import_button.move(button_x, button_y)


    def import_card(self):
        # Extract Pokémon name from card name
        pokemon_name = self.extract_pokemon_name(self.card_name)
        
        if not pokemon_name:
            QMessageBox.warning(self, "Import Failed", 
                            f"Could not determine which Pokémon this card represents.\n\nCard name: {self.card_name}")
            return
            
        # HYBRID APPROACH:
        # 1. Try the signal/slot method first if connected
        SIGNAL_HUB.import_card_signal.emit(pokemon_name, self.card_path)
        
        # 2. Fallback to direct dashboard reference if available
        if DASHBOARD is not None:
            success = DASHBOARD.import_card_for_pokemon(pokemon_name, self.card_path)
            
            if success:
                QMessageBox.information(self, "Import Successful", 
                                    f"Successfully imported card as {pokemon_name}!")
            else:
                QMessageBox.warning(self, "Import Failed", 
                                f"Could not find a matching Pokémon for '{pokemon_name}' in your Pokédex.")
        else:
            # If we get here, neither method worked
            QMessageBox.critical(self, "Import Failed", 
                            "Could not connect to the dashboard. Please try again.")

    def extract_pokemon_name(self, card_name):
        """
        Extract the Pokémon name from a card name.
        Handles various formats including complex card IDs.
        
        Examples:
        - "Card #56 Lillie's Clefairy ex" -> "Clefairy"
        - "GG01 Hisuian Voltorb" -> "Voltorb"
        - "SV093 Duraludon" -> "Duraludon"
        - "TG01 Flareon" -> "Flareon"
        - "SWSH001 Grookey" -> "Grookey"
        - "Pikachu VMAX" -> "Pikachu"
        - "Snorlax V-UNION" -> "Snorlax"
        - "Special Delivery Bidoof" -> "Bidoof"
        - "Paldean Tauros" -> "Tauros"
        - "Pikachu with Grey Felt Hat" -> "Pikachu"
        """
        import re
        
        # Return None for empty card names
        if not card_name:
            return None
        
        # Store original card_name for debugging if needed
        original_card_name = card_name
        
        # Remove "Card #XX " prefix if present
        card_name = re.sub(r'^Card #\d+\s+', '', card_name)
        
        # Remove complex card ID prefixes at the beginning (more specific pattern)
        # This pattern specifically targets the alphanumeric IDs like SWSH001, GG01
        card_name = re.sub(r'^[A-Za-z]{1,5}\d+\s+', '', card_name)
        
        # Handle specific costume or variant Pokémon first
        # These are direct matches for special cards with descriptive titles
        costume_variants = {
            "Pikachu with Grey Felt Hat": "Pikachu",
            "Pikachu with Red Cap": "Pikachu",
            "Pikachu with Blue Hat": "Pikachu",
            "Flying Pikachu": "Pikachu",
            "Surfing Pikachu": "Pikachu",
            "Detective Pikachu": "Pikachu",
            "Pikachu in Charizard Costume": "Pikachu"
            # Add other costume/variant cards as needed
        }
        
        # Check for exact matches in costume variants
        if card_name in costume_variants:
            return costume_variants[card_name]
        
        # Special case handling for specific Pokémon with unusual names
        special_cases = {
            "Mr. Mime": "Mr. Mime",
            "Mime Jr": "Mime Jr.",
            "Mime Jr.": "Mime Jr.",
            "Farfetch'd": "Farfetch'd",
            "Sirfetch'd": "Sirfetch'd",
            "Type: Null": "Type: Null",
            "Flabébé": "Flabébé",
            "Nidoran♀": "Nidoran♀",
            "Nidoran♂": "Nidoran♂"
        }
        
        # Check for special case matches within the name
        for special_name, replacement in special_cases.items():
            if special_name in card_name:
                return replacement
        
        # Generic pattern for Pokémon with costume/descriptive suffixes
        # This handles cases like "Pikachu with [something]" that aren't in the direct mapping
        costume_match = re.match(r"(\w+)(?:\s+with\s+.+)", card_name)
        if costume_match:
            return costume_match.group(1)
        
        # Handle Special Delivery cards directly
        if card_name.startswith("Special Delivery "):
            return card_name.replace("Special Delivery ", "", 1)
        
        # Handle Tapu cases directly (Tapu Koko, Tapu Lele, etc.)
        if card_name.startswith("Tapu "):
            # Extract just the Pokémon name without any suffixes
            tapu_match = re.match(r'(Tapu\s+\w+)(?:\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|V-FIGHTER|V-HERO))?', card_name)
            if tapu_match:
                return tapu_match.group(1)
            return card_name.split()[0] + " " + card_name.split()[1]
        
        # Handle regional forms - EXTRACT JUST THE BASE POKÉMON NAME
        regional_prefixes = ["Alolan", "Galarian", "Paldean", "Hisuian"]
        for region in regional_prefixes:
            if card_name.startswith(f"{region} "):
                # Extract only the Pokémon name after the region, excluding the region prefix
                region_match = re.match(f'{region}\\s+(\\w+(?:\\s+\\w+)?)(?:\\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION))?', card_name)
                if region_match:
                    return region_match.group(1)  # Return just the Pokémon name without regional prefix
        
        # Handle character's Pokémon (e.g., "Lillie's Clefairy")
        possessive_match = re.match(r"(\w+\'s)\s+(\w+(?:\s+\w+)?)(?:\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION))?", card_name)
        if possessive_match:
            return possessive_match.group(2)
        
        # For VMAX, V-UNION, and similar suffixes - extract the Pokémon name before the suffix
        vmax_match = re.match(r"(\w+(?:\s+\w+)?)\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|V-FIGHTER|V-HERO)", card_name)
        if vmax_match:
            return vmax_match.group(1)
        
        # Handle Radiant, Ancient, Primal prefix cases
        prefix_match = re.match(r"(?:Radiant|Ancient|Primal|Shadow|Origin|Noble|Terastal|Mega|M)\s+(\w+(?:\s+\w+)?)", card_name)
        if prefix_match:
            return prefix_match.group(1)
        
        # If we reach here, the card_name is likely just the Pokémon name or has an unknown format
        # Remove any remaining suffixes
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|V-FIGHTER|V-HERO)(?:\s+.*)?$', '', card_name)
        
        # Return the clean name
        return clean_name

def get_card_number(file_path):
    """
    Advanced card number extraction and sorting function.
    Handles various TCG card numbering formats:
    - Simple numeric: "1 Bulbasaur.png"
    - Basic alphanumeric: "GG01 Hisuian Voltorb.png"
    - Complex prefix with number: "SV093 Duraludon.png"
    - Letter-number format: "TG01 Flareon.png" 
    - Complex multi-part: "SWSH001 Grookey.png"
    """
    filename = os.path.basename(file_path).split('.')[0]
    
    # Extract the identifier from the start of the filename
    try:
        # Split by space and get the first part as identifier
        id_part = filename.split(' ')[0]
        
        # For pure numeric IDs, convert to int for proper sorting
        if id_part.isdigit():
            return (0, "", int(id_part))  # Priority 0 for purely numeric IDs
        
        # For complex alphanumeric IDs, we need to break them down:
        # 1. Extract any letter prefix (SV, TG, SWSH, etc.)
        # 2. Extract the numeric portion
        
        # Match the letter prefix and numeric parts
        prefix_match = re.match(r'^([A-Za-z]+)(\d+)$', id_part)
        
        if prefix_match:
            prefix = prefix_match.group(1)  # Letter part (SV, TG, SWSH)
            num_str = prefix_match.group(2)  # Number part (093, 01, 001)
            
            # Convert the numeric part to int for proper sorting
            num = int(num_str)
            
            # Create a tuple for sorting: (priority, prefix, number)
            # We'll assign different priorities to different prefix types
            # to group similar prefixes together
            
            # Define priority tiers based on common set prefixes
            prefix_priority = {
                # Define known prefix groups and their sort priority
                # Lower numbers appear first
                "SV": 1,    # Scarlet & Violet
                "TG": 2,    # Trainer Gallery
                "SWSH": 3,  # Sword And Shield Black Star Promos
                "SM": 4,    # Sun & Moon
                "XY": 5,    # X & Y
                "BW": 6,    # Black & White
                "DP": 7,    # Diamond & Pearl
                "GG": 8,    # Crown Zenith Galarian Gallery
                # Add more prefixes as needed
            }
            
            # Get the priority for this prefix, default to 100 if unknown
            priority = prefix_priority.get(prefix, 100)
            
            # Return the sorting tuple
            return (priority, prefix, num)
            
        # If no clear pattern, use lexicographic sorting with a high priority
        return (999, id_part, 0)
            
    except (ValueError, IndexError) as e:
        print(f"Error parsing card number from {filename}: {e}")
        # If parsing fails, return a value that sorts to the end
        return (999, "", float('inf'))
    
class ExportDialog(QDialog):
    """Dialog for configuring generation export options"""
    def __init__(self, gen_name, parent=None):
        super().__init__(parent)
        self.gen_name = gen_name
        self.setWindowTitle(f"Export {gen_name}")
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Format options section
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout()
        
        self.format_group = QButtonGroup()
        formats = [
            ("PNG Image Grid", "png"),
            ("PDF Document", "pdf"),
        ]
        
        for i, (format_name, format_id) in enumerate(formats):
            radio = QRadioButton(format_name)
            self.format_group.addButton(radio, i)
            format_layout.addWidget(radio)
            if i == 0:  # Select first option by default
                radio.setChecked(True)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Content options section
        content_group = QGroupBox("Export Options")
        content_layout = QVBoxLayout()
        
        self.include_all = QCheckBox("Include all Pokémon")
        self.include_all.setChecked(True)
        content_layout.addWidget(self.include_all)
        
        self.include_tcg_only = QCheckBox("Only Pokémon with TCG cards")
        self.include_tcg_only.setEnabled(False)  # Disabled by default
        content_layout.addWidget(self.include_tcg_only)
        
        # Connect the include_all checkbox to update include_tcg_only
        self.include_all.stateChanged.connect(self.update_tcg_option)
        
        # Collection name section
        self.include_collection_name = QCheckBox("Include collection name")
        self.include_collection_name.setChecked(True)
        content_layout.addWidget(self.include_collection_name)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Collection Name:"))
        self.collection_name = QLineEdit("My Pokédex Collection")
        name_layout.addWidget(self.collection_name)
        content_layout.addLayout(name_layout)
        
        # Connect collection name checkbox
        self.include_collection_name.stateChanged.connect(
            lambda state: self.collection_name.setEnabled(state == Qt.Checked)
        )
        
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def update_tcg_option(self, state):
        """Update the TCG-only option based on the include_all state"""
        if state == Qt.Checked:
            self.include_tcg_only.setChecked(False)
            self.include_tcg_only.setEnabled(False)
        else:
            self.include_tcg_only.setEnabled(True)
    
    def get_export_config(self):
        """Get the selected export configuration"""
        format_id = ["png", "pdf"][self.format_group.checkedId()]
        
        return {
            "format": format_id,
            "include_all": self.include_all.isChecked(),
            "include_tcg_only": self.include_tcg_only.isChecked(),
            "include_collection_name": self.include_collection_name.isChecked(),
            "collection_name": self.collection_name.text()
        }
        
class GenerationTab(QWidget):
    """A widget representing a single generation tab with fixed-dimension cards"""
    def __init__(self, gen_name, start_id, end_id, pokemon_metadata, imported_cards=None):
        super().__init__()
        self.gen_name = gen_name
        self.start_id = start_id
        self.end_id = end_id
        self.pokemon_metadata = pokemon_metadata
        self.imported_cards = imported_cards or {}
        self.initUI()
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header layout with title and export button
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel(self.gen_name)
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label, 3)  # Give title more space
        
        # Export button
        export_button = QPushButton("Export")
        export_button.setToolTip(f"Export {self.gen_name} collection")
        export_button.clicked.connect(self.export_generation)
        header_layout.addWidget(export_button, 1)
        
        main_layout.addLayout(header_layout)
        
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
        grid_layout.setSpacing(15)  # Add spacing between cards
        
        # Set equal column stretching to maintain alignment
        columns = 4
        for i in range(columns):
            grid_layout.setColumnStretch(i, 1)
        
        # Add Pokémon cards to the grid
        row, col = 0, 0
        for pokemon_id in range(self.start_id, self.end_id + 1):
            pokemon_data = self.get_pokemon_data(pokemon_id)
            if pokemon_data:
                pokemon_card = PokemonCard(pokemon_data, self.imported_cards)
                grid_layout.addWidget(pokemon_card, row, col, Qt.AlignCenter)
                
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
    def export_generation(self):
        """Open export dialog and handle the export process"""
        # Create and show the export dialog
        dialog = ExportDialog(self.gen_name, self)
        
        if dialog.exec_() == QDialog.Accepted:
            # Get export configuration
            config = dialog.get_export_config()
            
            # Choose file location for export
            default_name = f"{self.gen_name.replace(' ', '_')}_Collection"
            file_filter = {
                "png": "Images (*.png)",
                "pdf": "PDF Documents (*.pdf)",
            }[config["format"]]
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Export", default_name, file_filter
            )
            
            if file_path:
                # Handle export based on format
                if config["format"] == "png":
                    self.export_as_image(file_path, config)
                elif config["format"] == "pdf":
                    self.export_as_pdf(file_path, config)

    def export_as_image(self, file_path, config):
        """Export the generation as a PNG image"""
        # Create a temporary widget to render
        export_widget = QWidget()
        export_layout = QVBoxLayout(export_widget)
        export_layout.setSpacing(20)
        export_widget.setStyleSheet("background-color: white;")
        
        # Add header with collection name if enabled
        if config["include_collection_name"]:
            header_widget = QWidget()
            header_layout = QVBoxLayout(header_widget)
            
            title = QLabel(f"{config['collection_name']}")
            title.setFont(QFont('Arial', 20, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(title)
            
            subtitle = QLabel(f"{self.gen_name} - Pokémon #{self.start_id} - #{self.end_id}")
            subtitle.setFont(QFont('Arial', 14))
            subtitle.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(subtitle)
            
            # Add date
            date_label = QLabel(f"Exported on {datetime.datetime.now().strftime('%Y-%m-%d')}")
            date_label.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(date_label)
            
            export_layout.addWidget(header_widget)
        
        # Create grid for Pokémon cards
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(15)
        
        # Set equal column stretching
        columns = 4  # Use 5 columns for export
        for i in range(columns):
            grid_layout.setColumnStretch(i, 1)
        
        # Add Pokémon cards to the grid
        row, col = 0, 0
        cards_added = 0
        
        for pokemon_id in range(self.start_id, self.end_id + 1):
            pokemon_data = self.get_pokemon_data(pokemon_id)
            if not pokemon_data:
                continue
            
            # Check if we should include this Pokémon
            has_tcg_card = str(pokemon_id) in self.imported_cards
            
            if config["include_tcg_only"] and not has_tcg_card:
                continue
            
            # Create a PokemonCard
            pokemon_card = PokemonCard(pokemon_data, self.imported_cards)
            grid_layout.addWidget(pokemon_card, row, col, Qt.AlignCenter)
            cards_added += 1
            
            # Move to the next column or row
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        export_layout.addWidget(grid_widget)
        
        # Add footer
        footer = QLabel("Generated by PokéDextop")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(QFont('Arial', 10, QFont.StyleItalic))
        export_layout.addWidget(footer)
        
        if cards_added == 0:
            QMessageBox.warning(self, "Export Warning", 
                            "No Pokémon cards match your export criteria.")
            return False
        
        # Render the widget to a pixmap
        size = export_widget.sizeHint()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.white)
        
        # Make the widget visible in order to render it correctly
        export_widget.setVisible(True)
        export_widget.render(pixmap)
        
        # Save the pixmap
        if pixmap.save(file_path):
            QMessageBox.information(self, "Export Successful", 
                                f"Successfully exported {self.gen_name} to {file_path}")
            return True
        else:
            QMessageBox.warning(self, "Export Failed", 
                            f"Failed to save export to {file_path}")
            return False

    def export_as_pdf(self, file_path, config):
        """Export the generation as a PDF document with pagination (4x4 grid per page)"""
        try:
            # Create a printer
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            
            # Start the painter
            painter = QPainter()
            if not painter.begin(printer):
                QMessageBox.warning(self, "Export Failed", "Failed to initialize PDF printer")
                return False
            
            # Calculate the cards to include
            cards_to_render = []
            for pokemon_id in range(self.start_id, self.end_id + 1):
                pokemon_data = self.get_pokemon_data(pokemon_id)
                if not pokemon_data:
                    continue
                
                # Check if we should include this Pokémon
                has_tcg_card = str(pokemon_id) in self.imported_cards
                
                if config["include_tcg_only"] and not has_tcg_card:
                    continue
                
                cards_to_render.append((pokemon_id, pokemon_data, has_tcg_card))
            
            if not cards_to_render:
                painter.end()
                QMessageBox.warning(self, "Export Warning", "No Pokémon cards match your export criteria.")
                return False
            
            # Get page rectangle (in device pixels)
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            
            # Define grid parameters - 4x4 grid
            columns = 4
            rows = 4
            cards_per_page = columns * rows
            
            # Calculate card size
            margin = 50  # margin in pixels
            usable_width = page_rect.width() - (2 * margin)
            usable_height = page_rect.height() - (2 * margin)
            
            # Reserve space for header and footer
            header_height = 100 if config["include_collection_name"] else 0
            footer_height = 30
            
            card_width = usable_width / columns
            card_height = (usable_height - header_height - footer_height) / rows
            
            # Calculate number of pages
            total_pages = (len(cards_to_render) + cards_per_page - 1) // cards_per_page
            
            # Draw each page
            for page in range(total_pages):
                if page > 0:
                    # Add a new page for subsequent pages
                    printer.newPage()
                
                # Current page starting position
                x_start = margin
                y_start = margin
                
                # Draw header if enabled
                if config["include_collection_name"]:
                    painter.save()
                    
                    # Draw collection name
                    font = QFont('Arial', 14, QFont.Bold)
                    painter.setFont(font)
                    header_rect = QRectF(x_start, y_start, usable_width, 30)
                    painter.drawText(header_rect, Qt.AlignCenter, config["collection_name"])
                    
                    # Draw generation info
                    font = QFont('Arial', 12)
                    painter.setFont(font)
                    gen_rect = QRectF(x_start, y_start + 30, usable_width, 25)
                    painter.drawText(gen_rect, Qt.AlignCenter, 
                                f"{self.gen_name} - Page {page + 1} of {total_pages}")
                    
                    # Draw date
                    font = QFont('Arial', 10)
                    painter.setFont(font)
                    date_rect = QRectF(x_start, y_start + 55, usable_width, 20)
                    painter.drawText(date_rect, Qt.AlignCenter, 
                                f"Exported on {datetime.datetime.now().strftime('%Y-%m-%d')}")
                    
                    painter.restore()
                    
                    # Update starting position for cards
                    y_start += header_height
                
                # Draw cards for this page
                for i in range(cards_per_page):
                    card_index = page * cards_per_page + i
                    if card_index >= len(cards_to_render):
                        break
                    
                    pokemon_id, pokemon_data, has_tcg_card = cards_to_render[card_index]
                    
                    # Calculate card position
                    row = i // columns
                    col = i % columns
                    
                    x = x_start + (col * card_width)
                    y = y_start + (row * card_height)
                    
                    # Create a PokemonCard
                    pokemon_card = PokemonCard(pokemon_data, self.imported_cards)
                    
                    # Render the card to a pixmap
                    card_pixmap = QPixmap(pokemon_card.size())
                    card_pixmap.fill(Qt.transparent)
                    pokemon_card.render(card_pixmap)
                    
                    # Calculate scaling for the card to fit in the allocated space
                    scale_width = card_width * 0.9 / card_pixmap.width()
                    scale_height = card_height * 0.9 / card_pixmap.height()
                    scale = min(scale_width, scale_height)
                    
                    # Center the card in its cell
                    card_scaled_width = card_pixmap.width() * scale
                    card_scaled_height = card_pixmap.height() * scale
                    
                    x_centered = x + (card_width - card_scaled_width) / 2
                    y_centered = y + (card_height - card_scaled_height) / 2
                    
                    # Draw the card
                    target_rect = QRectF(x_centered, y_centered, card_scaled_width, card_scaled_height)
                    source_rect = QRectF(0, 0, card_pixmap.width(), card_pixmap.height())
                    painter.drawPixmap(target_rect, card_pixmap, source_rect)
                    
                    # # Draw a border around the card
                    # painter.setPen(QPen(Qt.white, 1))
                    # painter.drawRect(target_rect)
                
                # Draw footer
                font = QFont('Arial', 9, QFont.StyleItalic)
                painter.setFont(font)
                footer_rect = QRectF(x_start, page_rect.height() - margin - footer_height, 
                                    usable_width, footer_height)
                painter.drawText(footer_rect, Qt.AlignCenter, "Generated by PokéDextop")
            
            # End the painter
            painter.end()
            
            QMessageBox.information(self, "Export Successful", 
                                f"Successfully exported {self.gen_name} to {file_path} " +
                                f"({total_pages} pages)")
            return True
            
        except Exception as e:
            # Catch any errors that might occur during the PDF creation
            QMessageBox.critical(self, "Export Failed", 
                            f"Failed to create PDF: {str(e)}\n"
                            "Please make sure you have the necessary PyQt5 modules installed.")
            return False

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
        
        # Sort card files by the enhanced card number function
        try:
            card_files = sorted(card_files, key=get_card_number)
        except TypeError as e:
            # Fallback to simple sorting if the key function causes issues
            print(f"Warning: Using fallback sorting for {self.set_name} due to: {e}")
            card_files = sorted(card_files)
        
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
            
            # Extract the card identifier for display - now handles complex IDs
            try:
                card_id = filename.split(' ')[0]
            except (IndexError, ValueError):
                card_id = filename
                
            # Create TCG card without passing set_name (set to None to ensure it's not displayed)
            tcg_card = TCGCard(card_file, card_id, card_name, artist, None)
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
        # Set up global dashboard reference
        global DASHBOARD
        DASHBOARD = self
        
        # Load data
        self.pokemon_metadata = self.load_pokemon_metadata()
        self.tcg_metadata = self.load_tcg_metadata()
        self.imported_cards = self.load_imported_cards()
        
        # Set up generations
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
        
        # Connect to the signal hub
        SIGNAL_HUB.import_card_signal.connect(self.handle_import_signal)
        
        self.initUI()
    
    def handle_import_signal(self, pokemon_name, card_path):
        """Handle the import card signal"""
        # This method is called when a card is imported via the signal system
        self.import_card_for_pokemon(pokemon_name, card_path)
        
    def initUI(self):
        self.setWindowTitle('PokéDextop')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create the central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create main tab widget
        self.main_tabs = QTabWidget()
        
        # Create My Pokédex Tab (formerly Pokémon Sprites)
        sprites_tab = QWidget()
        sprites_layout = QVBoxLayout(sprites_tab)
        
        # Create a tab widget for generations
        self.gen_tabs = QTabWidget()
        
        # Add tabs for each generation
        for gen_name, (start_id, end_id) in self.generations.items():
            gen_tab = GenerationTab(gen_name, start_id, end_id, self.pokemon_metadata, self.imported_cards)
            self.gen_tabs.addTab(gen_tab, gen_name)
        
        sprites_layout.addWidget(self.gen_tabs)
        
        # Add the sprites tab to main tabs with the new name
        self.main_tabs.addTab(sprites_tab, "My Pokédex")
        
        # Create Search by Set Tab (formerly TCG Cards Tab)
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
        
        # Add the TCG tab to main tabs with the new name
        self.main_tabs.addTab(tcg_tab, "Search by Set")
        
        # Create Search by Pokemon Tab
        search_tab = PokemonSearchTab(self.pokemon_metadata, self.tcg_metadata)
        self.main_tabs.addTab(search_tab, "Search by Pokémon")
        
        # Add the main tab widget to the layout
        main_layout.addWidget(self.main_tabs)
        
        # Set up status bar
        pokemon_count = len(self.pokemon_metadata)
        tcg_set_count = len(set_dirs) if 'set_dirs' in locals() else 0
        imported_count = len(self.imported_cards)
        
        self.statusBar().showMessage(
            f"Pokémon: {pokemon_count} | TCG Sets: {tcg_set_count} | Imported Cards: {imported_count}"
        )
        
    def import_card_for_pokemon(self, pokemon_name, card_path):
        """Import a TCG card to replace a Pokémon sprite"""
        # Find Pokémon ID by name
        pokemon_id = None
        for pid, data in self.pokemon_metadata.items():
            if data.get('name', '').lower() == pokemon_name.lower():
                pokemon_id = pid
                break
                
        if not pokemon_id:
            # Try fuzzy matching if exact match fails
            best_match = None
            best_score = 0
            for pid, data in self.pokemon_metadata.items():
                name = data.get('name', '')
                # Simple similarity score: length of common substring
                if pokemon_name.lower() in name.lower() or name.lower() in pokemon_name.lower():
                    score = len(name) / max(len(name), len(pokemon_name))
                    if score > best_score:
                        best_score = score
                        best_match = pid
                        
            # Use best match if score is good enough
            if best_score > 0.5:
                pokemon_id = best_match
        
        if not pokemon_id:
            return False
            
        # Update imported cards dictionary
        self.imported_cards[pokemon_id] = card_path
        
        # Save to file
        self.save_imported_cards()
        
        # Update the UI
        self.refresh_pokedex()
        
        # Update status bar
        pokemon_count = len(self.pokemon_metadata)
        tcg_set_count = sum(1 for _ in os.listdir(os.path.join('assets', 'tcg_cards')) 
                          if os.path.isdir(os.path.join('assets', 'tcg_cards', _))) if os.path.exists(os.path.join('assets', 'tcg_cards')) else 0
        imported_count = len(self.imported_cards)
        
        self.statusBar().showMessage(
            f"Pokémon: {pokemon_count} | TCG Sets: {tcg_set_count} | Imported Cards: {imported_count}"
        )
        
        return True
        
    def refresh_pokedex(self):
        """Refresh the Pokédex tab to show updated imported cards"""
        # Create a new Gen tabs widget
        new_gen_tabs = QTabWidget()
        
        # Add tabs for each generation with updated imported cards
        for gen_name, (start_id, end_id) in self.generations.items():
            gen_tab = GenerationTab(gen_name, start_id, end_id, self.pokemon_metadata, self.imported_cards)
            new_gen_tabs.addTab(gen_tab, gen_name)
            
        # Get the My Pokédex tab widget
        pokedex_tab = self.main_tabs.widget(0)
        
        # Find the layout of the My Pokédex tab
        pokedex_layout = pokedex_tab.layout()
        
        # Remove the old gen tabs widget
        old_gen_tabs = pokedex_layout.itemAt(0).widget()
        pokedex_layout.removeWidget(old_gen_tabs)
        old_gen_tabs.deleteLater()
        
        # Add the new gen tabs widget
        pokedex_layout.addWidget(new_gen_tabs)
        self.gen_tabs = new_gen_tabs
        
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
        
    def load_imported_cards(self):
        """Load imported cards data from file"""
        if os.path.exists(IMPORTED_CARDS_FILE):
            try:
                with open(IMPORTED_CARDS_FILE, 'r') as f:
                    imported_cards = json.load(f)
                    print(f"Loaded {len(imported_cards)} imported cards")
                    return imported_cards
            except Exception as e:
                print(f"Error loading imported cards: {e}")
        
        return {}
        
    def save_imported_cards(self):
        """Save imported cards data to file"""
        try:
            with open(IMPORTED_CARDS_FILE, 'w') as f:
                json.dump(self.imported_cards, f, indent=2)
                print(f"Saved {len(self.imported_cards)} imported cards")
        except Exception as e:
            print(f"Error saving imported cards: {e}")

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