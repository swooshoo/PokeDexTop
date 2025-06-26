#!/usr/bin/env python3
"""
Test connection to Pokemon TCG API
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_connection():
    """Test basic API connectivity"""
    print("🔌 Testing Pokemon TCG API connection...")
    
    try:
        # Test direct Pokemon TCG SDK first (without our database layer)
        print("🔧 Testing direct Pokemon TCG SDK...")
        from pokemontcgsdk import Card
        
        # Direct API test
        print("🔍 Searching for Pikachu cards via SDK...")
        cards = Card.where(q='name:Pikachu')
        
        if cards:
            print(f"✅ SDK Success! Found {len(cards)} Pikachu cards")
            print(f"📋 First card: {cards[0].name}")
            print(f"🃏 Card ID: {cards[0].id}")
            print(f"🎨 Artist: {cards[0].artist}")
            print(f"📦 Set: {cards[0].set.name}")
        else:
            print("⚠️  No cards found via SDK")
            return False
            
        # Now test our database integration
        print("\n🔧 Testing our database integration...")
        from app import TCGAPIClient, DatabaseManager
        
        # Use a real temporary file instead of :memory:
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            # Initialize components with temp file
            print("📊 Setting up temporary database...")
            db_manager = DatabaseManager(temp_db.name)
            
            print("🔧 Initializing TCG client...")
            tcg_client = TCGAPIClient(db_manager)
            
            # Test our wrapped method
            print("🔍 Testing our TCG client wrapper...")
            our_cards = tcg_client.search_cards_by_pokemon_name("Pikachu")
            
            if our_cards:
                print(f"✅ Our wrapper success! Processed {len(our_cards)} Pikachu cards")
                print(f"📋 First card: {our_cards[0].get('name', 'Unknown')}")
            else:
                print("⚠️  Our wrapper returned no cards")
                
        finally:
            # Clean up temp file
            os.unlink(temp_db.name)
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Make sure pokemontcgsdk is installed: pip install pokemontcgsdk")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    print("🎉 All API tests completed successfully!")
    return True

if __name__ == "__main__":
    success = test_api_connection()
    if not success:
        sys.exit(1)