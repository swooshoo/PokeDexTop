"""
TCG Card Widgets - Extracted from app.py lines 600-850
Card display widgets for browse functionality
"""

import os
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

from cache.image_loader import ImageLoader
from utils.session_cart import SessionCartManager


class ClickableTCGCard(QFrame):
    """Enhanced TCG card widget with double-click functionality"""
    
    cardSelected = pyqtSignal(str, dict)  # card_id, card_data
    
    def __init__(self, card_data: Dict[str, Any], image_loader: Optional[ImageLoader] = None, 
                 cart_manager: Optional[SessionCartManager] = None):
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
                (250, 310),
                entity_id=self.card_data.get('id'),
                cache_type='tcg_card'
            )
        elif self.card_data.get('image_url_small'):
            self.image_loader.load_image(
                self.card_data['image_url_small'], 
                self.image_label, 
                (250, 310),
                entity_id=self.card_data.get('id'),
                cache_type='tcg_card'
            )
        
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
    
    def update_cart_indicator(self, in_cart: bool):
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
    
    def __init__(self, card_data: Dict[str, Any], image_loader: ImageLoader):
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
        
        # Card image
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
        
        # Load image
        if self.card_data.get('image_url_large'):
            self.image_loader.load_image(
                self.card_data['image_url_large'], 
                self.image_label, 
                (75, 95),
                entity_id=self.card_data.get('id'),
                cache_type='tcg_card'
            )
        elif self.card_data.get('image_url_small'):
            self.image_loader.load_image(
                self.card_data['image_url_small'], 
                self.image_label, 
                (75, 95),
                entity_id=self.card_data.get('id'),
                cache_type='tcg_card'
            )
        
        # Card info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Card name
        name_label = QLabel(self.card_data.get('name', 'Unknown'))
        name_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white; background: transparent; border: none;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
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
        
        # Remove button
        self.remove_label = QLabel()
        
        # Try to load delete icon
        icon_path = "assets/icons/delete.png"
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
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
        
        info_layout.addWidget(self.remove_label, alignment=Qt.AlignmentFlag.AlignLeft)
        info_layout.addStretch()
        layout.addLayout(info_layout)
    
    def on_remove_clicked(self, event):
        """Handle remove label click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.removeRequested.emit(self.card_data['card_id'])