#!/usr/bin/env python3
"""
Initialize the PokéDextop database with Bronze-Silver-Gold architecture.
"""

import os
import sys

def setup_database():
    """Initialize database with all required tables"""
    print("🏗️  Initializing PokéDextop database...")
    
    # Ensure data directory exists
    os.makedirs("data/databases", exist_ok=True)
    
    # Add the current directory to Python path
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, current_dir)
    
    try:
        from app import DatabaseManager
        
        # Initialize database
        db_manager = DatabaseManager("data/databases/pokedextop.db")
        
        print("✅ Database initialized successfully!")
        print(f"📁 Database location: data/databases/pokedextop.db")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Use 'Sync Data' to fetch Pokemon cards from TCG API")
        
    except ImportError as e:
        print(f"❌ Failed to import app.py: {e}")
        print("Make sure app.py is in the same directory as this script")
        return False
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    setup_database()