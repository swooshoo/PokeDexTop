# export/image_generator.py
"""
Collection Image Generator - Extracted from app.py lines 200-500
Thread for generating collection images
"""

import os
import sqlite3
import math
import requests
from datetime import datetime
from typing import Dict, Any, List

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QNetworkAccessManager

from data.database import DatabaseManager


class CollectionImageGenerator(QThread):
    """Thread for generating collection image"""
    
    progress_updated = pyqtSignal(int, str)
    generation_complete = pyqtSignal(str)
    generation_error = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager, export_config: Dict[str, Any]):
        super().__init__()
        self.db_manager = db_manager
        self.config = export_config
        self.network_manager = QNetworkAccessManager()
        self.downloaded_images = {}
    
    def run(self):
        """Generate the collection image"""
        try:
            # Step 1: Get collection data
            self.progress_updated.emit(10, "Loading collection data...")
            collection_data = self.get_collection_data()
            
            if not collection_data:
                self.generation_error.emit("No cards found in collection.")
                return
            
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
    
    def get_collection_data(self) -> List[Dict[str, Any]]:
        """Get collection data from database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Build query based on generation filter
        if self.config['generation_filter'] == 'all':
            query = """
                SELECT uc.pokemon_id, uc.card_id, p.name as pokemon_name,
                       c.name as card_name, c.set_name, c.artist, c.image_url_large,
                       c.image_url_small, p.generation
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
                       c.image_url_small, p.generation
                FROM gold_user_collections uc
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                JOIN silver_tcg_cards c ON uc.card_id = c.card_id
                WHERE p.generation = ?
                ORDER BY p.pokemon_id
            """
            cursor.execute(query, (self.config['generation_filter'],))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'pokemon_id': row[0],
                'card_id': row[1], 
                'pokemon_name': row[2],
                'card_name': row[3],
                'set_name': row[4],
                'artist': row[5],
                'image_url': row[6] or row[7],  # Prefer large, fallback to small
                'generation': row[8]
            }
            for row in results
        ]
    
    def download_all_images(self, collection_data: List[Dict[str, Any]]):
        """Download all card images"""
        total_cards = len(collection_data)
        
        for i, card_data in enumerate(collection_data):
            if card_data['image_url']:
                try:
                    # Download image
                    response = requests.get(card_data['image_url'], timeout=10)
                    response.raise_for_status()
                    
                    # Create QPixmap from data
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    
                    if not pixmap.isNull():
                        self.downloaded_images[card_data['card_id']] = pixmap
                    
                except Exception as e:
                    print(f"Failed to download image for {card_data['card_name']}: {e}")
                    # Create placeholder
                    self.downloaded_images[card_data['card_id']] = self.create_placeholder_image()
                
                # Update progress
                progress = 20 + int((i + 1) / total_cards * 50)
                self.progress_updated.emit(progress, f"Downloaded {i + 1}/{total_cards} images...")
            else:
                # Create placeholder for missing image
                self.downloaded_images[card_data['card_id']] = self.create_placeholder_image()
    
    def create_placeholder_image(self) -> QPixmap:
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
    
    def create_collection_image(self, collection_data: List[Dict[str, Any]]) -> QPixmap:
        """Create the final collection image"""
        # Calculate dimensions
        cards_per_row = self.config['cards_per_row']
        total_cards = len(collection_data)
        rows = math.ceil(total_cards / cards_per_row)
        
        # Quality settings
        if self.config['image_quality'] == 'high':
            card_width, card_height = 245, 342
            spacing = 20
            font_size_title = 24
            font_size_labels = 10
        elif self.config['image_quality'] == 'medium':
            card_width, card_height = 180, 252
            spacing = 15
            font_size_title = 20
            font_size_labels = 9
        else:  # low
            card_width, card_height = 120, 168
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
        total_width = (cards_per_row * card_width) + ((cards_per_row + 1) * spacing)
        total_height = header_height + (rows * (card_height + label_height + spacing)) + spacing + footer_height
        
        # Create the final image
        final_image = QPixmap(total_width, total_height)
        final_image.fill(QColor(44, 62, 80))  # Dark blue background
        
        painter = QPainter(final_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw header with custom title
        self.draw_header(painter, total_width, header_height, collection_data, font_size_title)
        
        # Draw cards
        current_y = header_height + spacing
        for i, card_data in enumerate(collection_data):
            row = i // cards_per_row
            col = i % cards_per_row
            
            x = spacing + col * (card_width + spacing)
            y = current_y + row * (card_height + label_height + spacing)
            
            # Draw card image
            if card_data['card_id'] in self.downloaded_images:
                card_image = self.downloaded_images[card_data['card_id']]
                scaled_card = card_image.scaled(
                    card_width, card_height, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Center the scaled image
                card_x = x + (card_width - scaled_card.width()) // 2
                card_y = y + (card_height - scaled_card.height()) // 2
                painter.drawPixmap(card_x, card_y, scaled_card)
            
            # Draw labels
            if label_height > 0:
                self.draw_card_labels(
                    painter, card_data, x, y + card_height + 5, 
                    card_width, label_height, font_size_labels
                )
        
        # Draw footer
        footer_y = total_height - footer_height
        self.draw_footer(painter, total_width, footer_height, footer_y, font_size_title - 4)
        
        painter.end()
        return final_image
    
    def draw_header(self, painter: QPainter, width: int, height: int, 
                   collection_data: List[Dict[str, Any]], font_size: int):
        """Draw the header section with custom title"""
        painter.fillRect(0, 0, width, height, QColor(52, 73, 94))
        
        # Custom title
        painter.setPen(QPen(QColor(255, 255, 255)))
        title_font = QFont('Arial', font_size, QFont.Weight.Bold)
        painter.setFont(title_font)
        
        custom_title = self.config['custom_title']
        title_rect = painter.viewport()
        title_rect.setHeight(35)
        title_rect.moveTop(10)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, custom_title)
    
    def draw_footer(self, painter: QPainter, width: int, height: int, 
                   y_position: int, font_size: int):
        """Draw the footer section with export date and branding"""
        painter.fillRect(0, y_position, width, height, QColor(52, 73, 94))
        
        # Export date
        painter.setPen(QPen(QColor(189, 195, 199)))
        date_font = QFont('Arial', font_size)
        painter.setFont(date_font)
        
        export_date = datetime.now().strftime('%B %d, %Y')
        date_text = f"Exported on {export_date}"
        
        date_rect = painter.viewport()
        date_rect.setHeight(20)
        date_rect.moveTop(y_position + 10)
        painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, date_text)
    
    def draw_card_labels(self, painter: QPainter, card_data: Dict[str, Any], 
                        x: int, y: int, width: int, height: int, font_size: int):
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