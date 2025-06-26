from PyQt5.QtCore import QObject, pyqtSignal, QUrl, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class ImageLoader(QObject):
    """Centralized image loading utility for the application"""
    
    imageLoaded = pyqtSignal(QPixmap)
    
    def __init__(self):
        super().__init__()
        self._network_manager = QNetworkAccessManager()
        self._loading_images = {}  # Track ongoing requests
        self._image_cache = {}  # Simple in-memory cache
    
    def load_image(self, url, label, size=None):
        """
        Load an image from URL and set it on a QLabel
        
        Args:
            url: Image URL
            label: QLabel to set the image on
            size: Optional tuple (width, height) to scale the image
        """
        if not url:
            label.setText("No Image")
            return
        
        # Check cache first
        if url in self._image_cache:
            self._set_image_on_label(label, self._image_cache[url], size)
            return
        
        # Show loading state
        label.setText("Loading...")
        label.setStyleSheet("color: #7f8c8d; background-color: #2c3e50; border-radius: 4px;")
        
        # Create request
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute, 
                           QNetworkRequest.PreferCache)
        
        reply = self._network_manager.get(request)
        
        # Store the reply with its associated data
        self._loading_images[reply] = (label, size, url)
        
        # Connect signals
        reply.finished.connect(lambda: self._on_image_loaded(reply))
        reply.error.connect(lambda: self._on_image_error(reply))
    
    def _on_image_loaded(self, reply):
        """Handle image loading completion"""
        if reply not in self._loading_images:
            reply.deleteLater()
            return
        
        label, size, url = self._loading_images.pop(reply)
        
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            
            if pixmap.loadFromData(data):
                # Cache the pixmap
                self._image_cache[url] = pixmap
                # Set on label
                self._set_image_on_label(label, pixmap, size)
            else:
                label.setText("Invalid\nImage")
                label.setStyleSheet("color: #e74c3c; background-color: #2c3e50; border-radius: 4px;")
        else:
            self._on_image_error(reply)
        
        reply.deleteLater()
    
    def _on_image_error(self, reply):
        """Handle image loading errors"""
        if reply in self._loading_images:
            label, _, _ = self._loading_images.pop(reply)
            label.setText("Failed to\nLoad Image")
            label.setStyleSheet("color: #e74c3c; background-color: #2c3e50; border-radius: 4px;")
        reply.deleteLater()
    
    def _set_image_on_label(self, label, pixmap, size):
        """Set pixmap on label with optional scaling"""
        if size:
            scaled_pixmap = pixmap.scaled(size[0], size[1], 
                                         Qt.KeepAspectRatio, 
                                         Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
        else:
            # Scale to label size
            label_size = label.size()
            scaled_pixmap = pixmap.scaled(label_size, 
                                         Qt.KeepAspectRatio, 
                                         Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
        
        label.setStyleSheet("")  # Clear loading styles