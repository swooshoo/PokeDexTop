# ui/dialogs/set_browse.py
"""
Set Browse Dialog - Extracted from app.py lines 1350-1550
Dialog for browsing and discovering TCG sets
"""

import sqlite3
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from data.database import DatabaseManager


class SetBrowseDialog(QDialog):
    """Dialog for browsing and discovering TCG sets"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_set_id = None
        self.setWindowTitle("Browse TCG Sets")
        self.setMinimumSize(800, 600)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Browse Available TCG Sets")
        title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search sets...")
        self.search_input.textChanged.connect(self.filter_sets)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Sets table
        self.sets_table = QTableWidget()
        self.sets_table.setColumnCount(5)
        self.sets_table.setHorizontalHeaderLabels(["Set Name", "Series", "Cards", "Release Date", "ID"])
        self.sets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sets_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sets_table.itemSelectionChanged.connect(self.on_set_selected)
        
        # Style the table
        self.sets_table.setStyleSheet("""
            QTableWidget {
                background-color: #2c3e50;
                color: white;
                gridline-color: #34495e;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        
        # Adjust column widths
        header = self.sets_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.sets_table)
        
        # Set preview
        preview_group = QGroupBox("Set Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Select a set to see details")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(100)
        self.preview_label.setStyleSheet("""
            background-color: #2c3e50; 
            border: 1px solid #34495e; 
            padding: 10px;
            color: white;
        """)
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select Set")
        self.select_button.setEnabled(False)
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.select_button.clicked.connect(self.accept)
        button_layout.addWidget(self.select_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Load sets
        self.load_all_sets()
    
    def load_all_sets(self):
        """Load all sets grouped by series"""
        self.sets_table.setRowCount(0)
        
        grouped_sets = self.db_manager.get_all_sets_grouped_by_series()
        
        # Sort series
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
        
        # Populate table
        for series in sorted_series:
            if series in grouped_sets:
                for set_info in grouped_sets[series]:
                    self.add_set_to_table(set_info)
    
    def add_set_to_table(self, set_info: Dict[str, Any]):
        """Add a set to the table"""
        row = self.sets_table.rowCount()
        self.sets_table.insertRow(row)
        
        # Set Name
        name_item = QTableWidgetItem(set_info['display_name'] or set_info['name'])
        self.sets_table.setItem(row, 0, name_item)
        
        # Series
        series_item = QTableWidgetItem(set_info['series'] or "Unknown")
        self.sets_table.setItem(row, 1, series_item)
        
        # Card Count
        card_count = set_info['total'] or 0
        count_item = QTableWidgetItem(str(card_count))
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sets_table.setItem(row, 2, count_item)
        
        # Release Date
        release_date = set_info['release_date'] or "Unknown"
        date_item = QTableWidgetItem(release_date)
        self.sets_table.setItem(row, 3, date_item)
        
        # Set ID
        id_item = QTableWidgetItem(set_info['set_id'])
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sets_table.setItem(row, 4, id_item)
        
        # Store full set info in the first item
        name_item.setData(Qt.ItemDataRole.UserRole, set_info)
    
    def filter_sets(self, text: str):
        """Filter sets based on search text"""
        search_text = text.lower()
        
        for row in range(self.sets_table.rowCount()):
            show_row = False
            
            # Check all columns
            for col in range(self.sets_table.columnCount()):
                item = self.sets_table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break
            
            self.sets_table.setRowHidden(row, not show_row)
    
    def on_set_selected(self):
        """Handle set selection"""
        selected_items = self.sets_table.selectedItems()
        
        if selected_items:
            # Get the set info from the first column
            row = selected_items[0].row()
            name_item = self.sets_table.item(row, 0)
            set_info = name_item.data(Qt.ItemDataRole.UserRole)
            
            if set_info:
                self.selected_set_id = set_info['set_id']
                self.select_button.setEnabled(True)
                
                # Update preview
                preview_text = f"<b>{set_info['display_name'] or set_info['name']}</b><br>"
                preview_text += f"Series: {set_info['series'] or 'Unknown'}<br>"
                preview_text += f"Cards: {set_info['total'] or 0}<br>"
                preview_text += f"Release: {set_info['release_date'] or 'Unknown'}<br>"
                preview_text += f"Set ID: {set_info['set_id']}"
                
                self.preview_label.setText(preview_text)
                self.preview_label.setStyleSheet("""
                    background-color: #2c3e50; 
                    border: 1px solid #34495e; 
                    padding: 10px;
                    color: white;
                """)
    
    def get_selected_set(self) -> Optional[str]:
        """Get the selected set ID"""
        return self.selected_set_id


class SetSearchDialog(QDialog):
    """Simplified set search dialog for quick access"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_set_id = None
        self.setWindowTitle("Quick Set Search")
        self.setMinimumSize(400, 300)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Quick Set Search")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Search input
        search_label = QLabel("Enter set name or ID:")
        search_label.setStyleSheet("color: white;")
        layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g. 'Base Set', 'xy1', 'Steam Siege'...")
        self.search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.search_input)
        
        # Search button
        search_btn = QPushButton("Search Sets")
        search_btn.clicked.connect(self.perform_search)
        layout.addWidget(search_btn)
        
        # Results area
        self.results_label = QLabel("Enter a search term to find sets")
        self.results_label.setStyleSheet("""
            background-color: #2c3e50; 
            border: 1px solid #34495e; 
            padding: 10px;
            color: white;
            min-height: 150px;
        """)
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_label.setWordWrap(True)
        layout.addWidget(self.results_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select First Match")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self.select_first_match)
        button_layout.addWidget(self.select_button)
        
        browse_btn = QPushButton("Browse All Sets")
        browse_btn.clicked.connect(self.open_full_browse)
        button_layout.addWidget(browse_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Focus on search input
        self.search_input.setFocus()
    
    def perform_search(self):
        """Perform set search"""
        search_term = self.search_input.text().strip()
        if not search_term:
            return
        
        # Search for matching sets
        matches = self.db_manager.search_sets(search_term)
        
        if not matches:
            self.results_label.setText(f"No sets found matching '{search_term}'.\n\nTry:\n• Different spelling\n• Set abbreviation (e.g. 'xy1')\n• Partial name\n• Browse all sets")
            self.select_button.setEnabled(False)
            return
        
        # Display results
        results_text = f"Found {len(matches)} matching sets:\n\n"
        
        for i, match in enumerate(matches[:5]):  # Show top 5 matches
            results_text += f"{i+1}. {match['display_name']}\n"
            results_text += f"   Series: {match['series']}\n"
            results_text += f"   Cards: {match['total']}\n"
            results_text += f"   ID: {match['set_id']}\n\n"
        
        if len(matches) > 5:
            results_text += f"... and {len(matches) - 5} more matches.\n"
            results_text += "Use 'Browse All Sets' to see everything."
        
        self.results_label.setText(results_text)
        self.matches = matches
        self.select_button.setEnabled(True)
    
    def select_first_match(self):
        """Select the first matching set"""
        if hasattr(self, 'matches') and self.matches:
            self.selected_set_id = self.matches[0]['set_id']
            self.accept()
    
    def open_full_browse(self):
        """Open the full browse dialog"""
        dialog = SetBrowseDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_set_id = dialog.get_selected_set()
            self.accept()
    
    def get_selected_set(self) -> Optional[str]:
        """Get the selected set ID"""
        return self.selected_set_id