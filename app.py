import sys
import os
import json
import sqlite3
import hashlib
import time
import math
import requests
from PyQt6 import sip
from datetime import datetime
from difflib import SequenceMatcher

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QScrollArea,
                            QGridLayout, QTabWidget, QSizePolicy, QFrame,
                            QComboBox, QLineEdit, QCompleter, QMessageBox, QDialog, QGroupBox, 
                            QCheckBox, QFileDialog,
                            QProgressBar, QTextEdit, QSpinBox, QListWidget, QListWidgetItem,
                            QAbstractItemView, QTableWidget, QTableWidgetItem, QHeaderView, QProgressDialog)

from PyQt6.QtGui import (QPixmap, QFont, QPainter, QPen, QColor)

from PyQt6.QtCore import (Qt, QStringListModel, pyqtSignal, QObject, QRect, 
                         QThread, QTimer, QUrl)

from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Pokemon TCG SDK imports
from pokemontcgsdk import Card, Set
from pokemontcgsdk.restclient import RestClient, PokemonTcgException


# =============================================================================
# ExPORT FUNCTION ARCHITECTURE
# =============================================================================


class CollectionExportOptionsDialog(QDialog):
    """Dialog for configuring collection export options"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.export_config = {
            'custom_title': 'My Pokémon Collection',
            'include_pokedex_info': True,
            'include_set_label': True,
            'include_artist_label': False,
            'cards_per_row': 4,
            'image_quality': 'high',
            'generation_filter': 'all',
            'tcg_only_mode': False  # Default to Full Pokédex Grid
        }
        self.setWindowTitle("Export Collection")
        self.setMinimumSize(450, 600)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Export Your Collection - Options")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Collection info
        collection_info = self.get_collection_info()
        info_label = QLabel(f"Found {collection_info['total_cards']} cards across {collection_info['generations']} generations")
        info_label.setStyleSheet("color: #bdc3c7; font-size: 12px; margin-bottom: 15px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Generation filter
        gen_group = QGroupBox("Generation Filter")
        gen_layout = QVBoxLayout()
        
        self.gen_combo = QComboBox()
        self.gen_combo.addItem("All Generations", "all")
        
        # Add individual generations
        generations = self.get_available_generations()
        for gen_num, gen_name, card_count in generations:
            self.gen_combo.addItem(f"{gen_name} ({card_count} cards)", gen_num)
        
        self.gen_combo.currentTextChanged.connect(self.update_preview)
        gen_layout.addWidget(self.gen_combo)
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # Label options
        labels_group = QGroupBox("Card Labels to Include")
        labels_layout = QVBoxLayout()
        
        self.pokedex_checkbox = QCheckBox("Pokédex Number & Name")
        self.pokedex_checkbox.setChecked(True)
        self.pokedex_checkbox.setStyleSheet("color: white;")
        self.pokedex_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.pokedex_checkbox)
        
        self.set_checkbox = QCheckBox("Set Name")
        self.set_checkbox.setChecked(True)
        self.set_checkbox.setStyleSheet("color: white;")
        self.set_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.set_checkbox)
        
        self.artist_checkbox = QCheckBox("Artist Name")
        self.artist_checkbox.setChecked(False)
        self.artist_checkbox.setStyleSheet("color: white;")
        self.artist_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.artist_checkbox)
        
        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)
        
        # Custom title input
        title_group = QGroupBox("Collection Title")
        title_layout = QVBoxLayout()
        
        title_label = QLabel("Enter a custom title for your collection:")
        title_label.setStyleSheet("color: white; font-size: 11px;")
        title_layout.addWidget(title_label)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("My Pokémon Collection")
        self.title_input.setText("My Pokémon Collection")
        self.title_input.setStyleSheet("padding: 8px; font-size: 12px;")
        self.title_input.textChanged.connect(self.update_preview)
        title_layout.addWidget(self.title_input)
        
        title_group.setLayout(title_layout)
        layout.addWidget(title_group)
        
        # Layout options
        layout_group = QGroupBox("Layout Options")
        layout_layout = QVBoxLayout()
        
        # Cards per row
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Cards per row:"))
        self.cards_per_row_spin = QSpinBox()
        self.cards_per_row_spin.setRange(2, 5)  # Min 2, Max 5 as requested
        self.cards_per_row_spin.setValue(4)      # Default 4 as requested
        self.cards_per_row_spin.valueChanged.connect(self.update_preview)
        row_layout.addWidget(self.cards_per_row_spin)
        row_layout.addStretch()
        layout_layout.addLayout(row_layout)
        
        # Quality options
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Image quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("High (Print Quality)", "high")
        self.quality_combo.addItem("Medium (Web Sharing)", "medium")
        self.quality_combo.addItem("Low (Quick Preview)", "low")
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        layout_layout.addLayout(quality_layout)
        
        # TCG Cards Only option
        self.tcg_only_checkbox = QCheckBox("TCG Cards Only (exclude Pokémon without imported cards)")
        self.tcg_only_checkbox.setChecked(False)  # Default to Full Pokédex Grid
        self.tcg_only_checkbox.setStyleSheet("color: white;")
        self.tcg_only_checkbox.toggled.connect(self.on_tcg_only_toggled)
        layout_layout.addWidget(self.tcg_only_checkbox)

        layout_group.setLayout(layout_layout)
        layout.addWidget(layout_group)
        
        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("""
            background-color: #2c3e50; 
            border: 1px solid #34495e; 
            padding: 8px;
            color: white;
            font-size: 11px;
        """)
        self.preview_label.setMinimumHeight(120)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.export_btn = QPushButton("📸 Export Collection")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
        # Initial preview update
        self.update_preview()
    
    def get_collection_info(self):
        """Get collection information based on current mode"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Check if checkbox exists yet (it might not during initial UI setup)
        tcg_only_mode = hasattr(self, 'tcg_only_checkbox') and self.tcg_only_checkbox.isChecked()
        
        if tcg_only_mode:
            # TCG Cards Only mode - only count imported cards
            cursor.execute("""
                SELECT COUNT(*) as total_cards,
                    COUNT(DISTINCT p.generation) as generations
                FROM gold_user_collections uc
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
            """)
        else:
            # Full Pokédex Grid mode - count all Pokémon in selected generation(s)
            if hasattr(self, 'gen_combo') and self.gen_combo.currentData() != 'all':
                # Specific generation
                cursor.execute("""
                    SELECT COUNT(*) as total_pokemon,
                        1 as generations
                    FROM silver_pokemon_master p
                    WHERE p.generation = ?
                """, (self.gen_combo.currentData(),))
            else:
                # All generations
                cursor.execute("""
                    SELECT COUNT(*) as total_pokemon,
                        COUNT(DISTINCT p.generation) as generations
                    FROM silver_pokemon_master p
                """)
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_cards': result[0] if result else 0,
            'generations': result[1] if result else 0
        }
    
    def get_available_generations(self):
        """Get generations that have cards in the collection"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.generation, g.name, COUNT(*) as card_count
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
            JOIN gold_pokemon_generations g ON p.generation = g.generation
            GROUP BY p.generation, g.name
            ORDER BY p.generation
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def update_preview(self):
        """Update the preview text"""
        generation = self.gen_combo.currentData()
        cards_per_row = self.cards_per_row_spin.value()
        custom_title = self.title_input.text().strip() or "My Pokémon Collection"
        tcg_only_mode = self.tcg_only_checkbox.isChecked()
        
        # Get card count for preview
        collection_info = self.get_collection_info()
        card_count = collection_info['total_cards']
        
        if generation == "all":
            gen_text = "All Generations"
        else:
            gen_text = f"Generation {generation}"
        
        if card_count == 0:
            if tcg_only_mode:
                self.preview_label.setText("No imported TCG cards found for selected generation.")
            else:
                self.preview_label.setText("No Pokémon found for selected generation.")
            self.export_btn.setEnabled(False)
            return
        
        self.export_btn.setEnabled(True)
        
        # Calculate grid dimensions
        rows = math.ceil(card_count / cards_per_row)
        
        preview_text = f"Export Preview:\n\n"
        preview_text += f"📋 Title: \"{custom_title}\"\n"
        preview_text += f"🎯 Generation: {gen_text}\n"
        
        # Different preview text based on mode
        if tcg_only_mode:
            preview_text += f"🃏 Mode: TCG Cards Only\n"
            preview_text += f"🃏 Cards: {card_count} imported cards\n"
        else:
            preview_text += f"📖 Mode: Full Pokédex Grid\n"
            preview_text += f"🎮 Pokémon: {card_count} total\n"
            preview_text += f"   (Mix of imported cards + game sprites)\n"
        
        preview_text += f"📐 Grid: {rows} rows × {cards_per_row} columns\n\n"
        
        preview_text += "Card Labels:\n"
        labels = []
        if self.pokedex_checkbox.isChecked():
            labels.append("• Pokédex # & Name")
        if self.set_checkbox.isChecked():
            labels.append("• Set Name")
        if self.artist_checkbox.isChecked():
            labels.append("• Artist")
        
        if labels:
            preview_text += "\n".join(labels)
        else:
            preview_text += "• No labels (cards only)"
        
        quality = self.quality_combo.currentText()
        preview_text += f"\n\nQuality: {quality}"
        preview_text += f"\n\nFooter: Export date + \"Exported by PokéDextop\""
        
        self.preview_label.setText(preview_text)
        
    def on_tcg_only_toggled(self, checked):
        """Handle TCG Cards Only checkbox toggle with confirmation"""
        if checked:
            # Show confirmation dialog
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("TCG Cards Only Export")
            msg_box.setText("TCG Cards Only Mode")
            msg_box.setInformativeText(
                "This mode will only include Pokémon that you have imported TCG cards for. "
                "Pokémon without imported cards will be excluded from the export.\n\n"
                "For a complete Pokédex grid showing your full collection progress "
                "(including Pokémon without cards), leave this option unchecked.\n\n"
                "Continue with TCG Cards Only export?"
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            
            result = msg_box.exec()
            
            if result == QMessageBox.StandardButton.Cancel:
                # User cancelled, uncheck the box
                self.tcg_only_checkbox.setChecked(False)
                return
        
        # Update preview with new mode
        self.update_preview()
    
    def start_export(self):
        """Start the export process"""
        # Update config
        self.export_config.update({
            'custom_title': self.title_input.text().strip() or "My Pokémon Collection",
            'include_pokedex_info': self.pokedex_checkbox.isChecked(),
            'include_set_label': self.set_checkbox.isChecked(),
            'include_artist_label': self.artist_checkbox.isChecked(),
            'cards_per_row': self.cards_per_row_spin.value(),
            'image_quality': self.quality_combo.currentData(),
            'generation_filter': self.gen_combo.currentData(),
            'tcg_only_mode': self.tcg_only_checkbox.isChecked()
        })
        
        # Get export file path
        # Create filename from custom title
        safe_title = "".join(c for c in self.export_config['custom_title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_').lower()
        
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection", filename, "PNG Images (*.png)"
        )
        
        if file_path:
            self.export_config['file_path'] = file_path
            self.accept()
    
    def get_export_config(self):
        """Get the export configuration"""
        return self.export_config


class CollectionImageGenerator(QThread):
    """Thread for generating collection image"""
    
    progress_updated = pyqtSignal(int, str)
    generation_complete = pyqtSignal(str)
    generation_error = pyqtSignal(str)
    
    def __init__(self, db_manager, export_config):
        super().__init__()
        self.db_manager = db_manager
        self.config = export_config
        self.network_manager = QNetworkAccessManager()
        self.downloaded_images = {}
    
    def run(self):
        """Generate the collection image"""
        try:
            # DEBUG: Print export configuration
            print(f"\n=== EXPORT DEBUG START ===")
            print(f"TCG Only Mode: {self.config.get('tcg_only_mode', 'NOT SET')}")
            print(f"Generation Filter: {self.config.get('generation_filter', 'NOT SET')}")
            print(f"Cards per row: {self.config.get('cards_per_row', 'NOT SET')}")
            print(f"Config keys: {list(self.config.keys())}")
            
            # Step 1: Get collection data
            self.progress_updated.emit(10, "Loading collection data...")
            collection_data = self.get_collection_data()
            
            if not collection_data:
                self.generation_error.emit("No cards found in collection.")
                return
            
            # DEBUG: Print collection data summary
            print(f"\n--- COLLECTION DATA DEBUG ---")
            print(f"Total items returned: {len(collection_data)}")
            if collection_data:
                content_types = {}
                for item in collection_data:
                    content_type = item.get('content_type', 'UNKNOWN')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                    
                print(f"Content type breakdown: {content_types}")
                print(f"First 3 items:")
                for i, item in enumerate(collection_data[:3]):
                    print(f"  [{i}] Pokemon #{item['pokemon_id']} {item['pokemon_name']} - Type: {item['content_type']} - Has URL: {bool(item.get('image_url'))}")
            
            # Step 2: Download images
            self.progress_updated.emit(20, "Downloading card images...")
            self.download_all_images(collection_data)
            
            # Step 3: Create composite image
            self.progress_updated.emit(70, "Creating collection image...")
            final_image = self.create_collection_image(collection_data)
            
            # Step 4: Save image
            self.progress_updated.emit(90, "Saving image...")
            success = final_image.save(self.config['file_path'], 'PNG', 95)
            
            if success:
                self.progress_updated.emit(100, "Export complete!")
                self.generation_complete.emit(self.config['file_path'])
            else:
                self.generation_error.emit("Failed to save image file.")
                
        except Exception as e:
            self.generation_error.emit(f"Export failed: {str(e)}")
    
    def get_collection_data(self):
        """Get collection data from database based on export mode"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # DEBUG: Print which branch we're taking
        print(f"\n--- SQL QUERY DEBUG ---")
        print(f"TCG Only Mode: {self.config['tcg_only_mode']}")
        print(f"Generation Filter: {self.config['generation_filter']}")
    
        if self.config['tcg_only_mode']:
            # TCG Cards Only mode - only get imported cards
            if self.config['generation_filter'] == 'all':
                print("EXECUTING: TCG Cards Only query")
                
                query = """
                    SELECT uc.pokemon_id, uc.card_id, p.name as pokemon_name,
                        c.name as card_name, c.set_name, c.artist, c.image_url_large,
                        c.image_url_small, p.generation, 'tcg_card' as content_type
                    FROM gold_user_collections uc
                    JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                    JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                    ORDER BY p.pokemon_id
                """
                cursor.execute(query)
            else:
                
                query = """
                    SELECT uc.pokemon_id, uc.card_id, p.name as pokemon_name,
                        c.name as card_name, c.set_name, c.artist, c.image_url_large,
                        c.image_url_small, p.generation, 'tcg_card' as content_type
                    FROM gold_user_collections uc
                    JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                    JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                    WHERE p.generation = ?
                    ORDER BY p.pokemon_id
                """
                cursor.execute(query, (self.config['generation_filter'],))
        else:
            print("EXECUTING: Full Pokédex Grid query")
            # Full Pokédex Grid mode - get all Pokémon, with or without cards
            if self.config['generation_filter'] == 'all':
                query = """
                    SELECT p.pokemon_id, uc.card_id, p.name as pokemon_name,
                        c.name as card_name, c.set_name, c.artist, c.image_url_large,
                        c.image_url_small, p.generation,
                        CASE WHEN uc.card_id IS NOT NULL THEN 'tcg_card' ELSE 'sprite' END as content_type
                    FROM silver_pokemon_master p
                    LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
                    LEFT JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                    ORDER BY p.pokemon_id
                """
                cursor.execute(query)
            else:
                query = """
                    SELECT p.pokemon_id, uc.card_id, p.name as pokemon_name,
                        c.name as card_name, c.set_name, c.artist, c.image_url_large,
                        c.image_url_small, p.generation,
                        CASE WHEN uc.card_id IS NOT NULL THEN 'tcg_card' ELSE 'sprite' END as content_type
                    FROM silver_pokemon_master p
                    LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
                    LEFT JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                    WHERE p.generation = ?
                    ORDER BY p.pokemon_id
                """
                cursor.execute(query, (self.config['generation_filter'],))
        
        results = cursor.fetchall()
        conn.close()
        print(f"Raw SQL results count: {len(results)}")
        if results:
            print(f"First raw result: {results[0]}")
            print(f"Sample result fields: pokemon_id={results[0][0]}, content_type={results[0][9] if len(results[0]) > 9 else 'MISSING'}")
        
        return [
            {
                'pokemon_id': row[0],
                'card_id': row[1], 
                'pokemon_name': row[2],
                'card_name': row[3],
                'set_name': row[4],
                'artist': row[5],
                'image_url': row[6] or row[7],  # Prefer large, fallback to small
                'generation': row[8],
                'content_type': row[9]  # 'tcg_card' or 'sprite'
            }
            for row in results
        ]
    
    def download_all_images(self, collection_data):
        """Download all images (TCG cards and sprites)"""
        total_items = len(collection_data)
        
        print(f"\n--- IMAGE DOWNLOAD DEBUG ---")
        print(f"Starting download for {total_items} items")
    
        for i, item_data in enumerate(collection_data):
            pokemon_id = item_data['pokemon_id']
            content_type = item_data['content_type']
            
            print(f"\nDownloading [{i+1}/{total_items}] Pokemon #{pokemon_id} - Type: {content_type}")
            
            try:
                if content_type == 'tcg_card' and item_data['image_url']:
                    print(f"  TCG CARD: {item_data['image_url']}")
                    # Download TCG card image
                    response = requests.get(item_data['image_url'], timeout=10)
                    response.raise_for_status()
                    
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    
                    if not pixmap.isNull():
                        self.downloaded_images[pokemon_id] = pixmap
                    else:
                        self.downloaded_images[pokemon_id] = self.create_placeholder_image()
                        
                elif content_type == 'sprite':
                    
                    # Download Pokémon sprite
                    sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
                    print(f"  SPRITE: {sprite_url}")
                    response = requests.get(sprite_url, timeout=10)
                    response.raise_for_status()
                    
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    
                    if not pixmap.isNull():
                        self.downloaded_images[pokemon_id] = pixmap
                    else:
                        self.downloaded_images[pokemon_id] = self.create_placeholder_image()
                else:
                    # Fallback to placeholder
                    self.downloaded_images[pokemon_id] = self.create_placeholder_image()
                    print(f"  PLACEHOLDER: No valid content_type or URL")
                
            except Exception as e:
                print(f"Failed to download image for Pokemon #{pokemon_id}: {e}")
                self.downloaded_images[pokemon_id] = self.create_placeholder_image()
                print(f"  ERROR: {e}")
            
            # Update progress
            progress = 20 + int((i + 1) / total_items * 50)
            self.progress_updated.emit(progress, f"Downloaded {i + 1}/{total_items} images...")
            
    
    def create_placeholder_image(self):
        """Create a placeholder image for missing cards"""
        pixmap = QPixmap(245, 342)  # Standard card dimensions
        pixmap.fill(QColor(52, 73, 94))  # Dark gray
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(127, 140, 141)))
        painter.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        
        rect = pixmap.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Image\nAvailable")
        painter.end()
        
        return pixmap
    
    def create_collection_image(self, collection_data):
        """Create the final collection image with mixed content support - Safe Version"""
        print(f"\n--- IMAGE CREATION DEBUG ---")
        print(f"Creating image for {len(collection_data)} items")
        print(f"Downloaded images available: {len(self.downloaded_images)}")
        print(f"Downloaded image keys: {list(self.downloaded_images.keys())[:10]}...")  # First 10 keys
        
        # Calculate dimensions
        cards_per_row = self.config['cards_per_row']
        total_items = len(collection_data)
        rows = math.ceil(total_items / cards_per_row)
        
        # Quality settings - standardized for mixed content
        if self.config['image_quality'] == 'high':
            item_width, item_height = 200, 200  # Standardized square for mixed content
            spacing = 20
            font_size_title = 24
            font_size_labels = 10
        elif self.config['image_quality'] == 'medium':
            item_width, item_height = 150, 150
            spacing = 15
            font_size_title = 20
            font_size_labels = 9
        else:  # low
            item_width, item_height = 100, 100
            spacing = 10
            font_size_title = 16
            font_size_labels = 8
        
        # Calculate label height
        label_height = 0
        if any([self.config['include_pokedex_info'], 
                self.config['include_set_label'], 
                self.config['include_artist_label']]):
            label_height = 60
        
        # Calculate total dimensions
        header_height = 80
        footer_height = 60
        total_width = (cards_per_row * item_width) + ((cards_per_row + 1) * spacing)
        total_height = header_height + (rows * (item_height + label_height + spacing)) + spacing + footer_height
        
        # Create the final image
        final_image = QPixmap(total_width, total_height)
        final_image.fill(QColor(44, 62, 80))  # Dark blue background
        
        # Create painter with proper error handling
        painter = QPainter()
        if not painter.begin(final_image):
            print("ERROR: Failed to begin painting")
            return final_image
        
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw header with custom title
            self.draw_header(painter, total_width, header_height, collection_data, font_size_title)
            
            # Draw items (cards/sprites)
            current_y = header_height + spacing
            for i, item_data in enumerate(collection_data):
                row = i // cards_per_row
                col = i % cards_per_row
                
                x = spacing + col * (item_width + spacing)
                y = current_y + row * (item_height + label_height + spacing)
                
                # Draw item image (standardized size for both cards and sprites)
                pokemon_id = item_data['pokemon_id']
                
                # DEBUG: Only debug first 5 items to avoid spam
                if i < 5:
                    print(f"  Drawing [{i}] Pokemon #{pokemon_id} - Available in downloads: {pokemon_id in self.downloaded_images}")
                
                # Safe image drawing with null checks
                if pokemon_id in self.downloaded_images:
                    try:
                        item_image = self.downloaded_images[pokemon_id]
                        if item_image and not item_image.isNull():
                            content_type = item_data.get('content_type', 'sprite')
                            
                            # Apply different scaling based on content type
                            if content_type == 'sprite':
                                # For sprites, smaller scale with fast transformation
                                target_width = min(item_width - 20, 100)
                                target_height = min(item_height - 20, 100)
                            else:
                                # For TCG cards, larger scale
                                target_width = item_width - 10
                                target_height = item_height - 10
                            
                            # Safe scaling
                            scaled_item = item_image.scaled(
                                target_width, target_height,
                                Qt.AspectRatioMode.KeepAspectRatio, 
                                Qt.TransformationMode.SmoothTransformation
                            )
                            
                            if not scaled_item.isNull():
                                # Center the scaled image
                                item_x = x + (item_width - scaled_item.width()) // 2
                                item_y = y + (item_height - scaled_item.height()) // 2
                                
                                # Draw image
                                painter.drawPixmap(item_x, item_y, scaled_item)
                                
                                # Simple border (removed complex border logic)
                                if content_type == 'sprite':
                                    painter.setPen(QPen(QColor(135, 206, 235), 1))  # Light blue, thinner
                                else:
                                    painter.setPen(QPen(QColor(52, 73, 94), 1))   # Dark, thinner
                                
                                painter.drawRect(item_x - 1, item_y - 1, scaled_item.width() + 2, scaled_item.height() + 2)
                        
                    except Exception as e:
                        print(f"  ERROR drawing Pokemon #{pokemon_id}: {e}")
                        # Continue to next item instead of crashing
                        
                # Draw labels (simplified)
                if label_height > 0:
                    try:
                        self.draw_item_labels(
                            painter, item_data, x, y + item_height + 5, 
                            item_width, label_height, font_size_labels
                        )
                    except Exception as e:
                        print(f"  ERROR drawing labels for Pokemon #{pokemon_id}: {e}")
            
            # Draw footer with date and branding
            footer_y = total_height - footer_height
            self.draw_footer(painter, total_width, footer_height, footer_y, font_size_title - 4)
            
        except Exception as e:
            print(f"PAINTING ERROR: {e}")
        finally:
            # Ensure painter is properly ended
            painter.end()
        
        print("Image creation completed successfully")
        return final_image
    
    def draw_header(self, painter, width, height, collection_data, font_size):
        """Draw the header section with custom title"""
        painter.fillRect(0, 0, width, height, QColor(52, 73, 94))
        
        # Custom title
        painter.setPen(QPen(QColor(255, 255, 255)))
        title_font = QFont('Arial', font_size, QFont.Weight.Bold)
        painter.setFont(title_font)
        
        custom_title = self.config['custom_title']
        title_rect = QRect(0, 10, width, 35)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, custom_title)
        
        # Subtitle with card count
        subtitle_font = QFont('Arial', font_size - 6)
        painter.setFont(subtitle_font)
        painter.setPen(QPen(QColor(189, 195, 199)))  # Light gray
        
        total_cards = len(collection_data)
        if self.config['generation_filter'] == 'all':
            subtitle = f"{total_cards} cards from all generations"
        else:
            subtitle = f"{total_cards} cards from Generation {self.config['generation_filter']}"
        
        subtitle_rect = QRect(0, 45, width, 25)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, subtitle)
    
    def draw_footer(self, painter, width, height, y_position, font_size):
        """Draw the footer section with export date and branding"""
        # Footer background
        painter.fillRect(0, y_position, width, height, QColor(52, 73, 94))
        
        # Export date
        painter.setPen(QPen(QColor(189, 195, 199)))  # Light gray
        date_font = QFont('Arial', font_size)
        painter.setFont(date_font)
        
        export_date = datetime.now().strftime('%B %d, %Y')
        date_text = f"Exported on {export_date}"
        
        date_rect = QRect(0, y_position + 10, width, 20)
        painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, date_text)
        
        # PokéDextop branding
        branding_font = QFont('Arial', font_size - 2, QFont.Weight.Bold)
        painter.setFont(branding_font)
        painter.setPen(QPen(QColor(52, 152, 219)))  # Blue color
        
        branding_text = "Exported by PokéDextop"
        branding_rect = QRect(0, y_position + 30, width, 20)
        painter.drawText(branding_rect, Qt.AlignmentFlag.AlignCenter, branding_text)
    
    def draw_card_labels(self, painter, card_data, x, y, width, height, font_size):
        """Draw labels for a card"""
        painter.setPen(QPen(QColor(255, 255, 255)))
        label_font = QFont('Arial', font_size, QFont.Weight.Bold)
        painter.setFont(label_font)
        
        current_y = y
        line_height = font_size + 2
        
        if self.config['include_pokedex_info']:
            pokemon_text = f"#{card_data['pokemon_id']:03d} {card_data['pokemon_name']}"
            painter.drawText(x, current_y, width, line_height, 
                           Qt.AlignmentFlag.AlignCenter, pokemon_text)
            current_y += line_height
        
        if self.config['include_set_label'] and card_data['set_name']:
            set_font = QFont('Arial', max(6, font_size - 2))
            painter.setFont(set_font)
            painter.setPen(QPen(QColor(52, 152, 219)))  # Blue for set
            
            set_text = card_data['set_name']
            if len(set_text) > 20:
                set_text = set_text[:17] + "..."
            
            painter.drawText(x, current_y, width, line_height, 
                           Qt.AlignmentFlag.AlignCenter, set_text)
            current_y += line_height - 2
        
        if self.config['include_artist_label'] and card_data['artist']:
            artist_font = QFont('Arial', max(6, font_size - 2))
            painter.setFont(artist_font)
            painter.setPen(QPen(QColor(149, 165, 166)))  # Gray for artist
            
            artist_text = f"Art: {card_data['artist']}"
            if len(artist_text) > 25:
                artist_text = artist_text[:22] + "..."
            
            painter.drawText(x, current_y, width, line_height, 
                           Qt.AlignmentFlag.AlignCenter, artist_text)


class EnhancedAnalyticsTab(QWidget):
    """Enhanced analytics tab with new export functionality"""
    
    def __init__(self, db_manager, parent_window):
        super().__init__()
        self.db_manager = db_manager
        self.parent_window = parent_window
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Collection statistics
        stats_group = QGroupBox("Collection Statistics")
        stats_layout = QVBoxLayout()
        
        self.collection_stats_label = QLabel()
        self.collection_stats_label.setStyleSheet("color: white; font-size: 12px;")
        stats_layout.addWidget(self.collection_stats_label)
        
        refresh_stats_btn = QPushButton("Refresh Statistics")
        refresh_stats_btn.clicked.connect(self.update_collection_stats)
        stats_layout.addWidget(refresh_stats_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Data quality metrics
        quality_group = QGroupBox("Data Quality")
        quality_layout = QVBoxLayout()
        
        self.data_quality_label = QLabel()
        self.data_quality_label.setStyleSheet("color: white; font-size: 12px;")
        quality_layout.addWidget(self.data_quality_label)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # Export & Backup section
        export_group = QGroupBox("Export & Backup")
        export_layout = QVBoxLayout()
        
        # Enhanced export collection button
        export_collection_btn = QPushButton("Export Collection as PNG")
        export_collection_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        export_collection_btn.clicked.connect(self.export_collection_image)
        export_layout.addWidget(export_collection_btn)
        
        # Legacy JSON export (smaller button)
        export_json_btn = QPushButton("Export as JSON (Legacy)")
        export_json_btn.setStyleSheet("font-size: 11px; padding: 6px;")
        export_json_btn.clicked.connect(self.export_collection_json)
        export_layout.addWidget(export_json_btn)
        
        backup_db_btn = QPushButton("Backup Database")
        export_json_btn.setStyleSheet("font-size: 11px; padding: 6px;")
        backup_db_btn.clicked.connect(self.backup_database)
        export_layout.addWidget(backup_db_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        # Update initial stats
        self.update_collection_stats()
        self.update_data_quality_stats()
    
    def export_collection_image(self):
        """Export collection as high-quality image"""
        # Check if user has any cards
        collection_info = self.get_collection_info()
        if collection_info['total_cards'] == 0:
            QMessageBox.information(self, "No Collection", 
                "You don't have any cards in your collection yet.\n"
                "Import some cards first!")
            return
        
        # Open export options dialog
        options_dialog = CollectionExportOptionsDialog(self.db_manager, self)
        if options_dialog.exec() == QDialog.DialogCode.Accepted:
            export_config = options_dialog.get_export_config()
            
            # Show progress dialog
            progress_dialog = QProgressDialog("Preparing export...", "Cancel", 0, 100, self)
            progress_dialog.setWindowTitle("Exporting Collection")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()
            
            # Create and start generator thread
            self.generator_thread = CollectionImageGenerator(self.db_manager, export_config)
            self.generator_thread.progress_updated.connect(progress_dialog.setValue)
            self.generator_thread.progress_updated.connect(
                lambda value, message: progress_dialog.setLabelText(message)
            )
            self.generator_thread.generation_complete.connect(
                lambda file_path: self.on_export_complete(file_path, progress_dialog)
            )
            self.generator_thread.generation_error.connect(
                lambda error: self.on_export_error(error, progress_dialog)
            )
            
            # Handle cancel
            progress_dialog.canceled.connect(self.generator_thread.terminate)
            
            # Start generation
            self.generator_thread.start()
    
    def on_export_complete(self, file_path, progress_dialog):
        """Handle successful export completion"""
        progress_dialog.hide()
        
        # Show success message with option to open file
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Export Complete")
        msg_box.setText(f"Collection exported successfully!")
        msg_box.setInformativeText(f"Saved to: {file_path}")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        
        result = msg_box.exec()
        if result == QMessageBox.StandardButton.Open:
            # Open file in default image viewer
            import subprocess
            import sys
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path])
                else:
                    subprocess.run(["xdg-open", file_path])
            except Exception as e:
                QMessageBox.warning(self, "Cannot Open File", 
                    f"Export successful but cannot open file: {str(e)}")
    
    def on_export_error(self, error_message, progress_dialog):
        """Handle export error"""
        progress_dialog.hide()
        QMessageBox.critical(self, "Export Failed", 
            f"Failed to export collection:\n{error_message}")
    
    def get_collection_info(self):
        """Get basic collection information"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total_cards,
                   COUNT(DISTINCT p.generation) as generations
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_cards': result[0] if result else 0,
            'generations': result[1] if result else 0
        }
    
    def export_collection_json(self):
        """Legacy JSON export functionality"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection (JSON)", "my_pokemon_collection.json", 
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                collection = self.db_manager.get_user_collection()
                
                with open(file_path, 'w') as f:
                    json.dump(collection, f, indent=2)
                
                QMessageBox.information(self, "Export Complete", 
                    f"Collection exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")
    
    def backup_database(self):
        """Create a backup of the database"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", 
            f"pokedextop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", 
            "Database files (*.db)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.db_manager.db_path, file_path)
                QMessageBox.information(self, "Backup Complete", 
                    f"Database backed up to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")
    
    def update_collection_stats(self):
        """Update detailed collection statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Collection completion by generation
        cursor.execute("""
            SELECT g.generation, g.name, 
                   COUNT(p.pokemon_id) as total_pokemon,
                   COUNT(uc.pokemon_id) as imported_pokemon
            FROM gold_pokemon_generations g
            LEFT JOIN silver_pokemon_master p ON g.generation = p.generation
            LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
            GROUP BY g.generation, g.name
            ORDER BY g.generation
        """)
        
        gen_stats = cursor.fetchall()
        
        # Build stats text
        stats_text = "Collection Completion by Generation:\n\n"
        total_pokemon = 0
        total_imported = 0
        
        for gen_num, gen_name, pokemon_count, imported_count in gen_stats:
            if pokemon_count > 0:
                completion_rate = (imported_count / pokemon_count) * 100
                stats_text += f"{gen_name}: {imported_count}/{pokemon_count} ({completion_rate:.1f}%)\n"
                total_pokemon += pokemon_count
                total_imported += imported_count
        
        if total_pokemon > 0:
            overall_completion = (total_imported / total_pokemon) * 100
            stats_text += f"\nOverall: {total_imported}/{total_pokemon} ({overall_completion:.1f}%)"
        
        self.collection_stats_label.setText(stats_text)
        conn.close()
    
    def update_data_quality_stats(self):
        """Update data quality metrics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Data freshness
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN datetime(data_pull_timestamp) > datetime('now', '-7 days') THEN 1 END) as recent_records
            FROM bronze_tcg_cards
        """)
        
        result = cursor.fetchone()
        total_records, recent_records = result if result else (0, 0)
        
        # Missing images
        cursor.execute("""
            SELECT COUNT(*) FROM silver_tcg_cards 
            WHERE image_url_large IS NULL OR image_url_small IS NULL
        """)
        
        missing_images_result = cursor.fetchone()
        missing_images = missing_images_result[0] if missing_images_result else 0
        
        quality_text = f"Data Quality Metrics:\n\n"
        quality_text += f"Total Records: {total_records}\n"
        quality_text += f"Recent (7 days): {recent_records}\n"
        quality_text += f"Missing Images: {missing_images}\n"
        
        if total_records > 0:
            freshness_rate = (recent_records / total_records) * 100
            quality_text += f"Data Freshness: {freshness_rate:.1f}%"
        
        self.data_quality_label.setText(quality_text)
        conn.close()
        
# =============================================================================
# BROWSE TAB ARCHITECTURE 
# =============================================================================

class SessionCartManager:
    """Manages the import cart during the current session"""
    
    def __init__(self):
        self.cart_items = {}  # card_id -> card_data
        self.item_added_callback = None
        self.item_removed_callback = None
    
    def add_card(self, card_id, card_data):
        """Add a card to the cart"""
        if card_id not in self.cart_items:
            self.cart_items[card_id] = card_data
            if self.item_added_callback:
                self.item_added_callback(card_id, card_data)
            return True
        return False  # Already in cart
    
    def remove_card(self, card_id):
        """Remove a card from the cart"""
        if card_id in self.cart_items:
            card_data = self.cart_items.pop(card_id)
            if self.item_removed_callback:
                self.item_removed_callback(card_id, card_data)
            return True
        return False
    
    def get_cart_items(self):
        """Get all items in cart"""
        return self.cart_items.copy()
    
    def get_cart_count(self):
        """Get number of items in cart"""
        return len(self.cart_items)
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items.clear()
        if self.item_removed_callback:
            self.item_removed_callback(None, None)  # Signal that cart was cleared
    
    def is_in_cart(self, card_id):
        """Check if card is in cart"""
        return card_id in self.cart_items

class ClickableTCGCard(QFrame):
    """Enhanced TCG card widget with double-click functionality"""
    
    cardSelected = pyqtSignal(str, dict)  # card_id, card_data
    
    def __init__(self, card_data, image_loader=None, cart_manager=None):
        super().__init__()
        self.card_data = card_data
        self.image_loader = image_loader
        self.cart_manager = cart_manager
        self.is_selected = False
        self.initUI()
    
    def initUI(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedSize(270, 410)
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 6px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
                background-color: #3d5a75;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Card image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(310)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Load image
        if self.card_data.get('image_url_large'):
            self.image_loader.load_image(
                self.card_data['image_url_large'], 
                self.image_label, 
                (250, 310)
            )
        elif self.card_data.get('image_url_small'):
            self.image_loader.load_image(
                self.card_data['image_url_small'], 
                self.image_label, 
                (250, 310)
            )
        else:
            self.image_label.setText("No Image")
        
        # Card info
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Card name
        name_label = QLabel(self.card_data.get('name', 'Unknown'))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(45)
        info_layout.addWidget(name_label)
        
        # Set info
        set_label = QLabel(f"📦 {self.card_data.get('set_name', 'Unknown Set')}")
        set_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label.setStyleSheet("color: #3498db; font-size: 10px; font-weight: bold;")
        set_label.setWordWrap(True)
        info_layout.addWidget(set_label)
        
        layout.addWidget(info_container)
        
        # Add to cart indicator
        self.cart_indicator = QLabel("Double-click to add to cart")
        self.cart_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cart_indicator.setStyleSheet("""
            color: #7f8c8d; 
            font-size: 10px; 
            background-color: #2c3e50;
            padding: 2px;
            border-radius: 2px;
        """)
        layout.addWidget(self.cart_indicator)
        
        # Update cart indicator if already in cart
        if self.cart_manager and self.cart_manager.is_in_cart(self.card_data['card_id']):
            self.update_cart_indicator(True)
    
    def update_cart_indicator(self, in_cart):
        """Update the cart indicator"""
        if in_cart:
            self.cart_indicator.setText("✓ In Cart")
            self.cart_indicator.setStyleSheet("""
                color: #27ae60; 
                font-size: 10px; 
                background-color: #2c3e50;
                padding: 2px;
                border-radius: 2px;
                font-weight: bold;
            """)
        else:
            self.cart_indicator.setText("Not Added")
            self.cart_indicator.setStyleSheet("""
                color: #7f8c8d; 
                font-size: 10px; 
                background-color: #2c3e50;
                padding: 2px;
                border-radius: 2px;
            """)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to add to cart"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.add_to_cart()
    
    def add_to_cart(self):
        """Add this card to the cart"""
        if self.cart_manager:
            success = self.cart_manager.add_card(self.card_data['card_id'], self.card_data)
            if success:
                self.update_cart_indicator(True)
                self.cardSelected.emit(self.card_data['card_id'], self.card_data)
            else:
                # Card already in cart - maybe show a brief message
                self.cart_indicator.setText("Already in cart!")
                QTimer.singleShot(1500, lambda: self.update_cart_indicator(True))

class CartItemWidget(QFrame):
    """Widget for individual items in the cart"""
    
    removeRequested = pyqtSignal(str)
    
    def __init__(self, card_data, image_loader):
        super().__init__()
        self.card_data = card_data
        self.image_loader = image_loader
        self.initUI()
    
    def initUI(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedHeight(130)
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 4px;
                margin: 2px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Card image (same as before)
        self.image_label = QLabel()
        self.image_label.setFixedSize(85, 105)
        self.image_label.setScaledContents(False)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 4px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Load image (same as before)
        if self.card_data.get('image_url_large'):
            self.image_loader.load_image(
                self.card_data['image_url_large'], 
                self.image_label, 
                (75, 95)
            )
        elif self.card_data.get('image_url_small'):
            self.image_loader.load_image(
                self.card_data['image_url_small'], 
                self.image_label, 
                (75, 95)
            )
        else:
            self.image_label.setText("No\nImage")
        
        # Card info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Card name
        name_label = QLabel(self.card_data.get('name', 'Unknown'))
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent; border: none;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        #Card number
        # num_label = QLabel(self.card_data.get('number', 'Unknown'))
        # num_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        # num_label.setStyleSheet("color: white;")
        # num_label.setWordWrap(True)
        # info_layout.addWidget(name_label)
        
        # Set name
        set_label = QLabel(self.card_data.get('set_name', 'Unknown Set'))
        set_label.setStyleSheet("color: #3498db; font-size: 10px; background: transparent; border: none;")
        set_label.setWordWrap(True)
        info_layout.addWidget(set_label)
        
        # Artist (if available)
        if self.card_data.get('artist'):
            artist_label = QLabel(f"{self.card_data['artist']}")
            artist_label.setStyleSheet("color: white; font-size: 8px; background: transparent; border: none;")
            info_layout.addWidget(artist_label)
        
        # Clickable QLabel with Material icon
        self.remove_label = QLabel()
        
        # Try to load Material Design delete icon
        icon_path = "assets/icons/delete.png"
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            # Tint the icon red
            scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
            self.remove_label.setPixmap(scaled_pixmap)
        else:
            # Fallback to emoji
            self.remove_label.setText("🗑️")
        
        self.remove_label.setFixedSize(95, 25)
        self.remove_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remove_label.setStyleSheet("""
            QLabel {
                background-color: #a93226;
                border-radius: 10px;
                margin-top: 4px;
            }
            QLabel:hover {
                background-color: #c0392b;
            }
        """)
        self.remove_label.setToolTip("Remove from cart")
        self.remove_label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Make it clickable
        self.remove_label.mousePressEvent = self.on_remove_clicked
        
        # Add the remove label under the artist info
        info_layout.addWidget(self.remove_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
    
    def on_remove_clicked(self, event):
        """Handle remove label click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.removeRequested.emit(self.card_data['card_id'])

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
    
# =============================================================================
# BRONZE-SILVER-GOLD DATA ARCHITECTURE
# =============================================================================

class DatabaseManager:
    """
    Implements Bronze-Silver-Gold data architecture:
    
    BRONZE (Raw): Direct API responses stored as-is
    SILVER (Processed): Cleaned and normalized data 
    GOLD (Master): Business-ready data for applications
    """
    
    def __init__(self, db_path="data/databases/pokedextop.db"):
        self.db_path = db_path
        # Only create directory for file-based databases, not in-memory
        if db_path != ":memory:" and not db_path.startswith(":"):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
        self.configure_database_for_concurrency()
        
    def load_pokemon_master_data(self):
        """Load the complete Pokémon list from JSON file"""
        master_file = os.path.join(os.path.dirname(__file__), 'data', 'pokemon_master_data.json')
        
        if not os.path.exists(master_file):
            print(f"WARNING: Pokemon master data file not found at {master_file}")
            return []
        
        with open(master_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['pokemon']
        
    def initialize_complete_pokedex(self):
        """Pre-populate database with all 1025 Pokémon"""
        pokemon_list = self.load_pokemon_master_data()
        
        if not pokemon_list:
            print("ERROR: No Pokemon master data loaded")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for pokemon in pokemon_list:
            cursor.execute("""
                INSERT OR IGNORE INTO silver_pokemon_master 
                (pokemon_id, name, generation, pokedex_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                pokemon['id'], 
                pokemon['name'], 
                pokemon['generation'], 
                json.dumps([pokemon['id']])
            ))
        
        conn.commit()
        conn.close()
        print(f"✓ Pre-populated database with {len(pokemon_list)} Pokémon")

    def init_database(self):
        """Create Bronze-Silver-Gold data tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # =============================================================================
        # BRONZE LAYER - Raw API Data (Immutable Historical Record)
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                api_endpoint TEXT,
                UNIQUE(card_id, data_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                UNIQUE(set_id, data_hash)
            )
        """)
        
        # =============================================================================
        # SILVER LAYER - Processed & Cleaned Data
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_pokemon_master (
                pokemon_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                generation INTEGER,
                pokedex_numbers TEXT,  -- JSON array of national pokedex numbers
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_ids TEXT  -- JSON array of bronze record IDs
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_cards (
                card_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pokemon_name TEXT,
                set_id TEXT NOT NULL,
                set_name TEXT,
                artist TEXT,
                rarity TEXT,
                supertype TEXT,
                subtypes TEXT,  -- JSON array
                types TEXT,     -- JSON array  
                hp TEXT,
                number TEXT,
                image_url_small TEXT,
                image_url_large TEXT,
                national_pokedex_numbers TEXT,  -- JSON array
                legalities TEXT,  -- JSON object
                market_prices TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_cards(id)
            )
        """)
        
        # Add team-up card mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_team_up_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                pokemon_name TEXT NOT NULL,
                position INTEGER DEFAULT 0,  -- position in team (0 = first, 1 = second, etc.)
                FOREIGN KEY (card_id) REFERENCES silver_tcg_cards(card_id),
                UNIQUE(card_id, pokemon_name)
            )
        """)
        
        # Enhanced silver_tcg_sets table with display name and search terms
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_sets (
                set_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,  -- User-friendly display name
                search_terms TEXT,  -- JSON array of searchable terms
                series TEXT,
                printed_total INTEGER,
                total INTEGER,
                release_date TEXT,
                symbol_url TEXT,
                logo_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_sets(id)
            )
        """)

        # Check if we need to add the new columns to existing tables
        cursor.execute("PRAGMA table_info(silver_tcg_sets)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'display_name' not in columns:
            cursor.execute("ALTER TABLE silver_tcg_sets ADD COLUMN display_name TEXT")

        if 'search_terms' not in columns:
            cursor.execute("ALTER TABLE silver_tcg_sets ADD COLUMN search_terms TEXT")
        
        # =============================================================================
        # GOLD LAYER - Business-Ready Application Data
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_user_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                pokemon_id INTEGER,
                card_id TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collection_type TEXT DEFAULT 'personal',  -- personal, wishlist, favorites
                notes TEXT,
                UNIQUE(user_id, pokemon_id, collection_type),
                FOREIGN KEY (pokemon_id) REFERENCES silver_pokemon_master(pokemon_id),
                FOREIGN KEY (card_id) REFERENCES silver_tcg_cards(card_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_pokemon_generations (
                generation INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                start_id INTEGER,
                end_id INTEGER,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # =============================================================================
        # S3 INTEGRATION LAYER - Image Management
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s3_image_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL UNIQUE,
                s3_bucket TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                s3_url TEXT NOT NULL,
                image_type TEXT,  -- 'sprite', 'card_small', 'card_large'
                entity_id TEXT,   -- pokemon_id or card_id
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                content_hash TEXT
            )
        """)
        
        # Performance indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bronze_cards_timestamp ON bronze_tcg_cards(data_pull_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_cards_pokemon ON silver_tcg_cards(pokemon_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_cards_set ON silver_tcg_cards(set_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_sets_display_name ON silver_tcg_sets(display_name)")  # New index for set search functionality Issue 33
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_silver_sets_series ON silver_tcg_sets(series)")  # New index for set search functionality Issue 33
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gold_collections_user ON gold_user_collections(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_s3_cache_entity ON s3_image_cache(entity_id, image_type)")
        
        # Initialize generation data
        self.initialize_generations(cursor)
        
        conn.commit()
        conn.close()
        self.initialize_complete_pokedex()  # Add this line
    
    def initialize_generations(self, cursor):
        """Initialize Pokemon generation data"""
        generations = [
            (1, "Generation I (Kanto)", 1, 151, "Kanto"),
            (2, "Generation II (Johto)", 152, 251, "Johto"),
            (3, "Generation III (Hoenn)", 252, 386, "Hoenn"),
            (4, "Generation IV (Sinnoh)", 387, 493, "Sinnoh"),
            (5, "Generation V (Unova)", 494, 649, "Unova"),
            (6, "Generation VI (Kalos)", 650, 721, "Kalos"),
            (7, "Generation VII (Alola)", 722, 809, "Alola"),
            (8, "Generation VIII (Galar)", 810, 905, "Galar"),
            (9, "Generation IX (Paldea)", 906, 1025, "Paldea")
        ]
        
        for gen_data in generations:
            cursor.execute("""
                INSERT OR IGNORE INTO gold_pokemon_generations 
                (generation, name, start_id, end_id, region)
                VALUES (?, ?, ?, ?, ?)
            """, gen_data)
            
    def configure_database_for_concurrency(self):
        """Configure database for better concurrency handling"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Set busy timeout
            conn.execute("PRAGMA busy_timeout=30000")
            # Optimize for faster writes
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.commit()
        finally:
            conn.close()
    
    # =============================================================================
    # BRONZE LAYER OPERATIONS - Raw Data Storage
    # =============================================================================
    
    def store_bronze_card_data(self, card_data, api_endpoint="cards"):
        """Store raw card data in Bronze layer with deduplication"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            card_id = card_data.get('id')
            raw_json = json.dumps(card_data, sort_keys=True)
            content_hash = hashlib.sha256(raw_json.encode()).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT INTO bronze_tcg_cards 
                    (card_id, raw_json, data_hash, api_endpoint)
                    VALUES (?, ?, ?, ?)
                """, (card_id, raw_json, content_hash, api_endpoint))
                
                bronze_id = cursor.lastrowid
                conn.commit()
                
                # Process to Silver layer
                self.process_bronze_to_silver_card(bronze_id, card_data)
                print(f"✓ Stored new card data: {card_id}")
                return bronze_id
                
            except sqlite3.IntegrityError:
                cursor.execute("""
                    SELECT id FROM bronze_tcg_cards 
                    WHERE card_id = ? AND data_hash = ?
                """, (card_id, content_hash))
                result = cursor.fetchone()
                existing_id = result[0] if result else None
                print(f"⚡ Duplicate card data found: {card_id}")
                return existing_id
                
        except Exception as e:
            print(f"Database error storing card {card_data.get('id', 'unknown')}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def store_bronze_set_data(self, set_data):
        """Store raw set data in Bronze layer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_id = set_data.get('id')
        raw_json = json.dumps(set_data, sort_keys=True)
        content_hash = hashlib.sha256(raw_json.encode()).hexdigest()
        
        try:
            cursor.execute("""
                INSERT INTO bronze_tcg_sets 
                (set_id, raw_json, data_hash)
                VALUES (?, ?, ?)
            """, (set_id, raw_json, content_hash))
            
            bronze_id = cursor.lastrowid
            conn.commit()
            
            # Process to Silver layer
            self.process_bronze_to_silver_set(bronze_id, set_data)
            return bronze_id
            
        except sqlite3.IntegrityError:
            cursor.execute("""
                SELECT id FROM bronze_tcg_sets 
                WHERE set_id = ? AND data_hash = ?
            """, (set_id, content_hash))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    # =============================================================================
    # SILVER LAYER OPERATIONS - Processed Data
    # =============================================================================
    
    def process_bronze_to_silver_card(self, bronze_id, card_data):
        """Process Bronze card data to Silver layer (cleaned/normalized)"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
            cursor = conn.cursor()
            
            # Extract and clean card data
            card_id = card_data.get('id')
            name = card_data.get('name', '')
            pokemon_names = self.extract_pokemon_name_from_card(name)
            
            # Handle team-up cards (pokemon_names will be a list)
            primary_pokemon_name = None
            is_team_up = False
            
            if isinstance(pokemon_names, list):
                # Team-up card
                is_team_up = True
                primary_pokemon_name = pokemon_names[0] if pokemon_names else None
                all_pokemon_names = pokemon_names
            else:
                # Single Pokemon card
                primary_pokemon_name = pokemon_names
                all_pokemon_names = [pokemon_names] if pokemon_names else []
            
            # Handle nested data safely
            set_data = card_data.get('set', {})
            images = card_data.get('images', {})
            legalities = card_data.get('legalities', {})
            tcgplayer = card_data.get('tcgplayer', {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_tcg_cards 
                (card_id, name, pokemon_name, set_id, set_name, artist, rarity, 
                supertype, subtypes, types, hp, number, 
                image_url_small, image_url_large, national_pokedex_numbers,
                legalities, market_prices, source_bronze_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                name,
                primary_pokemon_name,
                set_data.get('id'),
                set_data.get('name'),
                card_data.get('artist'),
                card_data.get('rarity'),
                card_data.get('supertype'),
                json.dumps(card_data.get('subtypes', [])),
                json.dumps(card_data.get('types', [])),
                card_data.get('hp'),
                card_data.get('number'),
                images.get('small'),
                images.get('large'),
                json.dumps(card_data.get('nationalPokedexNumbers', [])),
                json.dumps(legalities),
                json.dumps(tcgplayer.get('prices', {})),
                bronze_id
            ))
            
            # Handle team-up card mapping
            if is_team_up:
                # First, clear any existing team-up mappings for this card
                cursor.execute("DELETE FROM silver_team_up_cards WHERE card_id = ?", (card_id,))
                
                # Insert team-up mappings
                for position, pokemon_name in enumerate(all_pokemon_names):
                    if pokemon_name:
                        cursor.execute("""
                            INSERT INTO silver_team_up_cards (card_id, pokemon_name, position)
                            VALUES (?, ?, ?)
                        """, (card_id, pokemon_name, position))
            
            # Update Pokemon master records
            pokedex_numbers = card_data.get('nationalPokedexNumbers', [])
            if pokedex_numbers:
                if is_team_up and len(all_pokemon_names) > 1:
                    # For team-ups, we need to be smarter about assigning pokedex numbers
                    # If we have multiple pokedex numbers, try to match them to Pokemon
                    for pokemon_name in all_pokemon_names:
                        if pokemon_name:
                            # For now, use all pokedex numbers for each Pokemon
                            # In a more sophisticated system, we'd match specific numbers to specific Pokemon
                            self.update_silver_pokemon_master_with_connection(
                                cursor, pokemon_name, pokedex_numbers
                            )
                else:
                    # Single Pokemon card
                    if primary_pokemon_name:
                        self.update_silver_pokemon_master_with_connection(
                            cursor, primary_pokemon_name, pokedex_numbers
                        )
            
            conn.commit()
            
        except Exception as e:
            print(f"Error processing card to silver layer: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_silver_pokemon_master_with_connection(self, cursor, pokemon_name, pokedex_numbers):
        """Update Pokemon master using existing connection"""
        try:
            # Calculate generation from first pokedex number
            primary_number = pokedex_numbers[0] if pokedex_numbers else None
            generation = self.calculate_generation(primary_number) if primary_number else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_pokemon_master 
                (pokemon_id, name, generation, pokedex_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                primary_number,
                pokemon_name,
                generation,
                json.dumps(pokedex_numbers)
            ))
            
        except Exception as e:
            print(f"Error updating Pokemon master: {e}")
            raise
                
    def process_bronze_to_silver_set(self, bronze_id, set_data):
        """Process Bronze set data to Silver layer with enhanced display name and search terms"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract and clean set data
            set_id = set_data.get('id')
            name = set_data.get('name', '')
            series = set_data.get('series', '')
            printed_total = set_data.get('printedTotal', 0)
            total = set_data.get('total', 0)
            release_date = set_data.get('releaseDate', '')
            
            # Handle nested data safely
            images = set_data.get('images', {})
            
            # Generate display name and search terms
            display_name = self.generate_set_display_name(set_id, name, series)
            search_terms = self.generate_set_search_terms(set_id, name, series)
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_tcg_sets 
                (set_id, name, display_name, search_terms, series, printed_total, total, 
                release_date, symbol_url, logo_url, source_bronze_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                set_id,
                name,
                display_name,
                json.dumps(search_terms),
                series,
                printed_total,
                total,
                release_date,
                images.get('symbol'),
                images.get('logo'),
                bronze_id
            ))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error processing set to silver layer: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                
    def generate_set_display_name(self, set_id, name, series):
        """Generate user-friendly display name for a set"""
        # Create a more readable display name
        if series and name:
            display_name = f"{series}: {name}"
        else:
            display_name = name
        
        # Add set code in parentheses for clarity
        if set_id:
            display_name += f" ({set_id})"
        
        return display_name

    def generate_set_search_terms(self, set_id, name, series):
        """Generate searchable terms for a set"""
        terms = []
        
        # Add the set ID
        if set_id:
            terms.append(set_id.lower())
        
        # Add the full name
        if name:
            terms.append(name.lower())
            # Add individual words from the name
            words = name.split()
            terms.extend([word.lower() for word in words if len(word) > 2])
        
        # Add the series
        if series:
            terms.append(series.lower())
            # Add series abbreviations
            if series == "Sword & Shield":
                terms.extend(["swsh", "sword shield", "ss"])
            elif series == "Sun & Moon":
                terms.extend(["sm", "sun moon"])
            elif series == "XY":
                terms.extend(["xy", "x y", "x&y"])
            elif series == "Black & White":
                terms.extend(["bw", "black white"])
            elif series == "Diamond & Pearl":
                terms.extend(["dp", "diamond pearl"])
            elif series == "Scarlet & Violet":
                terms.extend(["sv", "scarlet violet"])
        
        # Add common variations
        if "Base Set" in name:
            terms.extend(["base", "base set", "original"])
        if "Crown Zenith" in name:
            terms.extend(["crown", "zenith", "cz"])
        if "Hidden Fates" in name:
            terms.extend(["hidden", "fates", "hf"])
        if "Shining Fates" in name:
            terms.extend(["shining", "fates", "sf"])
        
        # Remove duplicates
        return list(set(terms))
    
    def search_sets(self, search_term):
        """Search for sets using fuzzy matching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_term_lower = search_term.lower()
        
        # First, try exact matches
        cursor.execute("""
            SELECT set_id, name, display_name, series, total, release_date, symbol_url
            FROM silver_tcg_sets
            WHERE LOWER(set_id) = ? OR LOWER(name) = ?
            ORDER BY release_date DESC
        """, (search_term_lower, search_term_lower))
        
        exact_matches = cursor.fetchall()
        
        # Then, search in search terms
        cursor.execute("""
            SELECT set_id, name, display_name, series, total, release_date, symbol_url, search_terms
            FROM silver_tcg_sets
        """)
        
        all_sets = cursor.fetchall()
        conn.close()
    
        # Fuzzy match against search terms
        fuzzy_matches = []
        for set_data in all_sets:
            set_id, name, display_name, series, total, release_date, symbol_url, search_terms_json = set_data
            
            # Skip if already in exact matches
            if any(set_id == match[0] for match in exact_matches):
                continue
            
            # Check search terms
            search_terms = json.loads(search_terms_json) if search_terms_json else []
            
            # Calculate match score
            max_score = 0
            for term in search_terms:
                # Check if search term is contained in any searchable term
                if search_term_lower in term:
                    max_score = max(max_score, 0.8)
                else:
                    # Use fuzzy matching
                    score = SequenceMatcher(None, search_term_lower, term).ratio()
                    max_score = max(max_score, score)
            
            # Also check against display name
            if display_name:
                display_name_lower = display_name.lower()
                if search_term_lower in display_name_lower:
                    max_score = max(max_score, 0.9)
                else:
                    score = SequenceMatcher(None, search_term_lower, display_name_lower).ratio()
                    max_score = max(max_score, score)
            
            if max_score > 0.5:  # Threshold for fuzzy matching
                fuzzy_matches.append((set_data[:7], max_score))
        
        # Sort fuzzy matches by score
        fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Combine results
        results = []
        
        # Add exact matches first
        for match in exact_matches:
            results.append({
                'set_id': match[0],
                'name': match[1],
                'display_name': match[2],
                'series': match[3],
                'total': match[4],
                'release_date': match[5],
                'symbol_url': match[6],
                'match_score': 1.0
            })
        
        # Add fuzzy matches
        for match_data, score in fuzzy_matches[:10]:  # Limit to top 10 fuzzy matches
            results.append({
                'set_id': match_data[0],
                'name': match_data[1],
                'display_name': match_data[2],
                'series': match_data[3],
                'total': match_data[4],
                'release_date': match_data[5],
                'symbol_url': match_data[6],
                'match_score': score
            })
        
        return results

    def get_all_sets_grouped_by_series(self):
        """Get all sets grouped by series"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT set_id, name, display_name, series, total, release_date, symbol_url
            FROM silver_tcg_sets
            ORDER BY series, release_date DESC
        """)
        
        sets = cursor.fetchall()
        conn.close()
        
        # Group by series
        grouped = {}
        for set_data in sets:
            series = set_data[3] or "Other"
            if series not in grouped:
                grouped[series] = []
            
            grouped[series].append({
                'set_id': set_data[0],
                'name': set_data[1],
                'display_name': set_data[2],
                'series': set_data[3],
                'total': set_data[4],
                'release_date': set_data[5],
                'symbol_url': set_data[6]
            })
        
        return grouped

    def get_set_autocomplete_suggestions(self, prefix):
        """Get autocomplete suggestions for set search"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        prefix_lower = prefix.lower()
        
        # Search for sets that start with the prefix
        cursor.execute("""
            SELECT DISTINCT display_name, set_id
            FROM silver_tcg_sets
            WHERE LOWER(display_name) LIKE ? OR LOWER(set_id) LIKE ?
            ORDER BY release_date DESC
            LIMIT 20
        """, (f"{prefix_lower}%", f"{prefix_lower}%"))
        
        suggestions = []
        for row in cursor.fetchall():
            suggestions.append(row[0])  # Use display name for suggestions
        
        conn.close()
        return suggestions
    
    def extract_pokemon_name_from_card(self, card_name):
        """Extract Pokemon name from card name using improved logic"""
        import re
        
        if not card_name:
            return None
        
        # First, check for team-up cards (& symbol indicates multiple Pokemon)
        if ' & ' in card_name:
            # Extract all Pokemon names from team-up cards
            # Remove any suffixes first
            clean_team_name = re.sub(r'\s+(?:GX|TAG TEAM|LEGEND).*$', '', card_name)
            # Split by & and clean each name
            pokemon_names = []
            for name in clean_team_name.split(' & '):
                cleaned = self._clean_single_pokemon_name(name.strip())
                if cleaned:
                    pokemon_names.append(cleaned)
            return pokemon_names  # Return list for team-ups
        
        # For single Pokemon, use existing logic
        return self._clean_single_pokemon_name(card_name)
    
    def _clean_single_pokemon_name(self, card_name):
        """Clean a single Pokemon name"""
        import re
        
        if not card_name:
            return None
        
        # Remove card prefixes
        clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
        
        # Remove trainer possessives (e.g., "Team Rocket's", "Brock's", "Misty's")
        # This handles any possessive form ending with 's
        clean_name = re.sub(r"^[A-Za-z\s]+\'s\s+", '', clean_name)
        clean_name = re.sub(r"^Team\s+[A-Za-z\s]+\'s\s+", '', clean_name)
        
        # Handle special cases
        special_cases = {
            "Mr. Mime": "Mr. Mime",
            "Mime Jr.": "Mime Jr.",
            "Farfetch'd": "Farfetch'd",
            "Sirfetch'd": "Sirfetch'd",
            "Type: Null": "Type: Null",
            "Ho-Oh": "Ho-Oh",
            "Porygon-Z": "Porygon-Z",
            "Jangmo-o": "Jangmo-o",
            "Hakamo-o": "Hakamo-o",
            "Kommo-o": "Kommo-o"
        }
        
        for special_name, replacement in special_cases.items():
            if special_name in clean_name:
                return replacement
        
        # Remove regional prefixes but keep the base name
        regional_prefixes = ["Alolan", "Galarian", "Paldean", "Hisuian"]
        for region in regional_prefixes:
            if clean_name.startswith(f"{region} "):
                clean_name = clean_name.replace(f"{region} ", "", 1)
                break
        
        # Remove card suffixes
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|Prime|BREAK|Prism Star|◇|LV\.X|MEGA|M|Tag Team).*$', '', clean_name)
        
        # Remove any remaining special characters
        clean_name = re.sub(r'[◇★]', '', clean_name)
        
        return clean_name.strip()
    
    def update_silver_pokemon_master(self, pokemon_name, pokedex_numbers):
        """Update or create Pokemon master record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate generation from first pokedex number
        primary_number = pokedex_numbers[0] if pokedex_numbers else None
        generation = self.calculate_generation(primary_number) if primary_number else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO silver_pokemon_master 
            (pokemon_id, name, generation, pokedex_numbers)
            VALUES (?, ?, ?, ?)
        """, (
            primary_number,
            pokemon_name,
            generation,
            json.dumps(pokedex_numbers)
        ))
        
        conn.commit()
        conn.close()
    
    def calculate_generation(self, pokedex_number):
        """Calculate generation from pokedex number"""
        if not pokedex_number:
            return None
            
        generation_ranges = [
            (1, 151, 1), (152, 251, 2), (252, 386, 3), (387, 493, 4), (494, 649, 5),
            (650, 721, 6), (722, 809, 7), (810, 905, 8), (906, 1025, 9)
        ]
        
        for start, end, gen in generation_ranges:
            if start <= pokedex_number <= end:
                return gen
        return 9  # Default to latest
    
    # =============================================================================
    # GOLD LAYER OPERATIONS - Business Logic
    # =============================================================================
    
    def get_pokemon_by_generation(self, generation):
        """Get ALL Pokémon for a generation with card availability"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # This query now returns ALL Pokémon, even those without cards
        cursor.execute("""
            SELECT 
                p.pokemon_id, 
                p.name, 
                p.pokedex_numbers,
                COUNT(DISTINCT c.card_id) as card_count,
                GROUP_CONCAT(DISTINCT c.card_id) as available_cards
            FROM silver_pokemon_master p
            LEFT JOIN (
                SELECT card_id, pokemon_name FROM silver_tcg_cards
                UNION
                SELECT t.card_id, t.pokemon_name FROM silver_team_up_cards t
            ) c ON p.name = c.pokemon_name
            WHERE p.generation = ?
            GROUP BY p.pokemon_id, p.name
            ORDER BY p.pokemon_id
        """, (generation,))
        
        results = cursor.fetchall()
        conn.close()
        
        pokemon_dict = {}
        for row in results:
            pokemon_dict[str(row[0])] = {
                'id': row[0],
                'name': row[1],
                'generation': generation,
                'pokedex_numbers': json.loads(row[2]) if row[2] else [],
                'card_count': row[3],  # Will be 0 if no cards exist
                'available_cards': row[4].split(',') if row[4] else []
            }
        
        return pokemon_dict
    
    def get_user_collection(self, user_id='default'):
        """Get user's collection from Gold layer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT uc.pokemon_id, uc.card_id, c.name, c.image_url_large, c.set_name
            FROM gold_user_collections uc
            JOIN silver_tcg_cards c ON uc.card_id = c.card_id
            WHERE uc.user_id = ? AND uc.collection_type = 'personal'
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        collection = {}
        for row in results:
            collection[str(row[0])] = {
                'card_id': row[1],
                'card_name': row[2],
                'image_url': row[3],
                'set_name': row[4]
            }
        
        return collection
    
    def add_to_user_collection(self, user_id, pokemon_id, card_id):
        """Add card to user's collection (Gold layer)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO gold_user_collections 
            (user_id, pokemon_id, card_id, collection_type)
            VALUES (?, ?, ?, 'personal')
        """, (user_id, pokemon_id, card_id))
        
        conn.commit()
        conn.close()

# =============================================================================
# IMAGE LOADER
# =============================================================================

class ImageLoader(QObject):
    """Image loader with game sprite support"""
    
    imageLoaded = pyqtSignal(QPixmap)
    
    def __init__(self):
        super().__init__()
        self._network_manager = QNetworkAccessManager()
        self._loading_images = {}
        self._image_cache = {}
    
    def load_image(self, url, label, size=None):
        """Load image with sprite-aware styling"""
        if not url:
            label.setText("No Image")
            return
        
        # Check cache first
        if url in self._image_cache:
            self._set_image_on_label(label, self._image_cache[url], size)
            self._apply_post_load_styling(label, url)
            return
        
        # Create request
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, 
                           QNetworkRequest.CacheLoadControl.PreferCache)
        
        reply = self._network_manager.get(request)
        
        # Store the reply with its associated data
        self._loading_images[reply] = (label, size, url)
        
        # Connect signals
        reply.finished.connect(lambda: self._on_image_loaded(reply))
        reply.errorOccurred.connect(lambda: self._on_image_error(reply))
    
    def _on_image_loaded(self, reply):
        """Handle successful image loading"""
        if reply not in self._loading_images:
            reply.deleteLater()
            return
        
        label, size, url = self._loading_images.pop(reply)
        
        # Check if the label still exists
        try:
            if sip.isdeleted(label):
                reply.deleteLater()
                return
        except:
            try:
                _ = label.objectName()
            except RuntimeError:
                reply.deleteLater()
                return
        
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            
            if pixmap.loadFromData(data):
                # Cache the pixmap
                self._image_cache[url] = pixmap
                
                try:
                    self._set_image_on_label(label, pixmap, size)
                    self._apply_post_load_styling(label, url)
                except RuntimeError:
                    pass
            else:
                try:
                    self._show_sprite_error(label)
                except RuntimeError:
                    pass
        else:
            self._on_image_error(reply)
        
        reply.deleteLater()
    
    def _on_image_error(self, reply):
        """Handle image loading errors"""
        if reply in self._loading_images:
            label, _, url = self._loading_images.pop(reply)
            
            try:
                if not sip.isdeleted(label):
                    self._show_sprite_error(label)
            except:
                try:
                    self._show_sprite_error(label)
                except RuntimeError:
                    pass
                    
        reply.deleteLater()
    
    def _apply_post_load_styling(self, label, url):
        """Apply appropriate styling after image loads"""
        try:
            if "pokemon/" in url and "official-artwork" not in url:
                # Game sprite styling
                label.setStyleSheet("""
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                    border-radius: 6px; 
                    border: 2px solid #4a90e2;
                    padding: 8px;
                """)
            else:
                # TCG card - keep clean dark styling, no changes
                label.setStyleSheet("""
                    background-color: #2c3e50; 
                    border-radius: 6px;
                """)
        except RuntimeError:
            pass
    
    def _show_sprite_error(self, label):
        """Show error state for failed sprite loading"""
        try:
            label.setText("No Sprite\nAvailable")
            label.setStyleSheet("""
                background-color: #f8f9fa; 
                border-radius: 6px; 
                color: #6c757d;
                font-size: 10px;
                border: 2px dashed #dee2e6;
                padding: 15px;
            """)
        except RuntimeError:
            pass
    
    def _set_image_on_label(self, label, pixmap, size):
        """Set pixmap on label with optional scaling"""
        try:
            if sip.isdeleted(label):
                return
        except:
            pass
            
        try:
            if size:
                scaled_pixmap = pixmap.scaled(size[0], size[1], 
                                             Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(scaled_pixmap)
            else:
                label_size = label.size()
                scaled_pixmap = pixmap.scaled(label_size, 
                                             Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(scaled_pixmap)
        except RuntimeError:
            pass
    
    def cancel_all_requests(self):
        """Cancel all pending image requests"""
        for reply in list(self._loading_images.keys()):
            reply.abort()
            reply.deleteLater()
        self._loading_images.clear()
        
# =============================================================================
# TCG API CLIENT - Pokemon TCG SDK Integration
# =============================================================================

class TCGAPIClient:
    """Pokemon TCG API client using the official SDK"""
    
    def __init__(self, db_manager, api_key=None):
        self.db_manager = db_manager
        
        # Configure API key for higher rate limits
        if api_key:
            RestClient.configure(api_key)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def search_cards_by_pokemon_name(self, pokemon_name):
        """Search cards by Pokemon name"""
        try:
            self._rate_limit()
            
            # Search for cards containing the Pokemon name
            query = f'name:"{pokemon_name}"'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                try:
                    # Convert card object to dict for storage
                    card_data = self._card_to_dict(card)
                    bronze_id = self.db_manager.store_bronze_card_data(card_data)
                    stored_cards.append(card_data)
                except Exception as store_error:
                    print(f"Warning: Failed to store card {card.id}: {store_error}")
                    # Still add the card data even if storage fails
                    card_data = self._card_to_dict(card)
                    stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error searching for {pokemon_name}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error searching for {pokemon_name}: {e}")
            return []
    
    def search_cards_by_pokedex_number(self, pokedex_number):
        """Search cards by National Pokedex number"""
        try:
            self._rate_limit()
            
            query = f'nationalPokedexNumbers:{pokedex_number}'
            cards = Card.where(q=query)
            
            stored_cards = []
            for card in cards:
                card_data = self._card_to_dict(card)
                self.db_manager.store_bronze_card_data(card_data)
                stored_cards.append(card_data)
            
            return stored_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error for Pokedex #{pokedex_number}: {e}")
            return []
    
    def get_all_sets(self):
        """Fetch all TCG sets"""
        try:
            self._rate_limit()
            
            sets = Set.all()
            stored_sets = []
            
            for tcg_set in sets:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
                stored_sets.append(set_data)
            
            return stored_sets
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching sets: {e}")
            return []
    
    def get_cards_from_set(self, set_id, page_size=250):
        """Get all cards from a specific set"""
        try:
            page = 1
            all_cards = []
            
            # First, get and store the set information
            self._rate_limit()
            tcg_set = Set.find(set_id)
            if tcg_set:
                set_data = self._set_to_dict(tcg_set)
                self.db_manager.store_bronze_set_data(set_data)
            
            # Then get all cards from the set
            while True:
                self._rate_limit()
                
                query = f'set.id:{set_id}'
                cards = Card.where(q=query, page=page, pageSize=page_size)
                
                if not cards:
                    break
                
                for card in cards:
                    card_data = self._card_to_dict(card)
                    self.db_manager.store_bronze_card_data(card_data)
                    all_cards.append(card_data)
                
                page += 1
                
                # Safety break for large sets
                if page > 20:
                    break
            
            return all_cards
            
        except PokemonTcgException as e:
            print(f"TCG API Error fetching set {set_id}: {e}")
            return []
    
    def _card_to_dict(self, card):
        """Convert Card object to dictionary for storage"""
        return {
            'id': card.id,
            'name': card.name,
            'supertype': card.supertype,
            'subtypes': card.subtypes or [],
            'types': card.types or [],
            'hp': card.hp,
            'evolvesFrom': card.evolvesFrom,
            'attacks': [self._attack_to_dict(attack) for attack in (card.attacks or [])],
            'weaknesses': [self._weakness_to_dict(w) for w in (card.weaknesses or [])],
            'resistances': [self._resistance_to_dict(r) for r in (card.resistances or [])],
            'retreatCost': card.retreatCost or [],
            'convertedRetreatCost': card.convertedRetreatCost,
            'set': self._set_to_dict(card.set),
            'number': card.number,
            'artist': card.artist,
            'rarity': card.rarity,
            'flavorText': card.flavorText,
            'nationalPokedexNumbers': card.nationalPokedexNumbers or [],
            'legalities': self._legalities_to_dict(card.legalities),
            'images': {
                'small': card.images.small,
                'large': card.images.large
            } if card.images else {},
            'tcgplayer': self._tcgplayer_to_dict(card.tcgplayer) if card.tcgplayer else {}
        }
    
    def _set_to_dict(self, tcg_set):
        """Convert Set object to dictionary"""
        return {
            'id': tcg_set.id,
            'name': tcg_set.name,
            'series': tcg_set.series,
            'printedTotal': tcg_set.printedTotal,
            'total': tcg_set.total,
            'legalities': self._legalities_to_dict(tcg_set.legalities),
            'ptcgoCode': tcg_set.ptcgoCode,
            'releaseDate': tcg_set.releaseDate,
            'updatedAt': tcg_set.updatedAt,
            'images': {
                'symbol': tcg_set.images.symbol,
                'logo': tcg_set.images.logo
            } if tcg_set.images else {}
        }
    
    def _attack_to_dict(self, attack):
        """Convert Attack object to dictionary"""
        return {
            'name': attack.name,
            'cost': attack.cost or [],
            'convertedEnergyCost': attack.convertedEnergyCost,
            'damage': attack.damage,
            'text': attack.text
        }
    
    def _weakness_to_dict(self, weakness):
        """Convert Weakness object to dictionary"""
        return {
            'type': weakness.type,
            'value': weakness.value
        }
    
    def _resistance_to_dict(self, resistance):
        """Convert Resistance object to dictionary"""
        return {
            'type': resistance.type,
            'value': resistance.value
        }
    
    def _legalities_to_dict(self, legalities):
        """Convert Legalities object to dictionary"""
        if not legalities:
            return {}
        
        return {
            'unlimited': legalities.unlimited,
            'expanded': legalities.expanded,
            'standard': legalities.standard
        }
    
    def _tcgplayer_to_dict(self, tcgplayer):
        """Convert TCGPlayer object to dictionary"""
        return {
            'url': tcgplayer.url,
            'updatedAt': tcgplayer.updatedAt,
            'prices': self._prices_to_dict(tcgplayer.prices) if tcgplayer.prices else {}
        }
    
    def _prices_to_dict(self, prices):
        """Convert TCGPrices object to dictionary"""
        result = {}
        
        if prices.normal:
            result['normal'] = self._price_to_dict(prices.normal)
        if prices.holofoil:
            result['holofoil'] = self._price_to_dict(prices.holofoil)
        if prices.reverseHolofoil:
            result['reverseHolofoil'] = self._price_to_dict(prices.reverseHolofoil)
        if prices.firstEditionNormal:
            result['firstEditionNormal'] = self._price_to_dict(prices.firstEditionNormal)
        if prices.firstEditionHolofoil:
            result['firstEditionHolofoil'] = self._price_to_dict(prices.firstEditionHolofoil)
        
        return result
    
    def _price_to_dict(self, price):
        """Convert TCGPrice object to dictionary"""
        return {
            'low': price.low,
            'mid': price.mid,
            'high': price.high,
            'market': price.market,
            'directLow': price.directLow
        }

# =============================================================================
# UI COMPONENTS - Updated for Bronze-Silver-Gold Architecture
# =============================================================================
class SetBrowseDialog(QDialog):
    """Dialog for browsing and discovering TCG sets"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_set_id = None
        self.setWindowTitle("Browse TCG Sets")
        self.setMinimumSize(800, 600)
        self.initUI()

    def update_set_autocomplete(self):
        """Update autocomplete suggestions based on current input"""
        current_text = self.search_input.text()
        
        if len(current_text) >= 2:  # Only search after 2 characters
            suggestions = self.db_manager.get_set_autocomplete_suggestions(current_text)
            
            # Update completer model
            model = QStringListModel(suggestions)
            self.set_completer.setModel(model)
            
            # Update preview if we have matches
            if suggestions:
                self.set_preview_label.setText(f"Found {len(suggestions)} matching sets")
                self.set_preview_label.setStyleSheet("color: #3498db; font-size: 11px; padding: 5px;")
            else:
                self.set_preview_label.setText("No matching sets found. Try browsing all sets.")
                self.set_preview_label.setStyleSheet("color: #e74c3c; font-size: 11px; padding: 5px;")
        else:
            self.set_preview_label.setText("")

    def browse_sets(self):
        """Open set browse dialog"""
        dialog = SetBrowseDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_set_id = dialog.get_selected_set()
            if selected_set_id:
                self.sync_set_by_id(selected_set_id)

    def sync_searched_set(self):
        """Sync set based on search input"""
        search_term = self.set_search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Input Error", "Please enter a set name or ID")
            return
        
        # Search for matching sets
        matches = self.db_manager.search_sets(search_term)
        
        if not matches:
            QMessageBox.warning(self, "No Match", 
                f"No sets found matching '{search_term}'.\n"
                "Try browsing all sets or sync more data.")
            return
        
        if len(matches) == 1:
            # Single match - sync directly
            self.sync_set_by_id(matches[0]['set_id'])
        else:
            # Multiple matches - show selection dialog
            self.show_set_selection_dialog(matches)

    def show_set_selection_dialog(self, matches):
        """Show dialog to select from multiple matching sets"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Set to Sync")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel(f"Found {len(matches)} matching sets. Select one:")
        layout.addWidget(label)
        
        # List widget for sets
        list_widget = QListWidget()
        for match in matches[:10]:  # Limit to 10 results
            item_text = f"{match['display_name']} - {match['total']} cards"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, match['set_id'])
            list_widget.addItem(item)
        
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        sync_btn = QPushButton("Sync Selected")
        sync_btn.clicked.connect(lambda: self.sync_selected_from_list(list_widget, dialog))
        button_layout.addWidget(sync_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def sync_selected_from_list(self, list_widget, dialog):
        """Sync the selected set from list"""
        current_item = list_widget.currentItem()
        if current_item:
            set_id = current_item.data(Qt.ItemDataRole.UserRole)
            dialog.accept()
            self.sync_set_by_id(set_id)

    def sync_popular_set(self, index):
        """Sync a popular set from combo box"""
        set_id = self.popular_sets_combo.currentData()
        if set_id:
            self.sync_set_by_id(set_id)
            # Reset combo box
            self.popular_sets_combo.setCurrentIndex(0)

    def sync_set_by_id(self, set_id):
        """Sync a specific set by its ID"""
        self.disable_buttons()
        self.progress_label.setText(f"Syncing set {set_id}...")
        self.log_output.append(f"📦 Syncing set: {set_id}")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            cards = self.tcg_client.get_cards_from_set(set_id)
            
            if cards:
                self.log_output.append(f"✓ Set {set_id}: {len(cards)} cards synced")
                self.progress_label.setText(f"Set {set_id} complete! {len(cards)} cards synced")
                
                # Clear search input on success
                self.set_search_input.clear()
            else:
                self.log_output.append(f"⚠ No cards found for set {set_id}")
                self.progress_label.setText(f"No cards found for set {set_id}")
                
        except Exception as e:
            self.log_output.append(f"❌ Set sync failed: {str(e)}")
            self.progress_label.setText("Set sync failed")
        
        self.enable_buttons()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search sets...")
        self.search_input.textChanged.connect(self.filter_sets)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Sets table
        self.sets_table = QTableWidget()
        self.sets_table.setColumnCount(5)
        self.sets_table.setHorizontalHeaderLabels(["Set Name", "Series", "Cards", "Release Date", "ID"])
        self.sets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sets_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sets_table.itemSelectionChanged.connect(self.on_set_selected)
        
        # Style the table
        self.sets_table.setStyleSheet("""
            QTableWidget {
                background-color: #2c3e50;
                color: white;
                gridline-color: #34495e;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        
        # Adjust column widths
        header = self.sets_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.sets_table)
        
        # Set preview
        preview_group = QGroupBox("Set Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Select a set to see details")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select Set")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self.accept)
        button_layout.addWidget(self.select_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Load sets
        self.load_all_sets()
    
    def load_all_sets(self):
        """Load all sets grouped by series"""
        self.sets_table.setRowCount(0)
        
        grouped_sets = self.db_manager.get_all_sets_grouped_by_series()
        
        # Sort series
        series_order = ["Scarlet & Violet", "Sword & Shield", "Sun & Moon", "XY", 
                       "Black & White", "Diamond & Pearl", "Platinum", "HeartGold & SoulSilver",
                       "EX", "Base", "Other"]
        
        sorted_series = []
        for series in series_order:
            if series in grouped_sets:
                sorted_series.append(series)
        
        # Add any remaining series
        for series in grouped_sets:
            if series not in sorted_series:
                sorted_series.append(series)
        
        # Populate table
        for series in sorted_series:
            if series in grouped_sets:
                for set_info in grouped_sets[series]:
                    self.add_set_to_table(set_info)
    
    def add_set_to_table(self, set_info):
        """Add a set to the table"""
        row = self.sets_table.rowCount()
        self.sets_table.insertRow(row)
        
        # Set Name
        name_item = QTableWidgetItem(set_info['display_name'] or set_info['name'])
        self.sets_table.setItem(row, 0, name_item)
        
        # Series
        series_item = QTableWidgetItem(set_info['series'] or "Unknown")
        self.sets_table.setItem(row, 1, series_item)
        
        # Card Count
        card_count = set_info['total'] or 0
        count_item = QTableWidgetItem(str(card_count))
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sets_table.setItem(row, 2, count_item)
        
        # Release Date
        release_date = set_info['release_date'] or "Unknown"
        date_item = QTableWidgetItem(release_date)
        self.sets_table.setItem(row, 3, date_item)
        
        # Set ID
        id_item = QTableWidgetItem(set_info['set_id'])
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sets_table.setItem(row, 4, id_item)
        
        # Store full set info in the first item
        name_item.setData(Qt.ItemDataRole.UserRole, set_info)
    
    def filter_sets(self, text):
        """Filter sets based on search text"""
        search_text = text.lower()
        
        for row in range(self.sets_table.rowCount()):
            show_row = False
            
            # Check all columns
            for col in range(self.sets_table.columnCount()):
                item = self.sets_table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
            
            self.sets_table.setRowHidden(row, not show_row)
    
    def on_set_selected(self):
        """Handle set selection"""
        selected_items = self.sets_table.selectedItems()
        
        if selected_items:
            # Get the set info from the first column
            row = selected_items[0].row()
            name_item = self.sets_table.item(row, 0)
            set_info = name_item.data(Qt.ItemDataRole.UserRole)
            
            if set_info:
                self.selected_set_id = set_info['set_id']
                self.select_button.setEnabled(True)
                
                # Update preview
                preview_text = f"<b>{set_info['display_name'] or set_info['name']}</b><br>"
                preview_text += f"Series: {set_info['series'] or 'Unknown'}<br>"
                preview_text += f"Cards: {set_info['total'] or 0}<br>"
                preview_text += f"Release: {set_info['release_date'] or 'Unknown'}<br>"
                preview_text += f"Set ID: {set_info['set_id']}"
                
                self.preview_label.setText(preview_text)
                self.preview_label.setStyleSheet("color: white; padding: 10px;")
    
    def get_selected_set(self):
        """Get the selected set ID"""
        return self.selected_set_id


class DataSyncDialog(QDialog):
    """Advanced data sync dialog for TCG data"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.tcg_client = TCGAPIClient(db_manager)
        self.setWindowTitle("Sync Pokemon TCG Data")
        self.setMinimumWidth(500)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Sync options
        sync_section = QGroupBox("Sync Options")
        sync_layout = QVBoxLayout()
        
        # Generation sync
        gen_layout = QHBoxLayout()
        gen_layout.addWidget(QLabel("Generation:"))
        
        self.gen_combo = QComboBox()
        generations = [
            ("All Generations", "all"),
            ("Generation 1 (Kanto)", 1),
            ("Generation 2 (Johto)", 2),
            ("Generation 3 (Hoenn)", 3),
            ("Generation 4 (Sinnoh)", 4),
            ("Generation 5 (Unova)", 5),
            ("Generation 6 (Kalos)", 6),
            ("Generation 7 (Alola)", 7),
            ("Generation 8 (Galar)", 8),
            ("Generation 9 (Paldea)", 9)
        ]
        
        for gen_name, gen_value in generations:
            self.gen_combo.addItem(gen_name, gen_value)
        
        gen_layout.addWidget(self.gen_combo)
        
        self.gen_sync_btn = QPushButton("Sync Generation")
        self.gen_sync_btn.clicked.connect(self.sync_generation)
        gen_layout.addWidget(self.gen_sync_btn)
        
        sync_layout.addLayout(gen_layout)
        
        # Set sync - Dropdown style like Generation sync
        set_layout = QHBoxLayout()
        set_layout.addWidget(QLabel("TCG Set:"))
        
        self.set_combo = QComboBox()
        self.set_combo.setMinimumWidth(300)
        self.set_combo.addItem("Select a Set", None)
        
        # DON'T LOAD SETS HERE - REMOVE THIS LINE
        # self.load_sets_dropdown()
        
        set_layout.addWidget(self.set_combo)
        
        self.set_sync_btn = QPushButton("Sync Set")
        self.set_sync_btn.clicked.connect(self.sync_selected_set)
        set_layout.addWidget(self.set_sync_btn)
        
        sync_layout.addLayout(set_layout)
        
        # API Key section
        api_section = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()
        
        api_info = QLabel("Enter your Pokemon TCG API key for higher rate limits (optional):")
        api_layout.addWidget(api_info)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API Key (optional)")
        api_layout.addWidget(self.api_key_input)
        
        api_section.setLayout(api_layout)
        layout.addWidget(api_section)
        
        # Bulk operations
        bulk_layout = QHBoxLayout()
        self.sync_all_sets_btn = QPushButton("Sync All Sets")
        self.sync_all_sets_btn.clicked.connect(self.sync_all_sets)
        bulk_layout.addWidget(self.sync_all_sets_btn)
        
        self.reset_database_btn = QPushButton("Reset Database")
        self.reset_database_btn.clicked.connect(self.reset_database)
        self.reset_database_btn.setStyleSheet("background-color: #e74c3c;")
        bulk_layout.addWidget(self.reset_database_btn)
        
        sync_layout.addLayout(bulk_layout)
        
        sync_section.setLayout(sync_layout)
        layout.addWidget(sync_section)
        
        # Progress section
        progress_section = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to sync...")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setPlaceholderText("Sync logs will appear here...")
        progress_layout.addWidget(self.log_output)
        
        progress_section.setLayout(progress_layout)
        layout.addWidget(progress_section)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # NOW LOAD SETS - AT THE VERY END AFTER ALL WIDGETS ARE CREATED
        self.load_sets_dropdown()
    
    def load_sets_dropdown(self):
        """Load ALL available sets from API into the dropdown"""
        # Clear existing items except the first one
        while self.set_combo.count() > 1:
            self.set_combo.removeItem(1)
        
        # Try to get all sets from API first
        try:
            self.log_output.append("📋 Loading available sets...")
            
            # Configure API key if provided
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            # Get all sets from API
            all_sets = self.tcg_client.get_all_sets()
            
            if all_sets:
                # Group by series
                grouped = {}
                for set_data in all_sets:
                    series = set_data.get('series', 'Other')
                    if series not in grouped:
                        grouped[series] = []
                    grouped[series].append(set_data)
                
                # Sort series
                series_order = ["Scarlet & Violet", "Sword & Shield", "Sun & Moon", "XY", 
                            "Black & White", "Diamond & Pearl", "Platinum", "HeartGold & SoulSilver",
                            "EX", "Base", "Other"]
                
                sorted_series = []
                for series in series_order:
                    if series in grouped:
                        sorted_series.append(series)
                
                # Add any remaining series
                for series in grouped:
                    if series not in sorted_series:
                        sorted_series.append(series)
                
                # Populate combo box
                for series in sorted_series:
                    if series in grouped:
                        # Add series as a separator/header
                        self.set_combo.addItem(f"──── {series} ────", None)
                        index = self.set_combo.count() - 1
                        self.set_combo.model().item(index).setEnabled(False)
                        
                        # Add sets in this series
                        for set_info in grouped[series]:
                            set_id = set_info.get('id')
                            name = set_info.get('name')
                            total = set_info.get('total', 0)
                            
                            display_text = f"{name} ({set_id})"
                            if total:
                                display_text += f" - {total} cards"
                            
                            self.set_combo.addItem(display_text, set_id)
                
                self.log_output.append(f"✓ Loaded {len(all_sets)} available sets")
            else:
                self.log_output.append("⚠ No sets available from API")
                
        except Exception as e:
            self.log_output.append(f"❌ Failed to load sets: {str(e)}")
            # Fall back to loading from database
            self.load_sets_from_database()
            
    def load_sets_from_database(self):
        """Fallback to load sets from database if API fails"""
        # Get sets that have already been synced to the database
        grouped_sets = self.db_manager.get_all_sets_grouped_by_series()
        
        if grouped_sets:
            # Sort series in a logical order
            series_order = ["Scarlet & Violet", "Sword & Shield", "Sun & Moon", "XY", 
                        "Black & White", "Diamond & Pearl", "Platinum", "HeartGold & SoulSilver",
                        "EX", "Base", "Other"]
            
            sorted_series = []
            for series in series_order:
                if series in grouped_sets:
                    sorted_series.append(series)
            
            # Add any remaining series
            for series in grouped_sets:
                if series not in sorted_series:
                    sorted_series.append(series)
            
            # Populate combo box with synced sets
            for series in sorted_series:
                if series in grouped_sets:
                    # Add series as a separator/header
                    self.set_combo.addItem(f"──── {series} (Synced) ────", None)
                    index = self.set_combo.count() - 1
                    self.set_combo.model().item(index).setEnabled(False)
                    
                    # Add sets in this series
                    for set_info in grouped_sets[series]:
                        display_text = set_info['display_name'] or f"{set_info['name']} ({set_info['set_id']})"
                        if set_info['total']:
                            display_text += f" - {set_info['total']} cards"
                        
                        self.set_combo.addItem(display_text, set_info['set_id'])
            
            self.set_combo.addItem("──── Not Synced Yet ────", None)
            index = self.set_combo.count() - 1
            self.set_combo.model().item(index).setEnabled(False)
            self.set_combo.addItem("⚠️ Could not load from API - showing synced sets only", None)
        else:
            self.set_combo.addItem("No sets available - sync some sets first", None)
    
    def filter_set_dropdown(self, text):
        """Filter the dropdown based on search text"""
        search_text = text.lower()
        
        # For now, just reload the dropdown
        # A more sophisticated implementation would filter in place
        if not search_text:
            self.load_sets_dropdown()
    
    def sync_selected_set(self):
        """Sync the selected set from dropdown"""
        set_id = self.set_combo.currentData()
        
        if not set_id:
            QMessageBox.warning(self, "No Selection", "Please select a set to sync")
            return
        
        self.sync_set_by_id(set_id)
    
    def sync_set_by_id(self, set_id):
        """Sync a specific set by its ID"""
        self.disable_buttons()
        self.progress_label.setText(f"Syncing set {set_id}...")
        self.log_output.append(f"📦 Syncing set: {set_id}")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            cards = self.tcg_client.get_cards_from_set(set_id)
            
            if cards:
                self.log_output.append(f"✓ Set {set_id}: {len(cards)} cards synced")
                self.progress_label.setText(f"Set {set_id} complete! {len(cards)} cards synced")
                
                # Reset combo to first item
                self.set_combo.setCurrentIndex(0)
            else:
                self.log_output.append(f"⚠ No cards found for set {set_id}")
                self.progress_label.setText(f"No cards found for set {set_id}")
                
        except Exception as e:
            self.log_output.append(f"❌ Set sync failed: {str(e)}")
            self.progress_label.setText("Set sync failed")
        
        self.enable_buttons()
    
    def search_pokemon_cards(self):
        """Search for cards by Pokemon name"""
        pokemon_name = self.pokemon_input.text().strip()
        if not pokemon_name:
            QMessageBox.warning(self, "Input Error", "Please enter a Pokemon name")
            return
        
        self.disable_buttons()
        self.progress_label.setText(f"Searching cards for {pokemon_name}...")
        self.log_output.append(f"🔍 Searching for {pokemon_name} cards...")
        
        try:
            # Configure API key if provided
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
                self.log_output.append("✓ API key configured")
            
            # Search for cards
            cards = self.tcg_client.search_cards_by_pokemon_name(pokemon_name)
            
            if cards:
                self.log_output.append(f"✓ Found {len(cards)} cards for {pokemon_name}")
                self.progress_label.setText(f"Found {len(cards)} cards for {pokemon_name}")
            else:
                self.log_output.append(f"⚠ No cards found for {pokemon_name}")
                self.progress_label.setText(f"No cards found for {pokemon_name}")
                
        except Exception as e:
            self.log_output.append(f"❌ Error: {str(e)}")
            self.progress_label.setText("Search failed")
        
        self.enable_buttons()
    
    def sync_generation(self):
        """Sync all Pokemon cards for a generation"""
        generation = self.gen_combo.currentData()
        
        if generation == "all":
            self.sync_all_generations()
            return
        
        # Call the internal sync method directly
        self._sync_generation_internal(generation)

    def _sync_generation_internal(self, generation):
        """Internal method to sync a specific generation without UI dependencies"""
        self.disable_buttons()
        
        # Get generation range
        gen_ranges = {
            1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493), 5: (494, 649),
            6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025)
        }
        
        start_id, end_id = gen_ranges.get(generation, (1, 151))
        
        self.progress_bar.setRange(0, end_id - start_id + 1)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Syncing Generation {generation}...")
        self.log_output.append(f"🔄 Starting Generation {generation} sync (#{start_id}-#{end_id})")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            success_count = 0
            error_count = 0
            
            for pokedex_num in range(start_id, end_id + 1):
                try:
                    cards = self.tcg_client.search_cards_by_pokedex_number(pokedex_num)
                    if cards:
                        success_count += len(cards)
                        self.log_output.append(f"✓ #{pokedex_num}: {len(cards)} cards")
                    else:
                        self.log_output.append(f"○ #{pokedex_num}: no cards found")
                    
                    self.progress_bar.setValue(pokedex_num - start_id + 1)
                    QApplication.processEvents()
                    
                    # Add a small delay to prevent database locking
                    import time
                    time.sleep(0.1)  # 100ms delay between Pokemon
                    
                except Exception as e:
                    error_count += 1
                    self.log_output.append(f"❌ #{pokedex_num}: {str(e)}")
                    
                    # If too many errors, pause briefly
                    if error_count > 5:
                        self.log_output.append("⏸️ Too many errors, pausing for 2 seconds...")
                        import time
                        time.sleep(2)
                        error_count = 0
            
            self.progress_label.setText(f"Generation {generation} sync complete! {success_count} cards synced")
            self.log_output.append(f"✅ Generation {generation} complete: {success_count} total cards")
            
        except Exception as e:
            self.log_output.append(f"❌ Generation sync failed: {str(e)}")
            self.progress_label.setText("Generation sync failed")
        
        self.enable_buttons()

    def sync_all_generations(self):
        """Sync all generations sequentially - FIXED VERSION"""
        reply = QMessageBox.question(self, "Confirm", 
            "This will sync TCG cards for EVERY pokemon and may take a very long time. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.disable_buttons()
        self.log_output.append("🚀 Starting full database sync (all generations)")
        
        try:
            # Configure API key once
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            total_cards_synced = 0
            
            # Sync each generation directly without touching the UI combo box
            for gen in range(1, 10):
                self.log_output.append(f"📖 Starting Generation {gen}...")
                
                # Call internal method directly to avoid recursion
                gen_ranges = {
                    1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493), 5: (494, 649),
                    6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025)
                }
                
                start_id, end_id = gen_ranges.get(gen, (1, 151))
                
                self.progress_bar.setRange(0, end_id - start_id + 1)
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Syncing Generation {gen}...")
                
                gen_success_count = 0
                gen_error_count = 0
                
                for pokedex_num in range(start_id, end_id + 1):
                    try:
                        cards = self.tcg_client.search_cards_by_pokedex_number(pokedex_num)
                        if cards:
                            gen_success_count += len(cards)
                            total_cards_synced += len(cards)
                            if len(cards) > 0:  # Only log if cards found
                                self.log_output.append(f"✓ Gen {gen} #{pokedex_num}: {len(cards)} cards")
                        
                        self.progress_bar.setValue(pokedex_num - start_id + 1)
                        QApplication.processEvents()
                        
                        # Small delay to prevent overwhelming the API/database
                        import time
                        time.sleep(0.1)
                        
                    except Exception as e:
                        gen_error_count += 1
                        self.log_output.append(f"❌ Gen {gen} #{pokedex_num}: {str(e)}")
                        
                        # Pause if too many errors
                        if gen_error_count > 10:
                            self.log_output.append("⏸️ Too many errors, pausing for 3 seconds...")
                            import time
                            time.sleep(3)
                            gen_error_count = 0
                
                self.log_output.append(f"✅ Generation {gen} complete: {gen_success_count} cards synced")
                
                # Brief pause between generations
                import time
                time.sleep(0.5)
            
            self.progress_label.setText(f"All generations sync complete! {total_cards_synced} total cards synced")
            self.log_output.append(f"🎉 FULL SYNC COMPLETE: {total_cards_synced} cards from all generations")
            
        except Exception as e:
            self.log_output.append(f"❌ Full generation sync failed: {str(e)}")
            self.progress_label.setText("Full sync failed")
        
        self.enable_buttons()
    
    def sync_all_sets(self):
        """Sync all available TCG sets"""
        reply = QMessageBox.question(self, "Confirm", 
            "This will sync ALL TCG sets and may take a very long time. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.disable_buttons()
        self.log_output.append("🌐 Starting full TCG database sync...")
        
        try:
            api_key = self.api_key_input.text().strip()
            if api_key:
                RestClient.configure(api_key)
            
            # First, get all sets
            sets = self.tcg_client.get_all_sets()
            self.log_output.append(f"📋 Found {len(sets)} sets")
            
            self.progress_bar.setRange(0, len(sets))
            
            total_cards = 0
            for i, tcg_set in enumerate(sets):
                set_id = tcg_set['id']
                self.progress_label.setText(f"Syncing {set_id}...")
                
                cards = self.tcg_client.get_cards_from_set(set_id)
                total_cards += len(cards)
                
                self.log_output.append(f"✓ {set_id}: {len(cards)} cards")
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()
            
            self.progress_label.setText(f"All sets synced! {total_cards} total cards")
            self.log_output.append(f"🎉 Full sync complete: {total_cards} cards from {len(sets)} sets")
            
        except Exception as e:
            self.log_output.append(f"❌ Full sync failed: {str(e)}")
            self.progress_label.setText("Full sync failed")
        
        self.enable_buttons()
    
    def reset_database(self):
        """Reset the entire database"""
        reply = QMessageBox.question(self, "Confirm Reset", 
            "This will DELETE ALL data in the database. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(self.db_manager.db_path)
                self.db_manager.init_database()
                self.log_output.append("🗑️ Database reset complete")
                self.progress_label.setText("Database reset")
                # Reload sets dropdown
                self.load_sets_dropdown()
            except Exception as e:
                self.log_output.append(f"❌ Reset failed: {str(e)}")
    
    def disable_buttons(self):
        self.gen_sync_btn.setEnabled(False)
        self.set_combo.setEnabled(False)
        self.set_sync_btn.setEnabled(False)
        self.sync_all_sets_btn.setEnabled(False)
        self.reset_database_btn.setEnabled(False)
    
    def enable_buttons(self):
        self.gen_sync_btn.setEnabled(True)
        self.set_combo.setEnabled(True)
        self.set_sync_btn.setEnabled(True)
        self.sync_all_sets_btn.setEnabled(True)
        self.reset_database_btn.setEnabled(True)

class PokemonCard(QFrame):
    """Updated Pokemon card widget with enhanced larger image support"""
    
    # Add a signal to notify when a card is imported
    cardImported = pyqtSignal(str, str)  # pokemon_id, card_id
    
    def __init__(self, pokemon_data, user_collection=None, image_loader=None, db_manager=None):
        super().__init__()
        self.pokemon_data = pokemon_data
        self.user_collection = user_collection or {}
        self.image_loader = image_loader or ImageLoader()
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
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
        
        self.setFixedWidth(300)  # Slightly increased from 280
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)  # Increased padding
        layout.setSpacing(8)
        
        # Image container - Enhanced
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(220)  # Increased from 200
        self.image_label.setMaximumHeight(380)  # Increased from 350
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("background-color: #2c3e50; border-radius: 6px;")
        
        # Load the card image
        self.refresh_card_display()
        
        layout.addWidget(self.image_label, 1, Qt.AlignmentFlag.AlignCenter)
        
        # Pokemon info section - Enhanced
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)
        
        # Pokemon name with better styling
        name_label = QLabel(f"#{self.pokemon_data['id']} {self.pokemon_data['name']}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))  # Slightly larger
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
        
        layout.addWidget(info_container)
        
        self.setLayout(layout)
        
        ## Make clickable only if cards are available
        if card_count > 0:
            self.mousePressEvent = self.show_card_selection
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Don't make clickable if no cards exist
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def refresh_card_display(self):
        """Refresh the card display with proper TCG vs sprite loading"""
        pokemon_id = self.pokemon_data['id']
        pokemon_name = self.pokemon_data['name']
        user_card = self.user_collection.get(str(pokemon_id))
        
        if user_card and user_card.get('image_url'):
            # TCG card loading - keep it clean, no loading text
            self.image_label.setText("")  # Clear any text
            self.image_label.setStyleSheet("""
                background-color: #2c3e50; 
                border-radius: 6px;
            """)
            
            # Load TCG card image directly without loading state text
            self.image_loader.load_image(user_card['image_url'], self.image_label, (260, 360))
            
            tooltip_text = f"🃏 TCG Card: {user_card['card_name']}"
            if user_card.get('set_name'):
                tooltip_text += f"\n Set: {user_card['set_name']}"
            tooltip_text += f"\n\n Imported for #{pokemon_id} {pokemon_name}"
            tooltip_text += f"\n Click to change card"
            
            self.image_label.setToolTip(tooltip_text)
            
        else:
            # No TCG cards - load Pokémon game sprite with loading state
            sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
            
            # Set initial loading state ONLY for sprites
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
            self.image_loader.load_image(sprite_url, self.image_label, (120, 120))
            
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
            if self.db_manager:
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
                
                available_cards = [row[0] for row in results]
        
        if not available_cards:
            QMessageBox.information(self, "No Cards", 
                f"No TCG cards found for {pokemon_name}.\n"
                "Use 'Sync Data' to search for cards.")
            return
        
        # Create card selection dialog with image loader and db_manager
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
                # Import the card
                self.import_card(selected_card_id)
    
    def import_card(self, card_id):
        """Import a card for this Pokemon"""
        if not self.db_manager:
            return
        
        pokemon_id = self.pokemon_data['id']
        
        # Add to database
        self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
        
        # Update our local collection data
        self.user_collection[str(pokemon_id)] = self.get_card_details(card_id)
        
        # Refresh the display
        self.refresh_card_display()
        
        # Emit signal for parent to know about the import
        self.cardImported.emit(str(pokemon_id), card_id)
    
    def get_card_details(self, card_id):
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
# Updated CardSelectionDialog to accept pokemon_id and db_manager

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

class PokemonDashboard(QMainWindow):
    """Main dashboard with complete Bronze-Silver-Gold architecture"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Initialize shared image loader
        self.image_loader = ImageLoader()
        
        #Initialize session cart manager
        self.session_cart = SessionCartManager()
        
        # Set up generations (from database)
        self.load_generations()
        
        self.initUI()
    
    def load_generations(self):
        """Load generation data from database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT generation, name FROM gold_pokemon_generations 
            ORDER BY generation
        """)
        
        self.generations = cursor.fetchall()
        conn.close()
    
    
    def initUI(self):        
        self.setWindowTitle('PokéDextop 1.0')
    
        # Get available screen area (excludes taskbar, dock, etc.)
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry()
        available_width = available_geometry.width()
        available_height = available_geometry.height()
        
        print(f"Available screen area: {available_width}x{available_height}")
        print(f"Position: x={available_geometry.x()}, y={available_geometry.y()}")
        
        # Lock to available screen dimensions
        self.setFixedSize(available_width, available_height)
        
        # Position at available area start
        self.move(available_geometry.x(), available_geometry.y())
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #34495e;
                background-color: #2c3e50;
            }
            QTabBar::tab {
                background-color: #34495e;
                color: white;
                padding: 10px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0px 0px;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
            }
            QTabBar::tab:hover {
                background-color: #2980b9;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QGroupBox {
                color: white;
                border: 2px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
            QComboBox {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Add toolbar
        self.create_toolbar(main_layout)
        
        # Create main tab widget
        self.main_tabs = QTabWidget()
        
        # Create My Pokedex tab
        self.create_pokedex_tab()
        
        # Create TCG Browse tab
        self.create_tcg_browse_tab()
        
        # Create Analytics tab
        self.create_analytics_tab()
        
        self.main_tabs.currentChanged.connect(self.on_main_tab_changed)
    
        main_layout.addWidget(self.main_tabs)
    
        main_layout.addWidget(self.main_tabs)
        
        # Status bar
        self.update_status_bar()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_status_bar)
        self.refresh_timer.start(30000)  # Update every 30 seconds
    
    def create_toolbar(self, main_layout):
        """Create application toolbar"""
        toolbar_layout = QHBoxLayout()
        
        # Sync button
        sync_button = QPushButton("🔄 Sync Data")
        sync_button.setToolTip("Sync Pokemon TCG data from API")
        sync_button.clicked.connect(self.open_sync_dialog)
        toolbar_layout.addWidget(sync_button)
        
        # Database stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        toolbar_layout.addWidget(self.stats_label)
        
        main_layout.addLayout(toolbar_layout)
    
    def create_pokedex_tab(self):
        """Create the main Pokedex tab"""
        pokedex_tab = QWidget()
        pokedex_layout = QVBoxLayout(pokedex_tab)
        
        # Create generation tabs
        self.gen_tabs = QTabWidget()
        
        for generation, gen_name in self.generations:
            gen_tab = GenerationTab(gen_name, generation, self.db_manager, self.image_loader)
            self.gen_tabs.addTab(gen_tab, f"Gen {generation}")
        
        pokedex_layout.addWidget(self.gen_tabs)
        self.main_tabs.addTab(pokedex_tab, "📚 My Pokédex")
    
    def create_tcg_browse_tab(self):
        """Replace the existing create_tcg_browse_tab method in PokemonDashboard"""
        
        # Add session cart manager as an instance variable
        if not hasattr(self, 'session_cart'):
            self.session_cart = SessionCartManager()
        
        # Create enhanced browse tab
        enhanced_browse_tab = EnhancedBrowseTCGTab(
            self.db_manager, 
            self.image_loader, 
            self.session_cart
        )
        
        # Replace the existing tab or add as new tab
        self.main_tabs.addTab(enhanced_browse_tab, "🃏 Browse TCG Cards")

    def show_empty_tcg_state(self):
        """Show empty state when no TCG data is available"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        
        empty_label = QLabel("No TCG sets or cards found")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #7f8c8d; font-size: 16px;")
        empty_layout.addWidget(empty_label)
        
        sync_hint = QLabel("Use 'Sync Data' to fetch TCG sets and cards")
        sync_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sync_hint.setStyleSheet("color: #95a5a6; font-size: 12px;")
        empty_layout.addWidget(sync_hint)
        
        self.tcg_scroll.setWidget(empty_widget)
    
    def create_analytics_tab(self):
        """Create analytics and insights tab with enhanced export functionality"""
        # Replace the old analytics tab with the new enhanced version
        enhanced_analytics_tab = EnhancedAnalyticsTab(self.db_manager, self)
        self.main_tabs.addTab(enhanced_analytics_tab, "📊 Analytics")
    
    def load_sets_combo(self):
        """Load available sets into combo box with enhanced display names"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT set_id, display_name, name, series 
            FROM silver_tcg_sets 
            ORDER BY series DESC, release_date DESC
        """)
        
        current_series = None
        for row in cursor.fetchall():
            set_id, display_name, name, series = row
            # Add series separator
            if series != current_series:
                if current_series is not None:
                    self.set_combo.insertSeparator(self.set_combo.count())
                current_series = series
            
            # Use display name if available, otherwise fall back to name
            combo_text = display_name if display_name else f"{name} ({set_id})"
            self.set_combo.addItem(combo_text, set_id)
        
        conn.close()
    
    def load_rarities_combo(self):
        """Load available rarities into combo box"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT rarity FROM silver_tcg_cards 
            WHERE rarity IS NOT NULL
            ORDER BY rarity
        """)
        
        for row in cursor.fetchall():
            self.rarity_combo.addItem(row[0], row[0])
        
        conn.close()
    
    def apply_tcg_filters(self):
        """Apply filters to TCG card display"""
        # Get filter values
        selected_set = self.set_combo.currentData()
        selected_rarity = self.rarity_combo.currentData()
        
        # Build query
        query = "SELECT card_id, name, set_name, rarity, image_url_small FROM silver_tcg_cards WHERE 1=1"
        params = []
        
        if selected_set != "all":
            query += " AND set_id = ?"
            params.append(selected_set)
        
        if selected_rarity != "all":
            query += " AND rarity = ?"
            params.append(selected_rarity)
        
        query += " ORDER BY name LIMIT 200"  # Limit for performance
        
        # Execute query
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        cards = cursor.fetchall()
        conn.close()
        
        # Display cards
        self.display_tcg_cards(cards)
    
    def display_tcg_cards(self, cards):
        """Display TCG cards in grid with improved layout for larger cards"""
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: #2c3e50;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(5)  # Increased spacing for larger cards
        
        columns = 3 # Reduced from 5 to 4 for larger cards
        row, col = 0, 0
        
        for card_data in cards:
            card_widget = self.create_tcg_card_widget(card_data, self.image_loader)
            grid_layout.addWidget(card_widget, row, col, Qt.AlignmentFlag.AlignCenter)
            
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        if not cards:
            # Enhanced empty state
            no_cards_widget = QWidget()
            no_cards_layout = QVBoxLayout(no_cards_widget)
            
            no_cards_label = QLabel("🔍 No cards found with current filters")
            no_cards_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_cards_label.setStyleSheet("color: #7f8c8d; font-size: 16px; margin: 20px;")
            no_cards_layout.addWidget(no_cards_label)
            
            suggestion_label = QLabel("Try adjusting your filters or sync more data")
            suggestion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            suggestion_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
            no_cards_layout.addWidget(suggestion_label)
            
            grid_layout.addWidget(no_cards_widget, 0, 0, 1, columns)
        
        # Add some bottom padding
        grid_layout.setRowStretch(row + 1, 1)
        
        self.tcg_scroll.setWidget(grid_widget)
    
    def create_tcg_card_widget(self, card_data, image_loader=None):
        """Create a larger TCG card display widget for browsing"""
        card_id, name, set_name, rarity, image_url = card_data
        
        if not image_loader:
            image_loader = self.image_loader
        
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        widget.setFixedSize(270, 410)  # Increased from 150x220
        widget.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 2px solid #2c3e50;
                border-radius: 6px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
                background-color: #3d5a75;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Card image - Much larger
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedHeight(310)  # Increased from 120
        image_label.setScaledContents(False)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                border-radius: 6px;
                border: 1px solid #34495e;
            }
        """)
        layout.addWidget(image_label)
        
        # Load image with better quality
        if image_url:
            # Try to use large image first, fallback to small
            image_loader.load_image(image_url, image_label, (300, 320))
        else:
            image_label.setText("No Image\nAvailable")
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #2c3e50; 
                    border-radius: 4px; 
                    color: #7f8c8d;
                    font-size: 10px;
                }
            """)
        
        # Card info section with better layout
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Card name with better typography
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(45)  # Prevent overly tall names
        info_layout.addWidget(name_label)
        
        # Set info
        set_label = QLabel(f"📦 {set_name}")
        set_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label.setStyleSheet("color: #3498db; font-size: 10px; font-weight: bold;")
        set_label.setWordWrap(True)
        set_label.setMaximumHeight(30)
        info_layout.addWidget(set_label)
        
        # Rarity with icon and color
        if rarity:
            rarity_icon = "⭐" if "Rare" in rarity else "◆" if "Uncommon" in rarity else "●"
            rarity_label = QLabel(f"{rarity_icon} {rarity}")
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
            color = rarity_colors.get(rarity, '#f39c12')
            rarity_label.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: bold;")
            info_layout.addWidget(rarity_label)
        
        layout.addWidget(info_container)
        
        # Quick import hint
        hint_label = QLabel("Quick Import")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("""
            color: #7f8c8d; 
            font-size: 10px; 
            background-color: #2c3e50;
            padding: 2px;
            border-radius: 2px;
        """)
        layout.addWidget(hint_label)
        
        # Make clickable for import with better feedback
        widget.card_id = card_id
        widget.mousePressEvent = lambda event: self.quick_import_card(card_id, name)
        
        # Enhanced tooltip
        widget.setToolTip(f"🃏 {name}\n📦 Set: {set_name}\n⭐ {rarity or 'Unknown'}\n\n💾 Click to quick import this card")
        
        return widget
    
    def quick_import_card(self, card_id, card_name):
        """Quick import a card to collection"""
        # Extract Pokemon name and try to import
        pokemon_name = self.extract_pokemon_name(card_name)
        if pokemon_name:
            # Find Pokemon ID
            pokemon_id = self.find_pokemon_id_by_name(pokemon_name)
            if pokemon_id:
                self.db_manager.add_to_user_collection('default', pokemon_id, card_id)
                QMessageBox.information(self, "Import Success", 
                    f"Imported {card_name} for {pokemon_name}!")
                self.refresh_all_tabs()
            else:
                QMessageBox.warning(self, "Import Failed", 
                    f"Could not find Pokemon '{pokemon_name}' in database")
        else:
            QMessageBox.warning(self, "Import Failed", 
                f"Could not determine Pokemon from card name: {card_name}")
    
    def extract_pokemon_name(self, card_name):
        """Extract Pokemon name from card (simplified version)"""
        import re
        
        if not card_name:
            return None
        
        # Check for team-up cards first
        if ' & ' in card_name:
            # For team-ups, extract the first Pokemon name
            clean_team_name = re.sub(r'\s+(?:GX|TAG TEAM|LEGEND).*$', '', card_name)
            first_pokemon = clean_team_name.split(' & ')[0].strip()
            card_name = first_pokemon
        
        # Remove trainer possessives
        card_name = re.sub(r"^[A-Za-z\s]+\'s\s+", '', card_name)
        card_name = re.sub(r"^Team\s+[A-Za-z\s]+\'s\s+", '', card_name)
        
        # Remove prefixes and suffixes
        clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|Prime|BREAK|LV\.X|MEGA|M).*$', '', clean_name)
        
        # Handle possessive forms
        possessive_match = re.match(r"(\w+\'s)\s+(\w+(?:\s+\w+)?)", clean_name)
        if possessive_match:
            return possessive_match.group(2)
        
        return clean_name.strip()
    
    def find_pokemon_id_by_name(self, pokemon_name):
        """Find Pokemon ID by name in database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pokemon_id FROM silver_pokemon_master 
            WHERE LOWER(name) = LOWER(?)
        """, (pokemon_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def perform_search(self):
        """Perform search across Pokemon and cards"""
        search_term = self.search_input.text().strip()
        if not search_term:
            return
        
        # Search in database
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Search Pokemon
        cursor.execute("""
            SELECT pokemon_id, name, generation FROM silver_pokemon_master 
            WHERE name LIKE ? 
            ORDER BY name
        """, (f'%{search_term}%',))
        
        pokemon_results = cursor.fetchall()
        
        # Search cards
        cursor.execute("""
            SELECT card_id, name, set_name FROM silver_tcg_cards 
            WHERE name LIKE ? 
            ORDER BY name 
            LIMIT 20
        """, (f'%{search_term}%',))
        
        card_results = cursor.fetchall()
        conn.close()
        
        # Show results dialog
        self.show_search_results(search_term, pokemon_results, card_results)
    
    def show_search_results(self, search_term, pokemon_results, card_results):
        """Show search results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Search Results: '{search_term}'")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Pokemon results
        if pokemon_results:
            layout.addWidget(QLabel(f"Pokemon ({len(pokemon_results)} found):"))
            pokemon_list = QLabel()
            pokemon_text = "\n".join([f"#{p[0]} {p[1]} (Gen {p[2]})" for p in pokemon_results])
            pokemon_list.setText(pokemon_text)
            pokemon_list.setStyleSheet("color: white; background-color: #34495e; padding: 10px;")
            layout.addWidget(pokemon_list)
        
        # Card results
        if card_results:
            layout.addWidget(QLabel(f"Cards ({len(card_results)} found):"))
            card_list = QLabel()
            card_text = "\n".join([f"{c[1]} ({c[2]})" for c in card_results])
            card_list.setText(card_text)
            card_list.setStyleSheet("color: white; background-color: #34495e; padding: 10px;")
            layout.addWidget(card_list)
        
        if not pokemon_results and not card_results:
            layout.addWidget(QLabel("No results found"))
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def open_sync_dialog(self):
        """Open the data sync dialog"""
        dialog = DataSyncDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_all_tabs()
            self.update_status_bar()
    
    def refresh_all_tabs(self):
        """Refresh all generation tabs"""
        for i in range(self.gen_tabs.count()):
            gen_tab = self.gen_tabs.widget(i)
            if hasattr(gen_tab, 'refresh_data'):
                gen_tab.refresh_data()
    
    def update_status_bar(self):
        """Update the status bar with current statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM silver_pokemon_master")
        pokemon_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM silver_tcg_cards")
        card_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gold_user_collections")
        imported_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT set_id) FROM silver_tcg_sets")
        set_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Update displays
        status_text = f"Pokemon: {pokemon_count} | Cards: {card_count} | Sets: {set_count} | Imported: {imported_count}"
        self.statusBar().showMessage(status_text)
        self.stats_label.setText(status_text)
    
    def update_collection_stats(self):
        """Update detailed collection statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Collection completion by generation
        cursor.execute("""
            SELECT g.generation, g.name, 
                   COUNT(p.pokemon_id) as total_pokemon,
                   COUNT(uc.pokemon_id) as imported_pokemon
            FROM gold_pokemon_generations g
            LEFT JOIN silver_pokemon_master p ON g.generation = p.generation
            LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
            GROUP BY g.generation, g.name
            ORDER BY g.generation
        """)
        
        gen_stats = cursor.fetchall()
        
        # Build stats text
        stats_text = "Collection Completion by Generation:\n\n"
        total_pokemon = 0
        total_imported = 0
        
        for gen_num, gen_name, pokemon_count, imported_count in gen_stats:
            if pokemon_count > 0:
                completion_rate = (imported_count / pokemon_count) * 100
                stats_text += f"{gen_name}: {imported_count}/{pokemon_count} ({completion_rate:.1f}%)\n"
                total_pokemon += pokemon_count
                total_imported += imported_count
        
        if total_pokemon > 0:
            overall_completion = (total_imported / total_pokemon) * 100
            stats_text += f"\nOverall: {total_imported}/{total_pokemon} ({overall_completion:.1f}%)"
        
        self.collection_stats_label.setText(stats_text)
        conn.close()
    
    def update_data_quality_stats(self):
        """Update data quality metrics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Data freshness
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN datetime(data_pull_timestamp) > datetime('now', '-7 days') THEN 1 END) as recent_records
            FROM bronze_tcg_cards
        """)
        
        total_records, recent_records = cursor.fetchone()
        
        # Missing images
        cursor.execute("""
            SELECT COUNT(*) FROM silver_tcg_cards 
            WHERE image_url_large IS NULL OR image_url_small IS NULL
        """)
        
        missing_images = cursor.fetchone()[0]
        
        quality_text = f"Data Quality Metrics:\n\n"
        quality_text += f"Total Records: {total_records}\n"
        quality_text += f"Recent (7 days): {recent_records}\n"
        quality_text += f"Missing Images: {missing_images}\n"
        
        if total_records > 0:
            freshness_rate = (recent_records / total_records) * 100
            quality_text += f"Data Freshness: {freshness_rate:.1f}%"
        
        self.data_quality_label.setText(quality_text)
        conn.close()
    
    def export_collection(self):
        """Export user collection to JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection", "my_pokemon_collection.json", 
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                collection = self.db_manager.get_user_collection()
                
                with open(file_path, 'w') as f:
                    json.dump(collection, f, indent=2)
                
                QMessageBox.information(self, "Export Complete", 
                    f"Collection exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")
    
    def backup_database(self):
        """Create a backup of the database"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", 
            f"pokedextop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", 
            "Database files (*.db)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.db_manager.db_path, file_path)
                QMessageBox.information(self, "Backup Complete", 
                    f"Database backed up to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")
                
    def on_main_tab_changed(self, index):
        """Handle main tab changes - auto-refresh Pokedex when switching back to it"""
        # Index 0 is the "My Pokédex" tab
        if index == 0:
            # Refresh all generation tabs
            self.refresh_all_tabs()
            print("📚 Auto-refreshed Pokédex after tab switch")

def center_window(window):
    """Center the window on the screen"""
    frame_geometry = window.frameGeometry()
    screen_center = QApplication.primaryScreen().availableGeometry().center()
    frame_geometry.moveCenter(screen_center)
    window.move(frame_geometry.topLeft())

def main():
    try:
        print("==== STARTING POKEDEXTOP TCG CLOUD EDITION ====")
        print("Bronze-Silver-Gold Data Architecture Initialized")
        
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        main_window = PokemonDashboard()
        
        # Center the fixed-size window
        center_window(main_window)
        main_window.show()
        
        print("Application ready! Window dimensions locked.")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"CRITICAL APPLICATION ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()