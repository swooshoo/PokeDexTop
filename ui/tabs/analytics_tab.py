"""
Enhanced Analytics Tab - Extracted from app.py lines 274-550
Provides collection analytics and export functionality including PNG exports
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta

# PyQt6 imports
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox,
    QMessageBox, QDialog, QFileDialog, QProgressDialog)
from PyQt6.QtCore import Qt
from ui.dialogs.export_dialog import ExportOptionsDialog  
from export.image_generator import CollectionImageGenerator


class EnhancedAnalyticsTab(QWidget):
    """Enhanced analytics tab with new export functionality"""
    
    def __init__(self, db_manager, cache_manager, parent_window):  # Added cache_manager parameter
        super().__init__()
        self.db_manager = db_manager
        self.cache_manager = cache_manager  # Store cache_manager
        self.parent_window = parent_window
        
        self.stats_cache_valid = False # NEW: Smart caching and throttling
        self.last_refresh_time = None
        self.min_refresh_interval = timedelta(seconds=5)  # Throttle to max once per 5 seconds
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Collection statistics
        stats_group = QGroupBox("Collection Statistics")
        stats_layout = QVBoxLayout()
        
        self.collection_stats_label = QLabel()
        self.collection_stats_label.setStyleSheet("color: white; font-size: 12px;")
        stats_layout.addWidget(self.collection_stats_label)
        
        # refresh_stats_btn = QPushButton("Refresh Statistics") REMOVED REFRESH BUTTON ENTIRELY
        # refresh_stats_btn.clicked.connect(self.update_collection_stats)
        # stats_layout.addWidget(refresh_stats_btn)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Data quality metrics
        quality_group = QGroupBox("Data Quality")
        quality_layout = QVBoxLayout()
        
        self.data_quality_label = QLabel()
        self.data_quality_label.setStyleSheet("color: white; font-size: 12px;")
        quality_layout.addWidget(self.data_quality_label)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # Export & Backup section
        export_group = QGroupBox("Export & Backup")
        export_layout = QVBoxLayout()
        
        # Enhanced export collection button
        export_collection_btn = QPushButton("Export Collection as PNG")
        export_collection_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        export_collection_btn.clicked.connect(self.export_collection_image)
        export_layout.addWidget(export_collection_btn)
        
        # Legacy JSON export (smaller button)
        export_json_btn = QPushButton("Export as JSON (Legacy)")
        export_json_btn.setStyleSheet("font-size: 11px; padding: 6px;")
        export_json_btn.clicked.connect(self.export_collection_json)
        export_layout.addWidget(export_json_btn)
        
        backup_db_btn = QPushButton("Backup Database")
        backup_db_btn.setStyleSheet("font-size: 11px; padding: 6px;")
        backup_db_btn.clicked.connect(self.backup_database)
        export_layout.addWidget(backup_db_btn)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        # Update initial stats
        self.update_collection_stats()
        self.update_data_quality_stats()
    
    def export_collection_image(self):
        """Export collection as high-quality image"""
        # Check if user has any cards
        collection_info = self.get_collection_info()
        if collection_info['total_cards'] == 0:
            QMessageBox.information(self, "No Collection", 
                "You don't have any cards in your collection yet.\n"
                "Import some cards first!")
            return
        
        # Open export options dialog - UPDATED
        options_dialog = ExportOptionsDialog(self.db_manager, self)
        if options_dialog.exec() == QDialog.DialogCode.Accepted:
            export_config = options_dialog.get_export_config()
            
            # Show progress dialog
            progress_dialog = QProgressDialog("Preparing export...", "Cancel", 0, 100, self)
            progress_dialog.setWindowTitle("Exporting Collection")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()
            
            # Create and start generator thread
            self.generator_thread = CollectionImageGenerator(self.db_manager, export_config)
            self.generator_thread.progress_updated.connect(progress_dialog.setValue)
            self.generator_thread.progress_updated.connect(
                lambda value, message: progress_dialog.setLabelText(message)
            )
            self.generator_thread.generation_complete.connect(
                lambda file_path: self.on_export_complete(file_path, progress_dialog)
            )
            self.generator_thread.generation_error.connect(
                lambda error: self.on_export_error(error, progress_dialog)
            )
            
            # Handle cancel
            progress_dialog.canceled.connect(self.generator_thread.terminate)
            
            # Start generation
            self.generator_thread.start()
    
    def on_export_complete(self, file_path, progress_dialog):
        """Handle successful export completion"""
        progress_dialog.hide()
        
        # Show success message with option to open file
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Export Complete")
        msg_box.setText(f"Collection exported successfully!")
        msg_box.setInformativeText(f"Saved to: {file_path}")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        
        result = msg_box.exec()
        if result == QMessageBox.StandardButton.Open:
            # Open file in default image viewer
            import subprocess
            import sys
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path])
                else:
                    subprocess.run(["xdg-open", file_path])
            except Exception as e:
                QMessageBox.warning(self, "Cannot Open File", 
                    f"Export successful but cannot open file: {str(e)}")
    
    def on_export_error(self, error_message, progress_dialog):
        """Handle export error"""
        progress_dialog.hide()
        QMessageBox.critical(self, "Export Failed", 
            f"Failed to export collection:\n{error_message}")
    
    def get_collection_info(self):
        """Get basic collection information"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total_cards,
                   COUNT(DISTINCT p.generation) as generations
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total_cards': result[0] if result else 0,
            'generations': result[1] if result else 0
        }
    
    def export_collection_json(self):
        """Legacy JSON export functionality"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection (JSON)", "my_pokemon_collection.json", 
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                collection = self.db_manager.get_user_collection()
                
                with open(file_path, 'w') as f:
                    json.dump(collection, f, indent=2)
                
                QMessageBox.information(self, "Export Complete", 
                    f"Collection exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")
    
    def backup_database(self):
        """Create a backup of the database"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", 
            f"pokedextop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", 
            "Database files (*.db)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.db_manager.db_path, file_path)
                QMessageBox.information(self, "Backup Complete", 
                    f"Database backed up to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Error: {str(e)}")
    
    def update_collection_stats(self):
        """Update detailed collection statistics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Collection completion by generation
        cursor.execute("""
            SELECT g.generation, g.name, 
                   COUNT(p.pokemon_id) as total_pokemon,
                   COUNT(uc.pokemon_id) as imported_pokemon
            FROM gold_pokemon_generations g
            LEFT JOIN silver_pokemon_master p ON g.generation = p.generation
            LEFT JOIN gold_user_collections uc ON p.pokemon_id = uc.pokemon_id
            GROUP BY g.generation, g.name
            ORDER BY g.generation
        """)
        
        gen_stats = cursor.fetchall()
        
        # Build stats text
        stats_text = "Collection Completion by Generation:\n\n"
        total_pokemon = 0
        total_imported = 0
        
        for gen_num, gen_name, pokemon_count, imported_count in gen_stats:
            if pokemon_count > 0:
                completion_rate = (imported_count / pokemon_count) * 100
                stats_text += f"{gen_name}: {imported_count}/{pokemon_count} ({completion_rate:.1f}%)\n"
                total_pokemon += pokemon_count
                total_imported += imported_count
        
        if total_pokemon > 0:
            overall_completion = (total_imported / total_pokemon) * 100
            stats_text += f"\nOverall: {total_imported}/{total_pokemon} ({overall_completion:.1f}%)"
        
        self.collection_stats_label.setText(stats_text)
        conn.close()
    
    def update_data_quality_stats(self):
        """Update data quality metrics"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        # Data freshness
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN datetime(data_pull_timestamp) > datetime('now', '-7 days') THEN 1 END) as recent_records
            FROM bronze_tcg_cards
        """)
        
        result = cursor.fetchone()
        total_records, recent_records = result if result else (0, 0)
        
        # Missing images
        cursor.execute("""
            SELECT COUNT(*) FROM silver_tcg_cards 
            WHERE image_url_large IS NULL OR image_url_small IS NULL
        """)
        
        missing_images_result = cursor.fetchone()
        missing_images = missing_images_result[0] if missing_images_result else 0
        
        quality_text = f"Data Quality Metrics:\n\n"
        quality_text += f"Total Records: {total_records}\n"
        quality_text += f"Recent (7 days): {recent_records}\n"
        quality_text += f"Missing Images: {missing_images}\n"
        
        if total_records > 0:
            freshness_rate = (recent_records / total_records) * 100
            quality_text += f"Data Freshness: {freshness_rate:.1f}%"
        
        self.data_quality_label.setText(quality_text)
        conn.close()
        
    def mark_stats_dirty(self):
        """Mark statistics as needing refresh"""
        self.stats_cache_valid = False
        print("📊 Analytics stats marked as dirty")

    def refresh_if_needed(self):
        """Refresh stats only if needed (dirty) and not throttled"""
        now = datetime.now()
        
        # Check if refresh is needed
        if not self.stats_cache_valid:
            # Check throttling - don't refresh if we just did recently
            if (self.last_refresh_time is None or 
                now - self.last_refresh_time >= self.min_refresh_interval):
                
                print("📊 Refreshing analytics stats (cache invalid)")
                self.update_collection_stats()
                self.update_data_quality_stats()
                self.stats_cache_valid = True
                self.last_refresh_time = now
                return True
            else:
                time_remaining = self.min_refresh_interval - (now - self.last_refresh_time)
                print(f"📊 Analytics refresh throttled ({time_remaining.seconds}s remaining)")
                return False
        else:
            print("📊 Analytics stats cache valid, skipping refresh")
            return False

    def force_refresh_stats(self):
        """Force refresh stats regardless of cache state (for sync operations)"""
        print("📊 Force refreshing analytics stats")
        self.update_collection_stats()
        self.update_data_quality_stats()
        self.stats_cache_valid = True
        self.last_refresh_time = datetime.now()