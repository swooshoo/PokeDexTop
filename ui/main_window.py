"""
Main application window - PokemonDashboard
Extracted and cleaned from the monolithic app.py
"""

import sys
import sqlite3

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QPushButton, QLabel, QApplication, QProgressDialog)
from PyQt6.QtCore import QTimer

from config.settings import DARK_THEME_STYLE
from data.database import DatabaseManager
from cache.manager import CacheManager
from cache.image_loader import ImageLoader
from core.session import SessionCartManager

from ui.tabs.browse_tab import EnhancedBrowseTCGTab
from ui.tabs.analytics_tab import EnhancedAnalyticsTab
from ui.tabs.preload_generation_tab import PreloadGenerationTab
from ui.dialogs.generation_loading_dialog import GenerationLoadingDialog
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
        
        # Add these new attributes for preload system
        self.generation_tabs = {}
        self.loading_dialogs = {}
    
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
            gen_tab = PreloadGenerationTab(
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
        """Handle generation tab changes with loading dialog"""
        if index < 0 or index >= len(self.generations):
            return
        
        generation, gen_name = self.generations[index]
        gen_tab = self.generation_tabs.get(generation)
        
        if not gen_tab:
            return
        
        print(f"🔄 Switching to {gen_name} (Generation {generation})")
        
        # If tab is already loaded, no need for loading dialog
        if gen_tab.is_loaded:
            print(f"✅ {gen_name} already loaded - instant switch!")
            return
        
        # If tab is currently loading, show existing dialog
        if gen_tab.is_loading:
            existing_dialog = self.loading_dialogs.get(generation)
            if existing_dialog and existing_dialog.isVisible():
                existing_dialog.raise_()
                existing_dialog.activateWindow()
            return
        
        # Show loading dialog for unloaded tab
        self.show_generation_loading_dialog(generation, gen_name, gen_tab)
    
    def show_generation_loading_dialog(self, generation: int, gen_name: str, gen_tab):
        """Show loading dialog for generation preloading"""
        
        # Count Pokemon for progress tracking
        try:
            pokemon_data = self.db_manager.get_pokemon_by_generation(generation)
            total_cards = len(pokemon_data)
            
            if total_cards == 0:
                # No cards to load
                return
            
            print(f"📊 {gen_name} has {total_cards} Pokemon to preload")
            
            # Create loading dialog
            loading_dialog = GenerationLoadingDialog(gen_name, total_cards, self)
            self.loading_dialogs[generation] = loading_dialog
            
            # Connect tab signals to dialog
            if hasattr(gen_tab, 'preloader'):
                preloader = gen_tab.preloader
                if preloader:
                    preloader.progressUpdate.connect(loading_dialog.update_progress)
                    preloader.preloadComplete.connect(loading_dialog.set_completed)
                    preloader.preloadError.connect(loading_dialog.set_error)
            
            # Connect dialog cancel to tab
            loading_dialog.cancelled.connect(lambda: self.cancel_generation_loading(generation))
            
            # Show dialog
            loading_dialog.show()
            
            # Start preloading if not already started
            if not gen_tab.is_loading:
                gen_tab.start_preloading()
            
        except Exception as e:
            print(f"❌ Error showing loading dialog for {gen_name}: {e}")
            # Show simple loading dialog as fallback
            simple_dialog = QProgressDialog(
                f"Loading {gen_name}", 
                "Preparing Pokemon cards...", 
                self
            )
            simple_dialog.show()
            simple_dialog.auto_close(3000)


    def cancel_generation_loading(self, generation: int):
        """Cancel generation loading"""
        gen_tab = self.generation_tabs.get(generation)
        if gen_tab:
            gen_tab.stop_preloading()
            print(f"⏹️  Cancelled loading for Generation {generation}")
        
        # Clean up loading dialog
        loading_dialog = self.loading_dialogs.pop(generation, None)
        if loading_dialog:
            loading_dialog.deleteLater()


    def cleanup_loading_dialogs(self):
        """Clean up any remaining loading dialogs"""
        for dialog in self.loading_dialogs.values():
            if dialog and dialog.isVisible():
                dialog.close()
        self.loading_dialogs.clear()
    
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
        
    def closeEvent(self, event):
        """Handle application closing"""
        # Stop any ongoing preloading
        for gen_tab in self.generation_tabs.values():
            if gen_tab and gen_tab.is_loading:
                gen_tab.stop_preloading()
        
        # Clean up loading dialogs
        self.cleanup_loading_dialogs()
        
        # Call parent close event
        super().closeEvent(event)
        
    def update_status_bar(self):
        """Update status bar with current stats (ENHANCED)"""
        try:
            # Get basic stats
            total_pokemon = len(self.db_manager.get_all_pokemon())
            user_collection = self.db_manager.get_user_collection()
            imported_count = len(user_collection)
            
            # Check for any ongoing preloading
            loading_generations = []
            for gen, tab in self.generation_tabs.items():
                if tab and tab.is_loading:
                    loading_generations.append(f"Gen {gen}")
            
            status_text = (
                f"Ready | Total Pokémon: {total_pokemon} | "
                f"Imported Cards: {imported_count} | "
                f"Bronze-Silver-Gold Active"
            )
            
            if loading_generations:
                status_text += f" | Loading: {', '.join(loading_generations)}"
            
            self.statusBar().showMessage(status_text)
            
        except Exception as e:
            self.statusBar().showMessage(f"Status Update Error: {e}")
