"""
Database Manager - Bronze-Silver-Gold Data Architecture
Extracted from app.py with cache integration points added
"""

import os
import sqlite3
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import DEFAULT_DB_PATH, POKEMON_GENERATIONS


class DatabaseManager:
    """
    Implements Bronze-Silver-Gold data architecture with cache integration:
    
    BRONZE (Raw): Direct API responses stored as-is
    SILVER (Processed): Cleaned and normalized data 
    GOLD (Master): Business-ready data for applications
    
    Now includes cache path tracking for hybrid strategy
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        
        # Only create directory for file-based databases
        if self.db_path != ":memory:" and not self.db_path.startswith(":"):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.init_database()
        self.configure_database_for_concurrency()
        
        # Cache manager will be injected later to avoid circular imports
        self._cache_manager = None
    
    def set_cache_manager(self, cache_manager):
        """Set the cache manager for image caching integration"""
        self._cache_manager = cache_manager
    
    def load_pokemon_master_data(self):
        """Load the complete Pokémon list from JSON file"""
        master_file = Path(__file__).parent.parent / 'data' / 'pokemon_master_data.json'
        
        if not master_file.exists():
            print(f"WARNING: Pokemon master data file not found at {master_file}")
            return []
        
        with open(master_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['pokemon']
    
    def initialize_complete_pokedex(self):
        """Pre-populate database with all 1025 Pokémon"""
        pokemon_list = self.load_pokemon_master_data()
        
        if not pokemon_list:
            print("ERROR: No Pokemon master data loaded")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for pokemon in pokemon_list:
            cursor.execute("""
                INSERT OR IGNORE INTO silver_pokemon_master 
                (pokemon_id, name, generation, pokedex_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                pokemon['id'], 
                pokemon['name'], 
                pokemon['generation'], 
                json.dumps([pokemon['id']])
            ))
        
        conn.commit()
        conn.close()
        print(f"✓ Pre-populated database with {len(pokemon_list)} Pokémon")
    
    def init_database(self):
        """Create Bronze-Silver-Gold data tables with cache integration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # =============================================================================
        # BRONZE LAYER - Raw API Data (Immutable Historical Record)
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                api_endpoint TEXT,
                UNIQUE(card_id, data_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze_tcg_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id TEXT NOT NULL,
                api_source TEXT DEFAULT 'pokemontcg.io',
                raw_json TEXT NOT NULL,
                data_pull_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash TEXT NOT NULL,
                UNIQUE(set_id, data_hash)
            )
        """)
        
        # =============================================================================
        # SILVER LAYER - Processed & Cleaned Data (WITH CACHE INTEGRATION)
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_pokemon_master (
                pokemon_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                generation INTEGER,
                pokedex_numbers TEXT,  -- JSON array of national pokedex numbers
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_ids TEXT  -- JSON array of bronze record IDs
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_cards (
                card_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pokemon_name TEXT,
                set_id TEXT NOT NULL,
                set_name TEXT,
                artist TEXT,
                rarity TEXT,
                supertype TEXT,
                subtypes TEXT,  -- JSON array
                types TEXT,     -- JSON array  
                hp TEXT,
                number TEXT,
                image_url_small TEXT,
                image_url_large TEXT,
                national_pokedex_numbers TEXT,  -- JSON array
                legalities TEXT,  -- JSON object
                market_prices TEXT,  -- JSON object
                
                -- CACHE INTEGRATION FIELDS (HYBRID STRATEGY)
                cached_image_path TEXT,
                cached_at TIMESTAMP,
                original_file_size INTEGER,
                cache_quality TEXT, -- 'original', 'high', 'medium'
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_cards(id)
            )
        """)
        
        # Check if cache columns exist (for migration)
        cursor.execute("PRAGMA table_info(silver_tcg_cards)")
        columns = [column[1] for column in cursor.fetchall()]
        
        cache_columns = [
            ('cached_image_path', 'TEXT'),
            ('cached_at', 'TIMESTAMP'),
            ('original_file_size', 'INTEGER'),
            ('cache_quality', 'TEXT')
        ]
        
        for col_name, col_type in cache_columns:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE silver_tcg_cards ADD COLUMN {col_name} {col_type}")
        
        # Team-up card mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_team_up_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                pokemon_name TEXT NOT NULL,
                position INTEGER DEFAULT 0,  -- position in team (0 = first, 1 = second, etc.)
                FOREIGN KEY (card_id) REFERENCES silver_tcg_cards(card_id),
                UNIQUE(card_id, pokemon_name)
            )
        """)
        
        # Enhanced sets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_tcg_sets (
                set_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,  -- User-friendly display name
                search_terms TEXT,  -- JSON array of searchable terms
                series TEXT,
                printed_total INTEGER,
                total INTEGER,
                release_date TEXT,
                symbol_url TEXT,
                logo_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_bronze_id INTEGER,
                FOREIGN KEY (source_bronze_id) REFERENCES bronze_tcg_sets(id)
            )
        """)
        
        # Check if new columns exist
        cursor.execute("PRAGMA table_info(silver_tcg_sets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'display_name' not in columns:
            cursor.execute("ALTER TABLE silver_tcg_sets ADD COLUMN display_name TEXT")
        
        if 'search_terms' not in columns:
            cursor.execute("ALTER TABLE silver_tcg_sets ADD COLUMN search_terms TEXT")
        
        # =============================================================================
        # GOLD LAYER - Business-Ready Application Data
        # =============================================================================
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_user_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                pokemon_id INTEGER,
                card_id TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collection_type TEXT DEFAULT 'personal',  -- personal, wishlist, favorites
                notes TEXT,
                UNIQUE(user_id, pokemon_id, collection_type),
                FOREIGN KEY (pokemon_id) REFERENCES silver_pokemon_master(pokemon_id),
                FOREIGN KEY (card_id) REFERENCES silver_tcg_cards(card_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_pokemon_generations (
                generation INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                start_id INTEGER,
                end_id INTEGER,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance indexes
        self.create_indexes(cursor)
        
        # Initialize generation data
        self.initialize_generations(cursor)
        
        conn.commit()
        conn.close()
        
        # Initialize complete Pokedex
        self.initialize_complete_pokedex()
    
    def create_indexes(self, cursor):
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_bronze_cards_timestamp ON bronze_tcg_cards(data_pull_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_silver_cards_pokemon ON silver_tcg_cards(pokemon_name)",
            "CREATE INDEX IF NOT EXISTS idx_silver_cards_set ON silver_tcg_cards(set_id)",
            "CREATE INDEX IF NOT EXISTS idx_silver_sets_display_name ON silver_tcg_sets(display_name)",
            "CREATE INDEX IF NOT EXISTS idx_silver_sets_series ON silver_tcg_sets(series)",
            "CREATE INDEX IF NOT EXISTS idx_gold_collections_user ON gold_user_collections(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_silver_cards_cached_path ON silver_tcg_cards(cached_image_path)",  # New cache index
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def initialize_generations(self, cursor):
        """Initialize Pokemon generation data"""
        for gen_data in POKEMON_GENERATIONS:
            cursor.execute("""
                INSERT OR IGNORE INTO gold_pokemon_generations 
                (generation, name, start_id, end_id, region)
                VALUES (?, ?, ?, ?, ?)
            """, gen_data)
    
    def configure_database_for_concurrency(self):
        """Configure database for better concurrency handling"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Set busy timeout
            conn.execute("PRAGMA busy_timeout=30000")
            # Optimize for faster writes
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.commit()
        finally:
            conn.close()
    
    # =============================================================================
    # BRONZE LAYER OPERATIONS - Raw Data Storage
    # =============================================================================
    
    def store_bronze_card_data(self, card_data, api_endpoint="cards"):
        """Store raw card data in Bronze layer with deduplication"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            card_id = card_data.get('id')
            raw_json = json.dumps(card_data, sort_keys=True)
            content_hash = hashlib.sha256(raw_json.encode()).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT INTO bronze_tcg_cards 
                    (card_id, raw_json, data_hash, api_endpoint)
                    VALUES (?, ?, ?, ?)
                """, (card_id, raw_json, content_hash, api_endpoint))
                
                bronze_id = cursor.lastrowid
                conn.commit()
                
                # Process to Silver layer (with cache integration)
                self.process_bronze_to_silver_card(bronze_id, card_data)
                print(f"✓ Stored new card data: {card_id}")
                return bronze_id
                
            except sqlite3.IntegrityError:
                cursor.execute("""
                    SELECT id FROM bronze_tcg_cards 
                    WHERE card_id = ? AND data_hash = ?
                """, (card_id, content_hash))
                result = cursor.fetchone()
                existing_id = result[0] if result else None
                print(f"⚡ Duplicate card data found: {card_id}")
                return existing_id
                
        except Exception as e:
            print(f"Database error storing card {card_data.get('id', 'unknown')}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def process_bronze_to_silver_card(self, bronze_id, card_data):
        """Process Bronze card data to Silver layer with cache integration"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()
            
            # Extract and clean card data
            card_id = card_data.get('id')
            name = card_data.get('name', '')
            pokemon_names = self.extract_pokemon_name_from_card(name)
            
            # Handle team-up cards
            primary_pokemon_name = None
            is_team_up = False
            
            if isinstance(pokemon_names, list):
                is_team_up = True
                primary_pokemon_name = pokemon_names[0] if pokemon_names else None
                all_pokemon_names = pokemon_names
            else:
                primary_pokemon_name = pokemon_names
                all_pokemon_names = [pokemon_names] if pokemon_names else []
            
            # Handle nested data safely
            set_data = card_data.get('set', {})
            images = card_data.get('images', {})
            legalities = card_data.get('legalities', {})
            tcgplayer = card_data.get('tcgplayer', {})
            
            # CACHE INTEGRATION: Prepare image URL for caching
            image_url_large = images.get('large')
            cached_path = None
            if image_url_large and self._cache_manager:
                # Cache the image in background
                try:
                    cached_path = self._cache_manager.cache_image(
                        image_url_large, card_id, 'tcg_card', 'original'
                    )
                except Exception as cache_error:
                    print(f"Cache error for {card_id}: {cache_error}")
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_tcg_cards 
                (card_id, name, pokemon_name, set_id, set_name, artist, rarity, 
                supertype, subtypes, types, hp, number, 
                image_url_small, image_url_large, national_pokedex_numbers,
                legalities, market_prices, cached_image_path, cached_at, 
                cache_quality, source_bronze_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id, name, primary_pokemon_name, set_data.get('id'), 
                set_data.get('name'), card_data.get('artist'), card_data.get('rarity'),
                card_data.get('supertype'), json.dumps(card_data.get('subtypes', [])),
                json.dumps(card_data.get('types', [])), card_data.get('hp'),
                card_data.get('number'), images.get('small'), images.get('large'),
                json.dumps(card_data.get('nationalPokedexNumbers', [])),
                json.dumps(legalities), json.dumps(tcgplayer.get('prices', {})),
                str(cached_path) if cached_path else None,
                datetime.now() if cached_path else None,
                'original' if cached_path else None,
                bronze_id
            ))
            
            # Handle team-up card mapping (existing logic)
            if is_team_up:
                cursor.execute("DELETE FROM silver_team_up_cards WHERE card_id = ?", (card_id,))
                for position, pokemon_name in enumerate(all_pokemon_names):
                    if pokemon_name:
                        cursor.execute("""
                            INSERT INTO silver_team_up_cards (card_id, pokemon_name, position)
                            VALUES (?, ?, ?)
                        """, (card_id, pokemon_name, position))
            
            # Update Pokemon master records (existing logic)
            pokedex_numbers = card_data.get('nationalPokedexNumbers', [])
            if pokedex_numbers:
                if is_team_up and len(all_pokemon_names) > 1:
                    for pokemon_name in all_pokemon_names:
                        if pokemon_name:
                            self.update_silver_pokemon_master_with_connection(
                                cursor, pokemon_name, pokedex_numbers
                            )
                else:
                    if primary_pokemon_name:
                        self.update_silver_pokemon_master_with_connection(
                            cursor, primary_pokemon_name, pokedex_numbers
                        )
            
            conn.commit()
            
        except Exception as e:
            print(f"Error processing card to silver layer: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def update_silver_pokemon_master_with_connection(self, cursor, pokemon_name, pokedex_numbers):
        """Update Pokemon master using existing connection"""
        try:
            # Calculate generation from first pokedex number
            primary_number = pokedex_numbers[0] if pokedex_numbers else None
            generation = self.calculate_generation(primary_number) if primary_number else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO silver_pokemon_master 
                (pokemon_id, name, generation, pokedex_numbers)
                VALUES (?, ?, ?, ?)
            """, (
                primary_number,
                pokemon_name,
                generation,
                json.dumps(pokedex_numbers)
            ))
            
        except Exception as e:
            print(f"Error updating Pokemon master: {e}")
            raise
    
    def extract_pokemon_name_from_card(self, card_name):
        """Extract Pokemon name from card name using improved logic"""
        import re
        
        if not card_name:
            return None
        
        # First, check for team-up cards (& symbol indicates multiple Pokemon)
        if ' & ' in card_name:
            # Extract all Pokemon names from team-up cards
            # Remove any suffixes first
            clean_team_name = re.sub(r'\s+(?:GX|TAG TEAM|LEGEND).*$', '', card_name)
            # Split by & and clean each name
            pokemon_names = []
            for name in clean_team_name.split(' & '):
                cleaned = self._clean_single_pokemon_name(name.strip())
                if cleaned:
                    pokemon_names.append(cleaned)
            return pokemon_names  # Return list for team-ups
        
        # For single Pokemon, use existing logic
        return self._clean_single_pokemon_name(card_name)
    
    def _clean_single_pokemon_name(self, card_name):
        """Clean a single Pokemon name"""
        import re
        
        if not card_name:
            return None
        
        # Remove card prefixes
        clean_name = re.sub(r'^(Card #\d+\s+|[A-Z]{1,5}\d+\s+)', '', card_name)
        
        # Remove trainer possessives (e.g., "Team Rocket's", "Brock's", "Misty's")
        clean_name = re.sub(r"^[A-Za-z\s]+\'s\s+", '', clean_name)
        clean_name = re.sub(r"^Team\s+[A-Za-z\s]+\'s\s+", '', clean_name)
        
        # Handle special cases
        special_cases = {
            "Mr. Mime": "Mr. Mime",
            "Mime Jr.": "Mime Jr.",
            "Farfetch'd": "Farfetch'd",
            "Sirfetch'd": "Sirfetch'd",
            "Type: Null": "Type: Null",
            "Ho-Oh": "Ho-Oh",
            "Porygon-Z": "Porygon-Z",
            "Jangmo-o": "Jangmo-o",
            "Hakamo-o": "Hakamo-o",
            "Kommo-o": "Kommo-o"
        }
        
        for special_name, replacement in special_cases.items():
            if special_name in clean_name:
                return replacement
        
        # Remove regional prefixes but keep the base name
        regional_prefixes = ["Alolan", "Galarian", "Paldean", "Hisuian"]
        for region in regional_prefixes:
            if clean_name.startswith(f"{region} "):
                clean_name = clean_name.replace(f"{region} ", "", 1)
                break
        
        # Remove card suffixes
        clean_name = re.sub(r'\s+(?:ex|EX|GX|V|VMAX|VSTAR|V-UNION|Prime|BREAK|Prism Star|◇|LV\.X|MEGA|M|Tag Team).*$', '', clean_name)
        
        # Remove any remaining special characters
        clean_name = re.sub(r'[◇★]', '', clean_name)
        
        return clean_name.strip()
    
    def calculate_generation(self, pokedex_number):
        """Calculate generation from pokedex number"""
        if not pokedex_number:
            return None
            
        generation_ranges = [
            (1, 151, 1), (152, 251, 2), (252, 386, 3), (387, 493, 4), (494, 649, 5),
            (650, 721, 6), (722, 809, 7), (810, 905, 8), (906, 1025, 9)
        ]
        
        for start, end, gen in generation_ranges:
            if start <= pokedex_number <= end:
                return gen
        return 9  # Default to latest
    
    # =============================================================================
    # GOLD LAYER OPERATIONS - Business Logic
    # =============================================================================
    
    def get_pokemon_by_generation(self, generation):
        """Get ALL Pokémon for a generation with card availability"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.pokemon_id, 
                p.name, 
                p.pokedex_numbers,
                COUNT(DISTINCT c.card_id) as card_count,
                GROUP_CONCAT(DISTINCT c.card_id) as available_cards
            FROM silver_pokemon_master p
            LEFT JOIN (
                SELECT card_id, pokemon_name FROM silver_tcg_cards
                UNION
                SELECT t.card_id, t.pokemon_name FROM silver_team_up_cards t
            ) c ON p.name = c.pokemon_name
            WHERE p.generation = ?
            GROUP BY p.pokemon_id, p.name
            ORDER BY p.pokemon_id
        """, (generation,))
        
        results = cursor.fetchall()
        conn.close()
        
        pokemon_dict = {}
        for row in results:
            pokemon_dict[str(row[0])] = {
                'id': row[0],
                'name': row[1],
                'generation': generation,
                'pokedex_numbers': json.loads(row[2]) if row[2] else [],
                'card_count': row[3],
                'available_cards': row[4].split(',') if row[4] else []
            }
        
        return pokemon_dict
    
    def get_user_collection(self, user_id='default'):
        """Get user's collection from Gold layer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT uc.pokemon_id, uc.card_id, c.name, c.image_url_large, c.set_name
            FROM gold_user_collections uc
            JOIN silver_tcg_cards c ON uc.card_id = c.card_id
            WHERE uc.user_id = ? AND uc.collection_type = 'personal'
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        collection = {}
        for row in results:
            collection[str(row[0])] = {
                'card_id': row[1],
                'card_name': row[2],
                'image_url': row[3],
                'set_name': row[4]
            }
        
        return collection
    
    def add_to_user_collection(self, user_id, pokemon_id, card_id):
        """Add card to user's collection (Gold layer)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO gold_user_collections 
            (user_id, pokemon_id, card_id, collection_type)
            VALUES (?, ?, ?, 'personal')
        """, (user_id, pokemon_id, card_id))
        
        conn.commit()
        conn.close()
    
    # =============================================================================
    # CACHE INTEGRATION METHODS (NEW FOR HYBRID STRATEGY)
    # =============================================================================
    
    def update_card_cache_info(self, card_id: str, cached_path: str, file_size: int, quality: str):
        """Update cache information in silver_tcg_cards table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE silver_tcg_cards 
            SET cached_image_path = ?, cached_at = ?, original_file_size = ?, cache_quality = ?
            WHERE card_id = ?
        """, (cached_path, datetime.now(), file_size, quality, card_id))
        
        conn.commit()
        conn.close()
    
    def get_uncached_cards(self, quality: str = 'original') -> List[Dict[str, Any]]:
        """Get cards that don't have cached images"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT card_id, image_url_large, image_url_small
            FROM silver_tcg_cards 
            WHERE (cached_image_path IS NULL OR cache_quality != ?) 
            AND (image_url_large IS NOT NULL OR image_url_small IS NOT NULL)
        """, (quality,))
        
        results = cursor.fetchall()
        conn.close()
        
        uncached_cards = []
        for card_id, url_large, url_small in results:
            uncached_cards.append({
                'card_id': card_id,
                'image_url': url_large or url_small,
                'preferred_url': url_large or url_small
            })
        
        return uncached_cards
    
    def get_cached_card_path(self, card_id: str) -> Optional[str]:
        """Get cached path for a card if it exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cached_image_path 
            FROM silver_tcg_cards 
            WHERE card_id = ? AND cached_image_path IS NOT NULL
        """, (card_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and Path(result[0]).exists():
            return result[0]
        return None