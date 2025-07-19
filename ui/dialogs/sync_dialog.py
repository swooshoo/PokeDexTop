import os

from PyQt6.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QMessageBox, QDialog, QGroupBox, 
                            QProgressBar, QTextEdit)

from data.api_client import TCGAPIClient, RestClient, PokemonTcgException
from data.database import DatabaseManager


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
                
                # NEW: Mark analytics dirty after Pokemon sync
                if hasattr(self.parent(), 'mark_analytics_dirty'):
                    self.parent().mark_analytics_dirty()
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
            
            # NEW: Mark analytics dirty after sync completes
            if hasattr(self.parent(), 'mark_analytics_dirty'):
                self.parent().mark_analytics_dirty()
            
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
            
            # NEW: Mark analytics dirty after all sync completes
            if hasattr(self.parent(), 'mark_analytics_dirty'):
                self.parent().mark_analytics_dirty()
            
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