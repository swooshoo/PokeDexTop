# Test database operations
# Test TCG API integrationimport pytest
import os
import tempfile
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import DatabaseManager

class TestDatabaseManager:
    
    def setup_method(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def teardown_method(self):
        """Clean up temporary database"""
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test that database tables are created correctly"""
        import sqlite3
        
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check that key tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'bronze_tcg_cards',
            'silver_pokemon_master', 
            'gold_user_collections'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
        
        conn.close()
    
    def test_pokemon_generation_calculation(self):
        """Test generation calculation logic"""
        assert self.db_manager.calculate_generation(25) == 1    # Pikachu
        assert self.db_manager.calculate_generation(152) == 2   # Chikorita  
        assert self.db_manager.calculate_generation(906) == 9   # Sprigatito