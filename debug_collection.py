"""
Debug script to check the user collection format
Run this to see exactly what get_user_collection() returns
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import DatabaseManager

def debug_user_collection():
    """Debug the user collection data format"""
    print("🔍 DEBUGGING USER COLLECTION DATA FORMAT")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    try:
        # Get raw user collection
        print("1. Getting raw user collection...")
        raw_collection = db_manager.get_user_collection()
        
        print(f"\n📊 Raw collection type: {type(raw_collection)}")
        print(f"📊 Raw collection length: {len(raw_collection) if raw_collection else 0}")
        
        if raw_collection:
            print(f"\n🔍 First few items:")
            for i, item in enumerate(list(raw_collection)[:5]):
                print(f"   [{i}]: {type(item)} = {item}")
        else:
            print("❌ No collection data returned!")
            return
        
        print("\n" + "=" * 50)
        print("2. Checking what Pokemon cards expect...")
        
        # Show what format Pokemon cards expect
        expected_format = """
        Expected format for user_collection:
        {
            "pokemon_id": {
                "card_id": "xy1-1",
                "card_name": "Venusaur EX", 
                "image_url": "https://images.pokemontcg.io/xy1/1_hires.png",
                "set_name": "XY Base Set"
            }
        }
        """
        print(expected_format)
        
        print("\n" + "=" * 50)
        print("3. Attempting to format the data...")
        
        # Try to format the data
        formatted_collection = {}
        
        if isinstance(raw_collection, list):
            print("✅ Raw collection is a list")
            for item in raw_collection:
                if isinstance(item, tuple) and len(item) >= 5:
                    pokemon_id, card_id, card_name, image_url, set_name = item[:5]
                    formatted_collection[str(pokemon_id)] = {
                        'card_id': card_id,
                        'card_name': card_name,
                        'image_url': image_url,
                        'set_name': set_name
                    }
                    print(f"   ✅ Formatted Pokemon {pokemon_id}: {card_name}")
                else:
                    print(f"   ❌ Unexpected item format: {item}")
        
        elif isinstance(raw_collection, dict):
            print("✅ Raw collection is already a dict")
            formatted_collection = raw_collection
        
        else:
            print(f"❌ Unexpected collection type: {type(raw_collection)}")
        
        print(f"\n📊 Formatted collection: {len(formatted_collection)} Pokemon")
        
        if formatted_collection:
            print("\n🎯 Sample formatted data:")
            for pokemon_id, card_data in list(formatted_collection.items())[:3]:
                print(f"   Pokemon {pokemon_id}: {card_data}")
        
        print("\n" + "=" * 50)
        print("4. Testing with Generation 1...")
        
        # Test with Gen 1 Pokemon
        pokemon_data = db_manager.get_pokemon_by_generation(1)
        imported_in_gen1 = []
        
        for pokemon_id in pokemon_data.keys():
            if str(pokemon_id) in formatted_collection:
                pokemon_name = pokemon_data[pokemon_id]['name']
                card_name = formatted_collection[str(pokemon_id)]['card_name']
                imported_in_gen1.append(f"{pokemon_name} ({card_name})")
        
        print(f"\n🃏 Gen 1 imported cards: {len(imported_in_gen1)}")
        for card in imported_in_gen1[:10]:  # Show first 10
            print(f"   • {card}")
        
        if len(imported_in_gen1) > 10:
            print(f"   ... and {len(imported_in_gen1) - 10} more")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()


def check_database_structure():
    """Check the database structure"""
    print("\n" + "=" * 50)
    print("🗃️  CHECKING DATABASE STRUCTURE")
    print("=" * 50)
    
    db_manager = DatabaseManager()
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Check gold_user_collections table structure
        cursor.execute("PRAGMA table_info(gold_user_collections)")
        columns = cursor.fetchall()
        
        print("📋 gold_user_collections table structure:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        # Check number of records
        cursor.execute("SELECT COUNT(*) FROM gold_user_collections")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total records in gold_user_collections: {count}")
        
        # Show sample records
        cursor.execute("""
            SELECT uc.pokemon_id, uc.card_id, c.name, c.image_url_large, c.set_name
            FROM gold_user_collections uc
            JOIN silver_tcg_cards c ON uc.card_id = c.card_id
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        print(f"\n🔍 Sample records:")
        for record in records:
            print(f"   {record}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database check error: {e}")


if __name__ == '__main__':
    debug_user_collection()
    check_database_structure()
    
    print("\n" + "=" * 50)
    print("💡 NEXT STEPS:")
    print("1. Check if the formatted collection matches what you see in the stats")
    print("2. Verify that Pokemon IDs match between collection and generation data")
    print("3. If format is correct, the issue might be in the preload tab")