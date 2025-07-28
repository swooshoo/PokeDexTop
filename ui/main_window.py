"""
Main application window - PokemonDashboard
Extracted and cleaned from the monolithic app.py
"""

import sys
import sqlite3

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QPushButton, QLabel, QApplication)
from PyQt6.QtCore import QTimer

from config.settings import DARK_THEME_STYLE
from data.database import DatabaseManager
from cache.manager import CacheManager
from cache.image_loader import ImageLoader
from core.session import SessionCartManager

from ui.tabs.browse_tab import EnhancedBrowseTCGTab
from ui.tabs.analytics_tab import EnhancedAnalyticsTab
from ui.tabs.analytics_tab import GenerationTab
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
        # NEW: Set up collection modification callback
        self.db_manager.set_collection_modified_callback(self.mark_analytics_dirty)
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
        """Create the analytics and export tab with cache dependencies"""
        analytics_tab = EnhancedAnalyticsTab(
            self.db_manager,
            self.cache_manager,    # NEW: Pass cache manager
            self.image_loader,     # NEW: Pass image loader  
            self
        )
        
        self.main_tabs.addTab(analytics_tab, "📊 Analytics")
    
    def on_generation_tab_changed(self, index):
        """Handle generation tab changes - trigger lazy loading"""
        if index < 0:
            return
            
        # Deactivate previous tab
        for i in range(self.gen_tabs.count()):
            if i != index:
                tab = self.gen_tabs.widget(i)
                if hasattr(tab, 'on_tab_deactivated'):
                    tab.on_tab_deactivated()
        
        # Activate current tab
        current_tab = self.gen_tabs.widget(index)
        if hasattr(current_tab, 'on_tab_activated'):
            current_tab.on_tab_activated()
            
        print(f"📊 Switched to generation tab: {current_tab.gen_name}")
    
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
            
            # NEW: Mark analytics stats as dirty after sync
            analytics_tab = self.get_analytics_tab()
            if analytics_tab and hasattr(analytics_tab, 'mark_stats_dirty'):
                analytics_tab.mark_stats_dirty()
    
    def refresh_all_tabs(self):
        """Refresh all generation tabs"""
        for i in range(self.gen_tabs.count()):
            tab = self.gen_tabs.widget(i)
            if hasattr(tab, 'refresh_data'):
                tab.refresh_data()
    
    def get_analytics_tab(self):
        """Get reference to analytics tab widget"""
        for i in range(self.main_tabs.count()):
            tab = self.main_tabs.widget(i)
            if isinstance(tab, EnhancedAnalyticsTab):
                return tab
        return None

    def mark_analytics_dirty(self):
        """Convenience method to mark analytics stats as dirty"""
        analytics_tab = self.get_analytics_tab()
        if analytics_tab:
            analytics_tab.mark_stats_dirty()
        
    def on_main_tab_changed(self, index):
        """Handle main tab changes - auto-refresh Pokédex when switching back"""
        # Index 0 is the "My Pokédex" tab
        tab_name = self.main_tabs.tabText(index)
        self.statusBar().showMessage(f"Viewing: {tab_name}")

        if index == 0:
            # If switching to pokédex tab, activate current generation tab
            if hasattr(self, 'gen_tabs') and self.gen_tabs.count() > 0:
                current_gen_index = self.gen_tabs.currentIndex()
                if current_gen_index >= 0:
                    current_tab = self.gen_tabs.widget(current_gen_index)
                    if hasattr(current_tab, 'on_tab_activated'):
                        current_tab.on_tab_activated()
            
            print("📚 Auto-refreshed Pokédex after tab switch")

        # Index 2 is the "Analytics" tab
        elif index == 2:
            analytics_tab = self.main_tabs.widget(index)
            if hasattr(analytics_tab, 'refresh_if_needed'):
                refreshed = analytics_tab.refresh_if_needed()
                if refreshed:
                    print("📊 Auto-refreshed Analytics after tab switch")
                else:
                    print("📊 Analytics cache still valid")
                    
    def update_status_bar(self):
        """Update status bar with current stats"""
        try:
            # Get basic stats
            total_pokemon = len(self.db_manager.get_all_pokemon())
            user_collection = self.db_manager.get_user_collection()
            imported_count = len(user_collection)
            
            self.statusBar().showMessage(
                f"Ready | Total Pokémon: {total_pokemon} | "
                f"Imported Cards: {imported_count} | "
                f"Bronze-Silver-Gold Active"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Status Update Error: {e}")

    
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