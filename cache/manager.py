"""
Cache management system for local image storage
Implements the cache layer from the hybrid strategy
"""

import os
import sqlite3
import hashlib
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import requests
from PyQt6.QtGui import QPixmap

from config.settings import CACHE_CONFIG, IMAGE_QUALITY_CONFIGS


class CacheManager:
    """
    Manages local image cache for both UI and export quality images
    Implements the cache layer from the hybrid strategy
    """
    
    def __init__(self, cache_root: Optional[Path] = None):
        self.cache_root = cache_root or Path.home() / '.pokedextop' / 'cache'
        self.cache_db = self.cache_root / 'cache_index.db'
        
        # Ensure cache directories exist
        self._create_cache_directories()
        
        # Initialize cache database
        self._init_cache_database()
    
    def _create_cache_directories(self):
        """Create all cache directories from config"""
        for cache_type, paths in CACHE_CONFIG.items():
            for quality, path in paths.items():
                path.mkdir(parents=True, exist_ok=True)
    
    def _init_cache_database(self):
        """Initialize the cache tracking database"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                cache_type TEXT NOT NULL,  -- 'tcg_card', 'sprite', 'artwork'
                quality_level TEXT NOT NULL,  -- 'original', 'ui', 'export_high', etc.
                original_url TEXT NOT NULL,
                cached_path TEXT NOT NULL,
                file_size INTEGER,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                UNIQUE(entity_id, cache_type, quality_level)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_lookup 
            ON cache_entries(entity_id, cache_type, quality_level)
        """)
        
        conn.commit()
        conn.close()
    
    def get_cached_path(self, entity_id: str, cache_type: str, quality: str = 'original') -> Optional[Path]:
        """
        Get cached file path if it exists
        
        Args:
            entity_id: Pokemon ID or Card ID
            cache_type: 'tcg_card', 'sprite', 'artwork'
            quality: 'original', 'ui', 'export_high', 'export_medium', 'export_low'
        
        Returns:
            Path to cached file if exists, None otherwise
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cached_path FROM cache_entries 
            WHERE entity_id = ? AND cache_type = ? AND quality_level = ?
        """, (entity_id, cache_type, quality))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            cached_path = Path(result[0])
            if cached_path.exists():
                # Update last accessed time
                self._update_last_accessed(entity_id, cache_type, quality)
                return cached_path
            else:
                # File doesn't exist, remove from database
                self._remove_cache_entry(entity_id, cache_type, quality)
        
        return None
    
    def cache_image(self, url: str, entity_id: str, cache_type: str, quality: str = 'original') -> Optional[Path]:
        """
        Download and cache an image
        
        Args:
            url: Original image URL
            entity_id: Pokemon ID or Card ID
            cache_type: 'tcg_card', 'sprite', 'artwork'
            quality: Quality level for processing
        
        Returns:
            Path to cached file if successful, None otherwise
        """
        try:
            # Check if already cached
            existing_path = self.get_cached_path(entity_id, cache_type, quality)
            if existing_path:
                return existing_path
            
            # Download the image
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            file_extension = self._get_file_extension(url, response.headers.get('content-type', ''))
            filename = f"{entity_id}_{url_hash}{file_extension}"
            
            # Determine cache directory
            cache_dir = self._get_cache_directory(cache_type, quality)
            cached_path = cache_dir / filename
            
            # Process and save image based on quality level
            processed_data = self._process_image_data(response.content, quality)
            
            with open(cached_path, 'wb') as f:
                f.write(processed_data)
            
            # Record in database
            self._record_cache_entry(
                entity_id, cache_type, quality, url, 
                cached_path, len(processed_data), response.content
            )
            
            return cached_path
            
        except Exception as e:
            print(f"Failed to cache image {url}: {e}")
            return None
    
    def _get_cache_directory(self, cache_type: str, quality: str) -> Path:
        """Get the appropriate cache directory for the given type and quality"""
        if quality == 'original':
            return CACHE_CONFIG[cache_type]['original']
        elif quality == 'ui':
            return CACHE_CONFIG[cache_type]['ui']
        elif quality.startswith('export'):
            return CACHE_CONFIG[cache_type]['export']
        else:
            return CACHE_CONFIG[cache_type]['original']
    
    def _process_image_data(self, image_data: bytes, quality: str) -> bytes:
        """
        Process image data based on quality requirements
        
        Args:
            image_data: Raw image bytes
            quality: Quality level
        
        Returns:
            Processed image bytes
        """
        if quality == 'original':
            # No processing for original quality
            return image_data
        
        try:
            # Load image into QPixmap for processing
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            
            if pixmap.isNull():
                return image_data
            
            # Get quality config
            quality_config = IMAGE_QUALITY_CONFIGS.get(quality, IMAGE_QUALITY_CONFIGS['ui'])
            max_width = quality_config['max_width']
            max_height = quality_config['max_height']
            
            # Scale if needed
            if pixmap.width() > max_width or pixmap.height() > max_height:
                from PyQt6.QtCore import Qt
                pixmap = pixmap.scaled(
                    max_width, max_height, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
            
            # Convert back to bytes
            from PyQt6.QtCore import QBuffer, QIODevice
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            
            # Determine format and quality
            if quality.startswith('export'):
                # High quality for export
                pixmap.save(buffer, 'PNG', quality_config['png_compression'])
            else:
                # Compressed for UI
                pixmap.save(buffer, 'JPEG', quality_config['jpeg_quality'])
            
            return buffer.data().data()
            
        except Exception as e:
            print(f"Failed to process image data: {e}")
            return image_data
    
    def _get_file_extension(self, url: str, content_type: str) -> str:
        """Determine appropriate file extension"""
        if content_type:
            if 'png' in content_type.lower():
                return '.png'
            elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                return '.jpg'
        
        # Fall back to URL extension
        if url.lower().endswith(('.png', '.jpg', '.jpeg')):
            return '.' + url.split('.')[-1].lower()
        
        return '.png'  # Default
    
    def _record_cache_entry(self, entity_id: str, cache_type: str, quality: str, 
                           original_url: str, cached_path: Path, file_size: int, 
                           original_data: bytes):
        """Record cache entry in database"""
        content_hash = hashlib.sha256(original_data).hexdigest()
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO cache_entries 
            (entity_id, cache_type, quality_level, original_url, cached_path, 
             file_size, content_hash, cached_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id, cache_type, quality, original_url, str(cached_path),
            file_size, content_hash, datetime.now(), datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_last_accessed(self, entity_id: str, cache_type: str, quality: str):
        """Update last accessed timestamp"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE cache_entries 
            SET last_accessed = ? 
            WHERE entity_id = ? AND cache_type = ? AND quality_level = ?
        """, (datetime.now(), entity_id, cache_type, quality))
        
        conn.commit()
        conn.close()
    
    def _remove_cache_entry(self, entity_id: str, cache_type: str, quality: str):
        """Remove cache entry from database"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM cache_entries 
            WHERE entity_id = ? AND cache_type = ? AND quality_level = ?
        """, (entity_id, cache_type, quality))
        
        conn.commit()
        conn.close()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cache_type,
                quality_level,
                COUNT(*) as count,
                SUM(file_size) as total_size
            FROM cache_entries 
            GROUP BY cache_type, quality_level
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        stats = {}
        total_files = 0
        total_size = 0
        
        for cache_type, quality, count, size in results:
            if cache_type not in stats:
                stats[cache_type] = {}
            
            stats[cache_type][quality] = {
                'count': count,
                'size': size or 0
            }
            
            total_files += count
            total_size += size or 0
        
        stats['totals'] = {
            'files': total_files,
            'size': total_size
        }
        
        return stats
    
    def cleanup_old_cache(self, days_old: int = 30) -> Tuple[int, int]:
        """
        Clean up old unused cache files
        
        Args:
            days_old: Remove files not accessed in this many days
        
        Returns:
            Tuple of (files_removed, bytes_freed)
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cached_path, file_size 
            FROM cache_entries 
            WHERE last_accessed < ?
        """, (cutoff_date,))
        
        old_entries = cursor.fetchall()
        
        files_removed = 0
        bytes_freed = 0
        
        for cached_path, file_size in old_entries:
            try:
                path = Path(cached_path)
                if path.exists():
                    path.unlink()
                    files_removed += 1
                    bytes_freed += file_size or 0
            except Exception as e:
                print(f"Failed to remove {cached_path}: {e}")
        
        # Remove from database
        cursor.execute("""
            DELETE FROM cache_entries 
            WHERE last_accessed < ?
        """, (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        return files_removed, bytes_freed
    
    def clear_cache(self, cache_type: Optional[str] = None, quality: Optional[str] = None):
        """
        Clear cache (optionally filtered by type and quality)
        
        Args:
            cache_type: Optional cache type filter
            quality: Optional quality filter
        """
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        # Build query
        where_conditions = []
        params = []
        
        if cache_type:
            where_conditions.append("cache_type = ?")
            params.append(cache_type)
        
        if quality:
            where_conditions.append("quality_level = ?")
            params.append(quality)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Get files to remove
        cursor.execute(f"SELECT cached_path FROM cache_entries WHERE {where_clause}", params)
        cached_paths = cursor.fetchall()
        
        # Remove files
        for (cached_path,) in cached_paths:
            try:
                Path(cached_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"Failed to remove {cached_path}: {e}")
        
        # Remove from database
        cursor.execute(f"DELETE FROM cache_entries WHERE {where_clause}", params)
        
        conn.commit()
        conn.close()