# ui/dialogs/export_dialog.py
"""
Export Options Dialog - Extracted from app.py lines 50-200
Dialog for configuring collection export options
"""

import os
import json
import sqlite3
import math
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QCheckBox, QLineEdit, QSpinBox, QComboBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from data.database import DatabaseManager


class ExportOptionsDialog(QDialog):
    """Dialog for configuring collection export options"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.export_config = {
            'custom_title': 'My Pokémon Collection',
            'include_pokedex_info': True,
            'include_set_label': True,
            'include_artist_label': False,
            'cards_per_row': 4,
            'image_quality': 'high',
            'generation_filter': 'all'
        }
        self.setWindowTitle("Export Collection")
        self.setMinimumSize(450, 600)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Export Your Collection - Options")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Collection info
        collection_info = self.get_collection_info()
        info_label = QLabel(f"Found {collection_info['total_cards']} cards across {collection_info['generations']} generations")
        info_label.setStyleSheet("color: #bdc3c7; font-size: 12px; margin-bottom: 15px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Generation filter
        gen_group = QGroupBox("Generation Filter")
        gen_layout = QVBoxLayout()
        
        self.gen_combo = QComboBox()
        self.gen_combo.addItem("All Generations", "all")
        
        # Add individual generations
        generations = self.get_available_generations()
        for gen_num, gen_name, card_count in generations:
            self.gen_combo.addItem(f"{gen_name} ({card_count} cards)", gen_num)
        
        self.gen_combo.currentTextChanged.connect(self.update_preview)
        gen_layout.addWidget(self.gen_combo)
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)
        
        # Label options
        labels_group = QGroupBox("Card Labels to Include")
        labels_layout = QVBoxLayout()
        
        self.pokedex_checkbox = QCheckBox("Pokédex Number & Name")
        self.pokedex_checkbox.setChecked(True)
        self.pokedex_checkbox.setStyleSheet("color: white;")
        self.pokedex_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.pokedex_checkbox)
        
        self.set_checkbox = QCheckBox("Set Name")
        self.set_checkbox.setChecked(True)
        self.set_checkbox.setStyleSheet("color: white;")
        self.set_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.set_checkbox)
        
        self.artist_checkbox = QCheckBox("Artist Name")
        self.artist_checkbox.setChecked(False)
        self.artist_checkbox.setStyleSheet("color: white;")
        self.artist_checkbox.toggled.connect(self.update_preview)
        labels_layout.addWidget(self.artist_checkbox)
        
        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)
        
        # Custom title input
        title_group = QGroupBox("Collection Title")
        title_layout = QVBoxLayout()
        
        title_label = QLabel("Enter a custom title for your collection:")
        title_label.setStyleSheet("color: white; font-size: 11px;")
        title_layout.addWidget(title_label)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("My Pokémon Collection")
        self.title_input.setText("My Pokémon Collection")
        self.title_input.setStyleSheet("padding: 8px; font-size: 12px;")
        self.title_input.textChanged.connect(self.update_preview)
        title_layout.addWidget(self.title_input)
        
        title_group.setLayout(title_layout)
        layout.addWidget(title_group)
        
        # Layout options
        layout_group = QGroupBox("Layout Options")
        layout_layout = QVBoxLayout()
        
        # Cards per row
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Cards per row:"))
        self.cards_per_row_spin = QSpinBox()
        self.cards_per_row_spin.setRange(2, 5)
        self.cards_per_row_spin.setValue(4)
        self.cards_per_row_spin.valueChanged.connect(self.update_preview)
        row_layout.addWidget(self.cards_per_row_spin)
        row_layout.addStretch()
        layout_layout.addLayout(row_layout)
        
        # Quality options
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Image quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("High (Print Quality)", "high")
        self.quality_combo.addItem("Medium (Web Sharing)", "medium")
        self.quality_combo.addItem("Low (Quick Preview)", "low")
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        layout_layout.addLayout(quality_layout)
        
        layout_group.setLayout(layout_layout)
        layout.addWidget(layout_group)
        
        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("""
            background-color: #2c3e50; 
            border: 1px solid #34495e; 
            padding: 8px;
            color: white;
            font-size: 11px;
        """)
        self.preview_label.setMinimumHeight(120)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.export_btn = QPushButton("📸 Export Collection")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
        # Initial preview update
        self.update_preview()
    
    def get_collection_info(self) -> Dict[str, int]:
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
    
    def get_available_generations(self) -> List[tuple]:
        """Get generations that have cards in the collection"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.generation, g.name, COUNT(*) as card_count
            FROM gold_user_collections uc
            JOIN silver_pokemon_master p ON uc.pokemon_id = p.pokemon_id
            JOIN gold_pokemon_generations g ON p.generation = g.generation
            GROUP BY p.generation, g.name
            ORDER BY p.generation
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def update_preview(self):
        """Update the preview text"""
        generation = self.gen_combo.currentData()
        cards_per_row = self.cards_per_row_spin.value()
        custom_title = self.title_input.text().strip() or "My Pokémon Collection"
        
        # Get card count for preview
        if generation == "all":
            card_count = self.get_collection_info()['total_cards']
            gen_text = "All Generations"
        else:
            card_count = next((count for gen, name, count in self.get_available_generations() 
                             if gen == generation), 0)
            gen_text = f"Generation {generation}"
        
        if card_count == 0:
            self.preview_label.setText("No cards found for selected generation.")
            self.export_btn.setEnabled(False)
            return
        
        self.export_btn.setEnabled(True)
        
        # Calculate grid dimensions
        rows = math.ceil(card_count / cards_per_row)
        
        preview_text = f"Export Preview:\n\n"
        preview_text += f"📋 Title: \"{custom_title}\"\n"
        preview_text += f"🎯 Generation: {gen_text}\n"
        preview_text += f"🃏 Cards: {card_count}\n"
        preview_text += f"📐 Grid: {rows} rows × {cards_per_row} columns\n\n"
        
        preview_text += "Card Labels:\n"
        labels = []
        if self.pokedex_checkbox.isChecked():
            labels.append("• Pokédex # & Name")
        if self.set_checkbox.isChecked():
            labels.append("• Set Name")
        if self.artist_checkbox.isChecked():
            labels.append("• Artist")
        
        if labels:
            preview_text += "\n".join(labels)
        else:
            preview_text += "• No labels (cards only)"
        
        quality = self.quality_combo.currentText()
        preview_text += f"\n\nQuality: {quality}"
        preview_text += f"\n\nFooter: Export date + \"Exported by PokéDextop\""
        
        self.preview_label.setText(preview_text)
    
    def start_export(self):
        """Start the export process"""
        # Update config
        self.export_config.update({
            'custom_title': self.title_input.text().strip() or "My Pokémon Collection",
            'include_pokedex_info': self.pokedex_checkbox.isChecked(),
            'include_set_label': self.set_checkbox.isChecked(),
            'include_artist_label': self.artist_checkbox.isChecked(),
            'cards_per_row': self.cards_per_row_spin.value(),
            'image_quality': self.quality_combo.currentData(),
            'generation_filter': self.gen_combo.currentData()
        })
        
        # Get export file path
        safe_title = "".join(c for c in self.export_config['custom_title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_').lower()
        
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection", filename, "PNG Images (*.png)"
        )
        
        if file_path:
            self.export_config['file_path'] = file_path
            self.accept()
    
    def get_export_config(self) -> Dict[str, Any]:
        """Get the export configuration"""
        return self.export_config