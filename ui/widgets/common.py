import sqlite3
from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import (Qt, QStringListModel)
from difflib import SequenceMatcher

# Extract shared UI components
# Implementation from app.py lines 500-600

class PokemonNameCompleter(QCompleter):
    """Custom completer for Pokemon names with fuzzy matching"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.pokemon_names = self.load_pokemon_names()
        self.setModel(QStringListModel(self.pokemon_names))
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
    
    def load_pokemon_names(self):
        """Load all unique Pokemon names from database"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT name FROM silver_pokemon_master 
            ORDER BY name
        """)
        
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names
    
    def find_best_match(self, input_text):
        """Find the best fuzzy match for input text"""
        if not input_text:
            return None
        
        input_lower = input_text.lower()
        best_match = None
        best_ratio = 0
        
        for name in self.pokemon_names:
            name_lower = name.lower()
            
            # Exact match gets priority
            if input_lower == name_lower:
                return name
            
            # Starts with gets high priority
            if name_lower.startswith(input_lower):
                ratio = 0.9 + (len(input_text) / len(name)) * 0.1
            else:
                # Use sequence matcher for fuzzy matching
                ratio = SequenceMatcher(None, input_lower, name_lower).ratio()
            
            if ratio > best_ratio and ratio > 0.6:  # Minimum threshold
                best_ratio = ratio
                best_match = name
        
        return best_match