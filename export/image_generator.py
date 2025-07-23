# export/image_generator.py - UPDATED for Cache-First Export
"""
Collection Image Generator - Cache-Aware Version
Thread for generating collection images with cache integration
"""

import os
import sqlite3
import math
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt

from data.database import DatabaseManager
from cache.manager import CacheManager
from cache.image_loader import ImageLoader


class CollectionImageGenerator(QThread):
    """Thread for generating collection image with cache integration"""
    
    progress_updated = pyqtSignal(int, str)
    generation_complete = pyqtSignal(str)
    generation_error = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager, export_config: Dict[str, Any], 
                 cache_manager: CacheManager, image_loader: ImageLoader):
        super().__init__()
        self.db_manager = db_manager
        self.config = export_config
        self.cache_manager = cache_manager
        self.image_loader = image_loader
        
        # NO MORE in-memory image storage - stream from cache instead
        self.image_paths = {}  # card_id -> cached_path
    
    def run(self):
        """Generate the collection image"""
        try:
            # Step 1: Get collection data
            self.progress_updated.emit(5, "Loading collection data...")
            collection_data = self.get_collection_data()
            
            if not collection_data:
                self.generation_error.emit("No cards found in collection.")
                return
            
            # Step 2: Ensure all images are cached (NEW CACHE-FIRST LOGIC)
            self.progress_updated.emit(10, "Preparing image cache...")
            if not self.prepare_image_cache(collection_data):
                self.generation_error.emit("Failed to prepare image cache.")
                return
            
            # Step 3: Create composite image (streaming from cache)
            self.progress_updated.emit(70, "Creating collection image...")
            final_image = self.create_collection_image_from_cache(collection_data)
            
            # Step 4: Save image
            self.progress_updated.emit(90, "Saving image...")
            success = final_image.save(self.config['file_path'], 'PNG', 95)
            
            if success:
                self.progress_updated.emit(100, "Export complete!")
                self.generation_complete.emit(self.config['file_path'])
            else:
                self.generation_error.emit("Failed to save image file.")
                
        except Exception as e:
            self.generation_error.emit(f"Export error: {str(e)}")
    
    def prepare_image_cache(self, collection_data: List[Dict[str, Any]]) -> bool:
        """
        RESILIENT CACHE-FIRST METHOD: Handles API failures gracefully
        Always succeeds - uses placeholders for failed images
        """
        total_cards = len(collection_data)
        cached_count = 0
        download_count = 0
        failed_count = 0
        
        # Determine export quality based on config
        quality_map = {
            'high': 'export_high',
            'medium': 'export_medium', 
            'low': 'export_low'
        }
        export_quality = quality_map.get(self.config.get('image_quality', 'high'), 'export_high')
        
        for i, card_data in enumerate(collection_data):
            entity_id = card_data['card_id']
            
            if not card_data.get('image_url'):
                # No image URL - will use placeholder
                self.image_paths[entity_id] = None
                failed_count += 1
                continue
            
            cache_type = 'tcg_card'
            
            # Check if already cached
            cached_path = self.cache_manager.get_cached_path(entity_id, cache_type, export_quality)
            
            if cached_path and cached_path.exists():
                # Already cached!
                self.image_paths[entity_id] = cached_path
                cached_count += 1
                
                progress = 10 + int((i + 1) / total_cards * 60)
                self.progress_updated.emit(progress, f"Cache hit: {cached_count}, Failed: {failed_count}")
                
            else:
                # Try to download and cache - with fallback to smaller image
                cached_successfully = False
                
                # Try high-res image first
                try:
                    cached_path = self.cache_manager.cache_image(
                        card_data['image_url'], 
                        entity_id, 
                        cache_type, 
                        export_quality
                    )
                    
                    if cached_path and cached_path.exists():
                        self.image_paths[entity_id] = cached_path
                        download_count += 1
                        cached_successfully = True
                        
                except Exception as e:
                    print(f"High-res cache failed for {card_data['card_name']}: {e}")
                
                # If high-res failed, try fallback to small image
                if not cached_successfully and card_data.get('image_url') != card_data.get('image_url_small'):
                    try:
                        fallback_url = card_data['image_url'].replace('_hires.png', '.png')
                        cached_path = self.cache_manager.cache_image(
                            fallback_url, 
                            entity_id, 
                            cache_type, 
                            export_quality
                        )
                        
                        if cached_path and cached_path.exists():
                            self.image_paths[entity_id] = cached_path
                            download_count += 1
                            cached_successfully = True
                            print(f"✓ Fallback success for {card_data['card_name']}")
                            
                    except Exception as e:
                        print(f"Fallback cache failed for {card_data['card_name']}: {e}")
                
                # If both failed, use placeholder
                if not cached_successfully:
                    self.image_paths[entity_id] = None
                    failed_count += 1
                
                progress = 10 + int((i + 1) / total_cards * 60)
                self.progress_updated.emit(progress, f"Downloaded: {download_count}, Failed: {failed_count}")
        
        # Summary - ALWAYS SUCCEED, even with failures
        total_ready = cached_count + download_count
        placeholder_count = failed_count
        
        if total_ready > 0:
            self.progress_updated.emit(70, f"Cache ready: {total_ready}/{total_cards} images")
        else:
            self.progress_updated.emit(70, f"API issues: Using {placeholder_count} placeholders")
        
        # ALWAYS return True - export proceeds with placeholders for failed images
        return True
    
    def create_collection_image_from_cache(self, collection_data: List[Dict[str, Any]]) -> QPixmap:
        """
        NEW STREAMING METHOD: Create composite image by streaming from cache
        No bulk memory loading - process one image at a time
        """
        cards_per_row = self.config['cards_per_row']
        rows = math.ceil(len(collection_data) / cards_per_row)
        
        # Calculate dimensions based on quality
        quality_settings = {
            'high': {'card_width': 400, 'card_height': 560},
            'medium': {'card_width': 300, 'card_height': 420}, 
            'low': {'card_width': 200, 'card_height': 280}
        }
        
        settings = quality_settings.get(self.config.get('image_quality', 'high'), quality_settings['high'])
        card_width = settings['card_width']
        card_height = settings['card_height']
        
        padding = 20
        title_height = 80
        footer_height = 40
        
        # Calculate canvas size
        canvas_width = cards_per_row * card_width + (cards_per_row + 1) * padding
        canvas_height = title_height + rows * card_height + (rows + 1) * padding + footer_height
        
        # Create final canvas
        final_image = QPixmap(canvas_width, canvas_height)
        final_image.fill(QColor(245, 245, 245))
        
        painter = QPainter(final_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw title
        self._draw_title(painter, canvas_width, title_height)
        
        # Draw cards (STREAMING - one at a time)
        for i, card_data in enumerate(collection_data):
            row = i // cards_per_row
            col = i % cards_per_row
            
            x = padding + col * (card_width + padding)
            y = title_height + padding + row * (card_height + padding)
            
            # Load image from cache (streaming)
            card_pixmap = self._load_card_from_cache(
                card_data['card_id'], 
                card_width, 
                card_height,
                card_data.get('card_name', 'Unknown')
            )
            
            # Draw immediately and release from memory
            painter.drawPixmap(x, y, card_pixmap)
            
            # Optional: Draw labels if enabled
            if self.config.get('include_pokedex_info', False):
                self._draw_card_labels(painter, x, y, card_width, card_height, card_data)
        
        # Draw footer
        self._draw_footer(painter, canvas_width, canvas_height - footer_height)
        
        painter.end()
        return final_image
    
    def _load_card_from_cache(self, card_id: str, width: int, height: int, card_name: str) -> QPixmap:
        """
        Load single card image from cache and scale appropriately
        Memory efficient - only one image loaded at a time
        """
        cached_path = self.image_paths.get(card_id)
        
        if cached_path and cached_path.exists():
            # Load from cache
            pixmap = QPixmap(str(cached_path))
            if not pixmap.isNull():
                # Scale to export size
                return pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
        
        # Create placeholder
        return self._create_placeholder_image(width, height, card_name)
    
    def _create_placeholder_image(self, width: int, height: int, card_name: str) -> QPixmap:
        """Create informative placeholder for missing images"""
        placeholder = QPixmap(width, height)
        placeholder.fill(QColor(240, 240, 240))
        
        painter = QPainter(placeholder)
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(2, 2, width-4, height-4)
        
        # Add Pokemon card-like border
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(10, 10, width-20, height-20, 15, 15)
        
        # Add text with better formatting
        title_font = QFont("Arial", max(12, width // 25), QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(60, 60, 60))
        
        # Draw card name (truncated if needed)
        name_text = card_name[:15] + "..." if len(card_name) > 15 else card_name
        painter.drawText(15, height//3, name_text)
        
        # Add status text
        status_font = QFont("Arial", max(8, width // 35))
        painter.setFont(status_font)
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(15, height//2, "Image Unavailable")
        painter.drawText(15, height//2 + 20, "API Server Issue")
        
        # Add small logo/icon area
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        icon_size = min(width//4, height//4)
        painter.drawEllipse(width//2 - icon_size//2, height*2//3, icon_size, icon_size)
        
        painter.end()
        return placeholder
        
    def _draw_title(self, painter: QPainter, canvas_width: int, title_height: int):
        """Draw collection title"""
        title_font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(50, 50, 50))
        
        title_rect = painter.boundingRect(0, 0, canvas_width, title_height, 
                                        Qt.AlignmentFlag.AlignCenter, 
                                        self.config.get('custom_title', 'My Pokémon Collection'))
        
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, 
                        self.config.get('custom_title', 'My Pokémon Collection'))
    
    def _draw_card_labels(self, painter: QPainter, x: int, y: int, width: int, height: int, card_data: Dict[str, Any]):
        """Draw card labels if enabled"""
        if self.config.get('include_set_label', False):
            label_font = QFont("Arial", 10)
            painter.setFont(label_font)
            painter.setPen(QColor(70, 70, 70))
            painter.drawText(x + 5, y + height - 10, card_data.get('set_name', ''))
    
    def _draw_footer(self, painter: QPainter, canvas_width: int, footer_y: int):
        """Draw export footer"""
        footer_font = QFont("Arial", 10)
        painter.setFont(footer_font)
        painter.setPen(QColor(100, 100, 100))
        
        footer_text = f"Generated by PokéDextop on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        painter.drawText(10, footer_y + 20, footer_text)
    
    def get_collection_data(self) -> List[Dict[str, Any]]:
        """Get collection data from database - FIXED SCHEMA"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        if self.config['generation_filter'] == 'all':
            query = """
                SELECT DISTINCT 
                    uc.pokemon_id, uc.card_id, s.pokemon_name, s.name as card_name,
                    s.set_name, s.artist, s.image_url_large, s.image_url_small,
                    p.generation
                FROM gold_user_collections uc
                JOIN silver_tcg_cards s ON uc.card_id = s.card_id
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                ORDER BY uc.pokemon_id
            """
            cursor.execute(query)
        else:
            query = """
                SELECT DISTINCT 
                    uc.pokemon_id, uc.card_id, s.pokemon_name, s.name as card_name,
                    s.set_name, s.artist, s.image_url_large, s.image_url_small,
                    p.generation
                FROM gold_user_collections uc
                JOIN silver_tcg_cards s ON uc.card_id = s.card_id
                JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
                WHERE p.generation = ?
                ORDER BY uc.pokemon_id
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