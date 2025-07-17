"""
Main application window - PokemonDashboard
Extracted and cleaned from the monolithic app.py
"""

import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QPushButton, QLabel, QApplication)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont

from config.settings import DARK_THEME_STYLE
from data.database import DatabaseManager
from cache.manager import CacheManager
from cache.image_loader import ImageLoader
from core.session import SessionCartManager
from ui.tabs.generation_tab import GenerationTab
from ui.tabs.browse_tab import EnhancedBrowseTCGTab
from ui.tabs.analytics_tab import EnhancedAnalyticsTab
from ui.dialogs.sync_dialog import DataSyncDialog


class PokemonDashboard(QMainWindow):
    """
    Main application window with clean, modular architecture
    Manages the overall application state and coordinates between components
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize core systems
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        self.image_loader = ImageLoader(self.cache_manager)
        self.session_cart = SessionCartManager()
        
        # Load generations from database
        self.load_generations()
        
        # Initialize UI
        self.initUI()
        
        # Set up auto-refresh
        self.setup_auto_refresh()
    
    def load_generations(self):
        """Load generation data from database"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT generation, name FROM gold_pokemon_generations 
            ORDER BY generation
        """)
        
        self.generations = cursor.fetchall()
        conn.close()
    
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle('PokéDextop 1.0')
        
        # Set window to full available screen area
        self.setup_window_geometry()
        
        # Apply dark theme
        self.setStyleSheet(DARK_THEME_STYLE)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar(main_layout)
        
        # Create main tab widget
        self.create_main_tabs(main_layout)
        
        # Set up status bar
        self.update_status_bar()
    
    def setup_window_geometry(self):
        """Set up window geometry to use full available screen"""
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry()
        
        # Lock to available screen dimensions
        self.setFixedSize(available_geometry.width(), available_geometry.height())
        self.move(available_geometry.x(), available_geometry.y())
    
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
    
    def create_main_tabs(self, main_layout):
        """Create the main tab widget with all tabs"""
        self.main_tabs = QTabWidget()
        
        # Create Pokédex tab with generation sub-tabs
        self.create_pokedex_tab()
        
        # Create TCG Browse tab
        self.create_tcg_browse_tab()
        
        # Create Analytics tab
        self.create_analytics_tab()
        
        # Connect tab change event
        self.main_tabs.currentChanged.connect(self.on_main_tab_changed)
        
        main_layout.addWidget(self.main_tabs)
    
    def create_pokedex_tab(self):
        """Create the main Pokédex tab with generation sub-tabs"""
        pokedex_tab = QWidget()
        pokedex_layout = QVBoxLayout(pokedex_tab)
        
        # Create generation tabs
        self.gen_tabs = QTabWidget()
        
        for generation, gen_name in self.generations:
            gen_tab = GenerationTab(
                gen_name, 
                generation, 
                self.db_manager, 
                self.image_loader
            )
            self.gen_tabs.addTab(gen_tab, f"Gen {generation}")
        
        pokedex_layout.addWidget(self.gen_tabs)
        self.main_tabs.addTab(pokedex_tab, "📚 My Pokédex")
    
    def create_tcg_browse_tab(self):
        """Create the TCG browsing tab"""
        browse_tab = EnhancedBrowseTCGTab(
            self.db_manager,
            self.image_loader,
            self.session_cart
        )
        
        self.main_tabs.addTab(browse_tab, "🃏 Browse TCG Cards")
    
    def create_analytics_tab(self):
        """Create the analytics and export tab"""
        analytics_tab = EnhancedAnalyticsTab(
            self.db_manager,
            self.cache_manager,
            self
        )
        
        self.main_tabs.addTab(analytics_tab, "📊 Analytics")
    
    def setup_auto_refresh(self):
        """Set up auto-refresh timer for status updates"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_status_bar)
        self.refresh_timer.start(30000)  # Update every 30 seconds
    
    def open_sync_dialog(self):
        """Open the data synchronization dialog"""
        dialog = DataSyncDialog(self.db_manager, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            # Refresh all tabs after sync
            self.refresh_all_tabs()
            self.update_status_bar()
    
    def refresh_all_tabs(self):
        """Refresh all generation tabs and other content"""
        # Refresh Pokédex generation tabs
        for i in range(self.gen_tabs.count()):
            gen_tab = self.gen_tabs.widget(i)
            if hasattr(gen_tab, 'refresh_data'):
                gen_tab.refresh_data()
        
        # Refresh other tabs as needed
        # (Browse and Analytics tabs can handle their own refresh)
    
    def on_main_tab_changed(self, index):
        """Handle main tab changes - auto-refresh Pokédex when switching back"""
        # Index 0 is the "My Pokédex" tab
        if index == 0:
            self.refresh_all_tabs()
            print("📚 Auto-refreshed Pokédex after tab switch")
    
    def update_status_bar(self):
        """Update the status bar with current statistics"""
        import sqlite3
        
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
        
        # Update status bar
        if not hasattr(self, '_status_bar_initialized'):
            self.statusBar().showMessage(status_text)
            self._status_bar_initialized = True
        else:
            self.statusBar().showMessage(status_text)
        
        # Update toolbar stats
        self.stats_label.setText(status_text)
    
    def get_cache_stats(self):
        """Get cache statistics for display"""
        return self.cache_manager.get_cache_stats()
    
    def cleanup_cache(self, days_old: int = 30):
        """Clean up old cache files"""
        return self.cache_manager.cleanup_old_cache(days_old)
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Clean up resources
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        # Cancel any pending image loads
        if hasattr(self.image_loader, 'cancel_all_requests'):
            self.image_loader.cancel_all_requests()
        
        # Accept the close event
        event.accept()