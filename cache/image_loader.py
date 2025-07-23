"""
Enhanced Image Loader with cache integration
Implements dual pipeline: fast UI loading + high-quality export caching
"""

from PyQt6 import sip
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QLabel

from cache.manager import CacheManager
from config.settings import IMAGE_QUALITY_CONFIGS


class ImageLoader(QObject):
    """
    Enhanced image loader with cache integration and dual pipeline support
    - Fast loading for UI display
    - High-quality caching for export
    """
    
    imageLoaded = pyqtSignal(QPixmap)
    cachingComplete = pyqtSignal(str, str)  # entity_id, cached_path
    
    def __init__(self, cache_manager: CacheManager):
        super().__init__()
        self.cache_manager = cache_manager
        self._network_manager = QNetworkAccessManager()
        self._loading_images = {}  # reply -> (label, size, url, entity_id, cache_type)
        self._image_cache = {}     # In-memory cache for UI
        self._pending_cache_jobs = []
        
        # Background caching timer
        self._cache_timer = QTimer()
        self._cache_timer.timeout.connect(self._process_cache_queue)
        self._cache_timer.start(1000)  # Check every second
    
    def load_image(self, url: str, label: QLabel, size: Optional[Tuple[int, int]] = None,
                entity_id: Optional[str] = None, cache_type: str = 'tcg_card'):
        # REMOVE DEBUG SPAM - only log when debugging specific issues
        # print(f"*load_image: entity_id={entity_id}, cache_type={cache_type}, url={url[:50]}...")
        
        if cache_type == 'sprite' and entity_id:
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            sprite_path = project_root / 'assets' / 'sprites' / 'pokemon' / f"{entity_id}.png"
            
            if sprite_path.exists():
                pixmap = QPixmap(str(sprite_path))
                if not pixmap.isNull():
                    if size:
                        pixmap = pixmap.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(pixmap)
                    
                    # Apply sprite styling
                    label.setStyleSheet("""
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #f0f8ff, stop: 1 #e6f3ff);
                        border-radius: 6px; 
                        border: 2px solid #4a90e2;
                        padding: 8px;
                    """)
                    return
            
            # No local sprite - show clean placeholder and STOP (no download)
            label.setText(f"#{entity_id}\nSprite\nMissing")
            label.setStyleSheet("""
                background-color: #f8f9fa; 
                border-radius: 8px; 
                color: #6c757d;
                font-size: 10px;
                border: 2px dashed #dee2e6;
                padding: 15px;
            """)
            return  # ✅ STOP HERE - no network requests for missing sprites
        
        if not url:
            label.setText("No Image")
            return
        
        # Check in-memory cache first (fastest)
        cache_key = f"{url}_{size}"
        if cache_key in self._image_cache:
            self._set_image_on_label(label, self._image_cache[cache_key], size)
            self._apply_post_load_styling(label, url)
            return
        
        # Check file cache
        if entity_id and self.cache_manager:
            cached_path = self.cache_manager.get_cached_path(entity_id, cache_type, 'ui')
            if cached_path:
                pixmap = QPixmap(str(cached_path))
                if not pixmap.isNull():
                    self._image_cache[cache_key] = pixmap
                    self._set_image_on_label(label, pixmap, size)
                    self._apply_post_load_styling(label, url)
                    return
        
        # Only download for TCG cards and specific requests - NOT for missing sprites
        if cache_type == 'tcg_card':
            self._download_for_ui(url, label, size, entity_id, cache_type)
        else:
            # For other cache types, show placeholder instead of downloading
            label.setText("Image Unavailable")
            label.setStyleSheet("background-color: #f0f0f0; color: #666; padding: 10px;")
    
    def cache_for_export(self, url: str, entity_id: str, cache_type: str, 
                        quality: str = 'export_high', callback=None):
        """
        Cache image for export use (high quality)
        Uses background processing for export pipeline
        """
        if not self.cache_manager:
            if callback:
                callback(None)
            return
        
        # Check if already cached
        cached_path = self.cache_manager.get_cached_path(entity_id, cache_type, quality)
        if cached_path:
            if callback:
                callback(str(cached_path))
            return
        
        # Add to background cache queue
        cache_job = {
            'url': url,
            'entity_id': entity_id,
            'cache_type': cache_type,
            'quality': quality,
            'callback': callback,
            'priority': 1 if quality.startswith('export') else 0
        }
        
        self._pending_cache_jobs.append(cache_job)
        self._pending_cache_jobs.sort(key=lambda x: x['priority'], reverse=True)
    
    def _download_for_ui(self, url: str, label: QLabel, size: Optional[Tuple[int, int]],
                        entity_id: Optional[str], cache_type: str):
        """Download image for immediate UI display"""
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.PreferCache
        )
        
        reply = self._network_manager.get(request)
        
        # Store reply data
        self._loading_images[reply] = (label, size, url, entity_id, cache_type)
        
        # Connect signals
        reply.finished.connect(lambda: self._on_ui_image_loaded(reply))
        reply.errorOccurred.connect(lambda: self._on_ui_image_error(reply))
    
    def _on_ui_image_loaded(self, reply):
        """Handle UI image loading completion"""
        if reply not in self._loading_images:
            reply.deleteLater()
            return
        
        label, size, url, entity_id, cache_type = self._loading_images.pop(reply)
        
        # Check if label still exists
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
                # Cache in memory for UI
                cache_key = f"{url}_{size}"
                self._image_cache[cache_key] = pixmap
                
                try:
                    self._set_image_on_label(label, pixmap, size)
                    self._apply_post_load_styling(label, url)
                    
                    # Optionally cache to disk for UI quality
                    if entity_id and self.cache_manager:
                        self._queue_background_cache(url, entity_id, cache_type, 'ui')
                        
                except RuntimeError:
                    pass
            else:
                try:
                    self._show_image_error(label, url)
                except RuntimeError:
                    pass
        else:
            self._on_ui_image_error(reply)
        
        reply.deleteLater()
    
    def _on_ui_image_error(self, reply):
        """Handle UI image loading errors"""
        if reply in self._loading_images:
            label, _, url, _, _ = self._loading_images.pop(reply)
            
            try:
                if not sip.isdeleted(label):
                    self._show_image_error(label, url)
            except:
                try:
                    self._show_image_error(label, url)
                except RuntimeError:
                    pass
        
        reply.deleteLater()
    
    def _apply_post_load_styling(self, label: QLabel, url: str):
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
                # TCG card - keep clean dark styling
                label.setStyleSheet("""
                    background-color: #2c3e50; 
                    border-radius: 6px;
                """)
        except RuntimeError:
            pass
    
    def _show_image_error(self, label: QLabel, url: str):
        """Show error state for failed image loading"""
        try:
            if "pokemon/" in url:
                label.setText("No Sprite\nAvailable")
                label.setStyleSheet("""
                    background-color: #f8f9fa; 
                    border-radius: 6px; 
                    color: #6c757d;
                    font-size: 10px;
                    border: 2px dashed #dee2e6;
                    padding: 15px;
                """)
            else:
                label.setText("No Image\nAvailable")
                label.setStyleSheet("""
                    background-color: #2c3e50; 
                    border-radius: 6px; 
                    color: #7f8c8d;
                    font-size: 10px;
                    border: 2px dashed #34495e;
                    padding: 15px;
                """)
        except RuntimeError:
            pass
    
    def _set_image_on_label(self, label: QLabel, pixmap: QPixmap, size: Optional[Tuple[int, int]]):
        """Set pixmap on label with optional scaling"""
        try:
            if sip.isdeleted(label):
                return
        except:
            pass
        
        try:
            if size:
                from PyQt6.QtCore import Qt
                scaled_pixmap = pixmap.scaled(
                    size[0], size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
            else:
                label_size = label.size()
                from PyQt6.QtCore import Qt
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
        except RuntimeError:
            pass
    
    def _queue_background_cache(self, url: str, entity_id: str, cache_type: str, quality: str):
        """Queue a background caching job"""
        cache_job = {
            'url': url,
            'entity_id': entity_id,
            'cache_type': cache_type,
            'quality': quality,
            'callback': None,
            'priority': 0
        }
        
        # Check if already queued
        for job in self._pending_cache_jobs:
            if (job['entity_id'] == entity_id and 
                job['cache_type'] == cache_type and 
                job['quality'] == quality):
                return
        
        self._pending_cache_jobs.append(cache_job)
    
    def _process_cache_queue(self):
        """Process background cache queue"""
        if not self._pending_cache_jobs:
            return
        
        # Process one job per timer tick to avoid blocking UI
        job = self._pending_cache_jobs.pop(0)
        
        try:
            cached_path = self.cache_manager.cache_image(
                job['url'],
                job['entity_id'],
                job['cache_type'],
                job['quality']
            )
            
            if cached_path and job['callback']:
                job['callback'](str(cached_path))
            
            if cached_path:
                self.cachingComplete.emit(job['entity_id'], str(cached_path))
                
        except Exception as e:
            print(f"Background cache error: {e}")
            if job['callback']:
                job['callback'](None)
    
    def prepare_export_cache(self, collection_data: list, quality: str = 'export_high',
                           progress_callback=None):
        """
        Prepare cache for export by ensuring all images are cached
        
        Args:
            collection_data: List of items to cache
            quality: Quality level for export
            progress_callback: Function to call with progress (current, total)
        """
        total_items = len(collection_data)
        cached_items = 0
        
        for i, item in enumerate(collection_data):
            try:
                if item.get('has_tcg_card'):
                    # Cache TCG card
                    entity_id = item['card_id']
                    cache_type = 'tcg_card'
                    url = item.get('image_url')
                else:
                    # Cache sprite
                    entity_id = str(item['pokemon_id'])
                    cache_type = 'sprite'
                    url = item.get('sprite_url')
                
                if url:
                    cached_path = self.cache_manager.cache_image(
                        url, entity_id, cache_type, quality
                    )
                    if cached_path:
                        cached_items += 1
                
                if progress_callback:
                    progress_callback(i + 1, total_items)
                    
            except Exception as e:
                print(f"Error caching {item}: {e}")
        
        return cached_items
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics"""
        stats = {
            'memory_cache_size': len(self._image_cache),
            'pending_cache_jobs': len(self._pending_cache_jobs),
            'active_downloads': len(self._loading_images)
        }
        
        if self.cache_manager:
            disk_stats = self.cache_manager.get_cache_stats()
            stats.update(disk_stats)
        
        return stats
    
    def clear_memory_cache(self):
        """Clear in-memory image cache"""
        self._image_cache.clear()
    
    def cancel_all_requests(self):
        """Cancel all pending image requests"""
        for reply in list(self._loading_images.keys()):
            reply.abort()
            reply.deleteLater()
        self._loading_images.clear()
        self._pending_cache_jobs.clear()


class ExportImageLoader(QObject):
    """
    Specialized image loader for export operations
    Focuses on high-quality caching and batch operations
    """
    
    batchComplete = pyqtSignal(int, int)  # completed, total
    
    def __init__(self, cache_manager: CacheManager):
        super().__init__()
        self.cache_manager = cache_manager
    
    def load_for_export_widget(self, entity_id: str, cache_type: str, 
                              quality: str = 'export_high') -> Optional[QPixmap]:
        """
        Load image for export widget (synchronous, from cache only)
        
        Args:
            entity_id: Pokemon ID or Card ID
            cache_type: 'tcg_card', 'sprite', 'artwork'
            quality: Quality level
        
        Returns:
            QPixmap if cached, None otherwise
        """
        cached_path = self.cache_manager.get_cached_path(entity_id, cache_type, quality)
        
        if cached_path and cached_path.exists():
            pixmap = QPixmap(str(cached_path))
            if not pixmap.isNull():
                return pixmap
        
        return None
    
    def batch_cache_for_export(self, items: list, quality: str = 'export_high',
                              progress_callback=None) -> Dict[str, str]:
        """
        Cache multiple items for export in batch
        
        Args:
            items: List of {entity_id, url, cache_type} dicts
            quality: Quality level
            progress_callback: Progress callback function
        
        Returns:
            Dict mapping entity_id to cached_path
        """
        cached_paths = {}
        total = len(items)
        
        for i, item in enumerate(items):
            try:
                cached_path = self.cache_manager.cache_image(
                    item['url'],
                    item['entity_id'],
                    item['cache_type'],
                    quality
                )
                
                if cached_path:
                    cached_paths[item['entity_id']] = str(cached_path)
                
                if progress_callback:
                    progress_callback(i + 1, total)
                
            except Exception as e:
                print(f"Batch cache error for {item['entity_id']}: {e}")
        
        self.batchComplete.emit(len(cached_paths), total)
        return cached_paths
    
    def verify_export_cache(self, collection_data: list, quality: str = 'export_high') -> Dict[str, bool]:
        """
        Verify that all items in collection are properly cached for export
        
        Args:
            collection_data: Collection data to verify
            quality: Required quality level
        
        Returns:
            Dict mapping entity_id to cached status (True/False)
        """
        cache_status = {}
        
        for item in collection_data:
            if item.get('has_tcg_card'):
                entity_id = item['card_id']
                cache_type = 'tcg_card'
            else:
                entity_id = str(item['pokemon_id'])
                cache_type = 'sprite'
            
            cached_path = self.cache_manager.get_cached_path(entity_id, cache_type, quality)
            cache_status[entity_id] = cached_path is not None and cached_path.exists()
        
        return cache_status